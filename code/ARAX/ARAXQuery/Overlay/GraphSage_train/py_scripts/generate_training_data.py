## This script is used to generate the training data of mychem, ndf and semmed for training the model.
import sys, os
import pandas as pd
import requests
import time
import numpy
import urllib
import ast
import subprocess
import gzip
import csv
import numpy as np
from neo4j import GraphDatabase
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'reasoningtool','kg-construction']))
from QueryMyChem import QueryMyChem

class DataGeneration:

    #### Constructor
    def __init__(self):
        ## Connect to neo4j database
        rtxc = RTXConfiguration()
        rtxc.live = 'KG2c'
        self.driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))

    def get_drug_curies_from_graph(self):
        ## Pulls a dataframe of all of the graph drug-associated nodes
        query = "match (n {category:'biolink:ChemicalSubstance'}) with distinct n.id as id, n.name as name, n.equivalent_curies as equivalent_curies return id, name, equivalent_curies union match (n {category:'biolink:Drug'}) with distinct n.id as id, n.name as name, n.equivalent_curies as equivalent_curies return id, name, equivalent_curies"
        session = self.driver.session()
        res = session.run(query)
        drugs = pd.DataFrame(res.data())
        select_rows = [index for index in range(len(drugs.equivalent_curies)) if type(drugs.equivalent_curies[index]) is list]
        drugs = drugs.loc[select_rows,:].reset_index(drop=True)
        drugs = pd.DataFrame([(curie, drugs.loc[index, 'name']) for index in range(drugs.shape[0]) for curie in drugs.loc[index,'equivalent_curies'] if curie.upper().startswith('CHEMBL')]).rename(columns={0:'id',1:'name'})
        return drugs

    def call_oxo_API(self, uid, dist=2):
        """Call OxO (the EMBL-EBI Ontology Xref Service) API to find ontology mapping.

        Args:
            uid (str): the curie name e.g. "DRUGBANK:DB05024", "UMLS:C0876032", "UMLS:C0908863"
            dist (int): an integer indicating the max mapping distance allowed. By default this is 2. Use distance 1 for direct asserted mappings.

        Returns:
            tuple: a tuple containing curie name and its corresponding OMOP concept ids if it has mapping.
        """
        if dist != 1 and dist != 2 and dist != 3:
            print('Error occurred in calling OXO API! Only 1, 2, 3 are allowed for the distance.')
            return None

        url_str = f"https://www.ebi.ac.uk/spot/oxo/api/search?format=json&ids={uid}&distance={dist}"
        try:
            res = requests.get(url_str, timeout=120)
        except requests.exceptions.Timeout:
            print('HTTP timeout in generate_training_data.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except requests.exceptions.ConnectionError:
            print('HTTP connection error in generate_training_data.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
            res = None
        return res

    def get_all_from_oxo(self, curie_id, map_to=None, dist=2):
        """
        this takes a curie id and gets all the mappings that oxo has for the given id

        :param curie_id: The string for the curie id to submit to OXO (e.g. 'HP:0001947')
        :param map_to: A string containing the prefix for the resulting ids. If set to None it will return all mappings. (default is none)
        :param dist: an integer indicating the max mapping distance allowed. By default this is 2. Use distance 1 for direct asserted mappings.

        :return: A list of strings containing the found mapped ids or None if none where found
        """
        if type(curie_id) != str:
            curie_id = str(curie_id)
        if curie_id.startswith('REACT:'):
            curie_id = curie_id.replace('REACT', 'Reactome')
        res = self.call_oxo_API(curie_id, dist=dist)
        synonym_ids = None
        if res is not None:
            res = res.json()
            synonym_ids = set()
            synonym_ids = list(set([curie['curie'] for item in res['_embedded']['searchResults'] if len(item['mappingResponseList']) != 0 for curie in item['mappingResponseList']]))
            if map_to is not None:
                if not isinstance(map_to, list):
                    map_to = [map_to]
                synonym_ids = [curie for curie in synonym_ids if curie.split(":")[0] in map_to]
            if len(synonym_ids) == 0:
                synonym_ids = None
        return synonym_ids

    def map_drug_to_ontology(self, chembl_id, dist=2):
        """
        mapping between a drug and Disease Ontology IDs and/or Human Phenotype Ontology IDs corresponding to indications
        :param chembl_id: The CHEMBL ID for a drug
        :param dist: an integer indicating the max mapping distance allowed. By default this is 2. Use distance 1 for direct asserted mappings.
        :return: A dictionary with two fields ('indication' and 'contraindication'). Each field is a set of strings
                containing the found hp / omim / doid ids or empty set if none were found
        """
        indication_onto_set = set()
        contraindication_onto_set = set()
        if not isinstance(chembl_id, str):
            return {'indications': indication_onto_set, "contraindications": contraindication_onto_set}
        drug_use = QueryMyChem.get_drug_use(chembl_id)
        indications = drug_use['indications']
        contraindications = drug_use['contraindications']
        for indication in indications:
            if 'snomed_concept_id' in indication.keys():
                oxo_results = self.get_all_from_oxo(curie_id='SNOMEDCT:' + str(indication['snomed_concept_id']), map_to=['DOID', 'OMIM', 'HP', 'UMLS', 'MeSH', 'EFO', 'NCIT'], dist=dist)
                if oxo_results is not None:
                    for oxo_result in oxo_results:
                        indication_onto_set.add(oxo_result)

        for contraindication in contraindications:
            if 'snomed_concept_id' in contraindication.keys():
                oxo_results = self.get_all_from_oxo(curie_id='SNOMEDCT:' + str(contraindication['snomed_concept_id']), map_to=['DOID', 'OMIM', 'HP', 'UMLS', 'MeSH', 'EFO', 'NCIT'], dist=dist)
                if oxo_results is not None:
                    for oxo_result in oxo_results:
                        contraindication_onto_set.add(oxo_result)

        return {'indications': indication_onto_set, "contraindications": contraindication_onto_set}

    def generate_MyChemData(self, drugs=None, output_path=os.getcwd(), dist=2):
        """Generate MyChem Training Data"""
        # Initialized the lists used to create the dataframes
        mychem_tp_list = []
        mychem_tn_list = []
        # UMLS targets will be seperated to be converted into DOID, HP, or OMIM
        # umls_tn_list = []
        # umls_tp_list = []

        d = 0
        first_flag = True
        if drugs is None:
            drugs = self.get_drug_curies_from_graph()
        else:
            drugs = drugs
        drugs = drugs.loc[drugs["id"].str.upper().str.startswith('CHEMBL', na=False)].reset_index(drop=True)
        drugs = drugs.loc[[index for index, curie in enumerate(drugs.id) if curie.split(":")[0]!='CHEMBL.MECHANISM'],:].reset_index(drop=True)
        print("Generating MyChem Data", flush=True)
        for drug in drugs['id']:
            chembl_id = drug.split(':')[1]
            if not chembl_id.startswith('CHEMBL'):
                chembl_id = 'CHEMBL' + chembl_id
            elif chembl_id.startswith('CHEMBL.COMPOUND'):
                chembl_id = chembl_id.split(':')[1]
            res = self.map_drug_to_ontology(chembl_id, dist=dist)
            # Load indications and contraintications into their respective lists
            for ind in res['indications']:
                # if ind.startswith('UMLS:'):
                #     # umls_tp_list += [[drug, ind.split(':')[1]]]
                #     umls_tp_list += [[drug, ind]]
                # else:
                mychem_tp_list += [[drug, ind]]
            for cont in res['contraindications']:
                # if cont.startswith('UMLS:'):
                #     #umls_tn_list += [[drug, cont.split(':')[1]]]
                #     umls_tn_list += [[drug, ind]]
                # else:
                mychem_tn_list += [[drug, cont]]

            d += 1
            if d % int(len(drugs)/1000 + 1) == 0:
                # Convert lists to dataframes
                tp_df = pd.DataFrame(mychem_tp_list,columns = ['source','target'])
                tn_df = pd.DataFrame(mychem_tn_list,columns = ['source','target'])
                # umls_tp_df = pd.DataFrame(umls_tp_list,columns = ['source','target'])
                # umls_tn_df = pd.DataFrame(umls_tn_list,columns = ['source','target'])
                # Save dataframes as txt
                if first_flag:
                    tp_df.to_csv(output_path+"/mychem_tp.txt",sep='\t',index=False)
                    tn_df.to_csv(output_path+"/mychem_tn.txt",sep='\t',index=False)
                    # umls_tp_df.to_csv(output_path+"/mychem_tp_umls.txt",sep='\t',index=False)
                    # umls_tn_df.to_csv(output_path+"/mychem_tn_umls.txt",sep='\t',index=False)
                    first_flag = False
                else:
                    tp_df.to_csv(output_path+"/mychem_tp.txt",mode='a',sep='\t',header=False,index=False)
                    tn_df.to_csv(output_path+"/mychem_tn.txt",mode='a',sep='\t',header=False,index=False)
                    # umls_tp_df.to_csv(output_path+"/mychem_tp_umls.txt",mode='a',sep='\t',header=False,index=False)
                    # umls_tn_df.to_csv(output_path+"/mychem_tn_umls.txt",mode='a',sep='\t',header=False,index=False)
                # This prints percentage progress every 1%
                print(str(round((d/len(drugs))*100,2))+"%", end='..', flush=True)


        # Convert lists to dataframes
        tp_df = pd.DataFrame(mychem_tp_list,columns = ['source','target'])
        tn_df = pd.DataFrame(mychem_tn_list,columns = ['source','target'])
        # umls_tp_df = pd.DataFrame(umls_tp_list,columns = ['source','target'])
        # umls_tn_df = pd.DataFrame(umls_tn_list,columns = ['source','target'])
        # Save dataframes as txt
        tp_df.to_csv(output_path+"/mychem_tp.txt",mode='a',sep='\t',header=False,index=False)
        tn_df.to_csv(output_path+"/mychem_tn.txt",mode='a',sep='\t',header=False,index=False)
        # umls_tp_df.to_csv(output_path+"/mychem_tp_umls.txt",mode='a',sep='\t',header=False,index=False)
        # umls_tn_df.to_csv(output_path+"/mychem_tn_umls.txt",mode='a',sep='\t',header=False,index=False)

    @staticmethod
    def is_insert(line):
        """
        Returns true if the line begins a SQL insert statement.
        """
        return line.startswith('INSERT INTO') or False

    @staticmethod
    def get_values(line):
        """
        Returns the portion of an INSERT statement containing values
        """
        return line.partition('` VALUES ')[2]

    @staticmethod
    def values_sanity_check(values):
        """
        Ensures that values from the INSERT statement meet basic checks.
        """
        assert values
        assert values[0] == '('
        # Assertions have not been raised
        return True

    @staticmethod
    def parse_values(values, outfile):
        """
        Given a file handle and the raw values from a MySQL INSERT
        statement, write the equivalent CSV to the file
        """
        latest_row = []

        reader = csv.reader([values], delimiter=',',
                            doublequote=False,
                            escapechar='\\',
                            quotechar="'",
                            strict=True
        )

        writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
        for reader_row in reader:
            for column in reader_row:
                # If our current string is empty...
                if len(column) == 0 or column == 'NULL':
                    latest_row.append(chr(0))
                    continue
                # If our string starts with an open paren
                if column[0] == "(":
                    # Assume that this column does not begin
                    # a new row.
                    new_row = False
                    # If we've been filling out a row
                    if len(latest_row) > 0:
                        # Check if the previous entry ended in
                        # a close paren. If so, the row we've
                        # been filling out has been COMPLETED
                        # as:
                        #    1) the previous entry ended in a )
                        #    2) the current entry starts with a (
                        if latest_row[-1][-1] == ")":
                            # Remove the close paren.
                            latest_row[-1] = latest_row[-1][:-1]
                            new_row = True
                    # If we've found a new row, write it out
                    # and begin our new one
                    if new_row:
                        writer.writerow(latest_row)
                        latest_row = []
                    # If we're beginning a new row, eliminate the
                    # opening parentheses.
                    if len(latest_row) == 0:
                        column = column[1:]
                # Add our column to the row we're working on.
                latest_row.append(column)
            # At the end of an INSERT statement, we'll
            # have the semicolon.
            # Make sure to remove the semicolon and
            # the close paren.
            if latest_row[-1][-2:] == ");":
                latest_row[-1] = latest_row[-1][:-2]
                writer.writerow(latest_row)

    @staticmethod
    def convert_mysqldump_to_csv(mysqldump_path, to_path=os.getcwd()):
        """Converts the gzipped mysql dump from SemMedDB to a csv."""

        inputfile = gzip.open(mysqldump_path, 'r')
        sys.stdout = open(to_path + '/PREDICATION.csv', 'w')
        for line in inputfile:
            line = line.decode('utf-8')
            if DataGeneration.is_insert(line):
                values = DataGeneration.get_values(line)
                if DataGeneration.values_sanity_check(values):
                    DataGeneration.parse_values(values, sys.stdout)

    @staticmethod
    def split_df(df, columns, split_val='|'):
        df = df.assign(**{column:df[column].str.split(split_val) for column in columns})
        diff_columns = df.columns.difference(columns)
        lengths = df[columns[0]].str.len()
        if sum(lengths > 0) == len(df):
            df2 = pd.DataFrame({column:np.repeat(df[column].values, df[columns[0]].str.len()) for column in diff_columns})
            df2 = df2.assign(**{column:np.concatenate(df[column].values) for column in columns}).loc[:, df.columns]
            return df2
        else:
            df2 = pd.DataFrame({column:np.repeat(df[column].values, df[columns[0]].str.len()) for column in diff_columns})
            df2 = df2.assign(**{column:np.concatenate(df[column].values) for column in columns}).append(df.loc[lengths==0, diff_columns]).fillna('').loc[:, df.columns]
            return df2


    def generate_SemmedData(self, mysqldump_path, output_path=os.getcwd()):

        DataGeneration.convert_mysqldump_to_csv(mysqldump_path, to_path=output_path)
        if os.path.exists(output_path + '/PREDICATION.csv'):
            col_names = ['PREDICATION_ID','SENTENCE_ID','PMID','PREDICATE','SUBJECT_CUI','SUBJECT_NAME','SUBJECT_SEMTYPE','SUBJECT_NOVELTY','OBJECT_CUI', 'OBJECT_NAME', 'OBJECT_SEMTYPE', 'OBJECT_NOVELTY']
            ## these terms are promiscuous (i.e. connected to lots of things) due to them being general terms
            remove_term = ['C0012634','C0039082','C0009450','C0439064','C0011854','C0277554','C0020517','C0332307','C1442792','C0003126','C0221198']
            predication = pd.read_csv(output_path + '/PREDICATION.csv', usecols=list(range(12)), sep=',', header=None, names=col_names)
            # extracts, counts, and formats positive training data from SemMEdDB
            predication_pos_temp = predication.loc[[row=='TREATS' for row in predication['PREDICATE']]].reset_index().drop(columns=['index'])
            select_rows = [row for row in range(predication_pos_temp.shape[0]) if predication_pos_temp.loc[row,'SUBJECT_CUI'] not in remove_term and predication_pos_temp.loc[row, 'OBJECT_CUI'] not in remove_term]
            predication_pos_temp= predication_pos_temp.loc[select_rows,:]
            predication_pos = predication_pos_temp[['PMID','PREDICATE','SUBJECT_CUI','SUBJECT_NAME','OBJECT_CUI','OBJECT_NAME']]
            df_left = DataGeneration.split_df(predication_pos, ['SUBJECT_CUI','SUBJECT_NAME'])
            df2 = DataGeneration.split_df(df_left, ['OBJECT_CUI','OBJECT_NAME'])
            predication_pos = df2
            predication_pos['count'] = predication_pos['SUBJECT_CUI'] + ',' + predication_pos['OBJECT_CUI']
            predication_pos = pd.DataFrame(predication_pos['count'].value_counts()).reset_index()
            predication_pos = pd.concat([predication_pos['count'],predication_pos['index'].str.split(",",expand=True)], axis=1)
            predication_pos = predication_pos.rename(columns={0:'source',1:'target'})
            predication_pos['source'] = ['UMLS:'+umls_id for umls_id in predication_pos['source']]
            predication_pos['target'] = ['UMLS:'+umls_id for umls_id in predication_pos['target']]
            predication_pos.to_csv(output_path+'/semmed_tp.txt', sep='\t', index=None)

            # extracts, counts, and formats negative training data from SemMEdDB
            predication_neg_temp = predication.loc[[row=='NEG_TREATS' for row in predication['PREDICATE']]].reset_index().drop(columns=['index'])
            select_rows = [row for row in range(predication_neg_temp.shape[0]) if predication_neg_temp.loc[row,'SUBJECT_CUI'] not in remove_term and predication_neg_temp.loc[row, 'OBJECT_CUI'] not in remove_term]
            predication_neg_temp= predication_neg_temp.loc[select_rows,:]
            predication_neg = predication_neg_temp[['PMID','PREDICATE','SUBJECT_CUI','SUBJECT_NAME','OBJECT_CUI','OBJECT_NAME']]
            df_left = DataGeneration.split_df(predication_neg, ['SUBJECT_CUI','SUBJECT_NAME'])
            df2 = DataGeneration.split_df(df_left, ['OBJECT_CUI','OBJECT_NAME'])
            predication_neg = df2
            predication_neg['count'] = predication_neg['SUBJECT_CUI'] + ',' + predication_neg['OBJECT_CUI']
            predication_neg = pd.DataFrame(predication_neg['count'].value_counts()).reset_index()
            predication_neg = pd.concat([predication_neg['count'],predication_neg['index'].str.split(",",expand=True)], axis=1)
            predication_neg = predication_neg.rename(columns={0:'source',1:'target'})
            predication_neg['source'] = ['UMLS:'+umls_id for umls_id in predication_neg['source']]
            predication_neg['target'] = ['UMLS:'+umls_id for umls_id in predication_neg['target']]
            predication_neg.to_csv(output_path+'/semmed_tn.txt', sep='\t', index=None)

        else:
            print("Error: the 'PREDICATION.csv' file can be detected under {output_path}", flush=True)
            sys.exit(0)


if __name__ == "__main__":
    dataGenerator = DataGeneration()
    drugs = dataGenerator.get_drug_curies_from_graph()
    drugs.to_csv('/home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_5_1/raw_training_data/drugs.txt',sep='\t',index=False)
    dataGenerator.generate_MyChemData(drugs=drugs, output_path='/home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_5_1/raw_training_data/',dist=2)
    ## For semmedVER43_2020_R_PREDICATION.sql.gz, you might dowload from /data/orangeboard/databases/KG2.3.4/semmedVER43_2020_R_PREDICATION.sql.gz on arax.ncats.io server or directly download the latest one from semmedb website
    # dataGenerator.generate_SemmedData(mysqldump_path='/home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/semmedVER43_2020_R_PREDICATION.sql.gz', output_path='/home/cqm5886/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_5_1/raw_training_data/')
    
