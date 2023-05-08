
"""
This script is used to build a database for mapping the nodes and edges in the predicted paths generated from KGML-xDTD model to the original KG2 graph.
Author: Chunyu Ma
"""

import os, sys
import pandas as pd
import numpy as np
import argparse
from tqdm import tqdm
import sqlite3
import csv
csv.field_size_limit(sys.maxsize)
import collections

class xDTDMappingDB():
    
    # Constructor
    def __init__(self, kgml_xdtd_data_path=None, tsv_path=None, database_name='xdtd_mapping.db', outdir=None, mode='build', db_loc=None):
        """
        Args:
            kgml_xdtd_data_path (str): path to a folder containing data to generate KGML-xDTD model
            tsv_path (str): path to a folder containing KG2 TSV files
            database_name (str, optional): database name (Defaults: xdtd_mapping.db).
            outdir (str, optional): path to a folder where the database is generated (Defaults: ./).
            mode (str, optional): mode to build the database (Defaults: build).
        """

        if mode == 'build':
            if not os.path.exists(kgml_xdtd_data_path):
                print(f"Error: The given path '{kgml_xdtd_data_path}' doesn't exist.", flush=True)
                raise
            else:
                self.kgml_xdtd_data_path = kgml_xdtd_data_path
            if not os.path.exists(tsv_path):
                print(f"Error: The given path '{tsv_path}' doesn't exist.", flush=True)
                raise
            else:
                self.tsv_path = tsv_path

            self.database_name = database_name
            
            # Create output directory if it doesn't exist
            if outdir is None:
                self.database_name = './'
            else:
                if not os.path.exists(outdir):
                    os.makedirs(outdir)

            # Create a database connection
            db_path = os.path.join(outdir, self.database_name)
            self.success_con = self._connect(db_path)
        elif mode == 'run':
            if db_loc is None:
                print(f"Error: The given path '{db_loc}' doesn't exist.", flush=True)
                raise
            else:
                db_path = os.path.join(db_loc, database_name)
                self.success_con = self._connect(db_path)
            
        
    def __del__(self):
        self._disconnect()

    # Create and store a database connection
    def _connect(self, db_path):

        if os.path.exists(db_path):
            self.connection = sqlite3.connect(db_path)
            print("Connecting to database", flush=True)
            return True
        else:
            self.connection = sqlite3.connect(db_path)
            print("INFO: Connecting to database", flush=True)
            return True
        
    # Destroy the database connection
    def _disconnect(self):

        if self.success_con is True:
            self.connection.commit()
            self.connection.close()
            print("Disconnecting from database", flush=True)
            self.success_con = False
        else:
            print("No database was connected! So skip disconnecting from database.", flush=True)
            return
        
    # Delete and create the tables
    def create_tables(self):

        if self.success_con is True:
            print(f"Creating database {self.database_name}", flush=True)
            self.connection.execute(f"DROP TABLE IF EXISTS NODE_MAPPING_TABLE")
            self.connection.execute(f"CREATE TABLE NODE_MAPPING_TABLE( id VARCHAR(255), name VARCHAR, category VARCHAR(255), iri VARCHAR(255), description VARCHAR, all_categories VARCHAR, all_names VARCHAR, equivalent_curies VARCHAR, publications VARCHAR)")
            self.connection.execute(f"DROP TABLE IF EXISTS EDGE_MAPPING_TABLE")
            self.connection.execute(f"CREATE TABLE EDGE_MAPPING_TABLE( triple VARCHAR(255), subject VARCHAR(255), object VARCHAR(255), predicate VARCHAR(255), knowledge_source VARCHAR, publications VARCHAR, publications_info VARCHAR, kg2_ids VARCHAR(255))")
            print(f"Creating tables is completed", flush=True)
            
    ## Populate the tables
    def populate_table(self):

        if self.success_con is True:
            
            ## load kgml_xdtd data
            print("Loading KGML-xDTD data...", flush=True)
            kgml_xdtd_graph_nodes = pd.read_csv(os.path.join(self.kgml_xdtd_data_path, 'entity2freq.txt'), sep='\t', header=None).drop(columns=[1])
            kgml_xdtd_graph_edges = pd.read_csv(os.path.join(self.kgml_xdtd_data_path, 'graph_edges.txt'), sep='\t', header=0)
            kgml_xdtd_graph_edges_dict = {(row[0],row[2],row[1]):1 for row in kgml_xdtd_graph_edges.to_numpy()}
            # kgml_xdtd_graph_edges_dict = {}
            # for row in tqdm(kgml_xdtd_graph_edges.to_numpy()):
            #     if row[2] == 'biolink:entity_regulates_entity':
            #         kgml_xdtd_graph_edges_dict.update({(row[0], row[2], row[1]):1})
            #         kgml_xdtd_graph_edges_dict.update({(row[0], 'biolink:regulates', row[1]):1})
            #     if row[2] == 'biolink:entity_positively_regulates_entity':
            #         kgml_xdtd_graph_edges_dict.update({(row[0], row[2], row[1]):1})
            #         kgml_xdtd_graph_edges_dict.update({(row[0], 'biolink:positively_regulates', row[1]):1})
            #     if row[2] == 'biolink:entity_negatively_regulates_entity':
            #         kgml_xdtd_graph_edges_dict.update({(row[0], row[2], row[1]):1})
            #         kgml_xdtd_graph_edges_dict.update({(row[0], 'biolink:negatively_regulates', row[1]):1})
            #     if row[2] == 'biolink:related_to':
            #         kgml_xdtd_graph_edges_dict.update({(row[0], row[2], row[1]):1})
            #         kgml_xdtd_graph_edges_dict.update({(row[0], 'biolink:has_count', row[1]):1})
            #         kgml_xdtd_graph_edges_dict.update({(row[0], 'biolink:has_quantitative_value', row[1]):1})
            #         kgml_xdtd_graph_edges_dict.update({(row[0], 'biolink:has_unit', row[1]):1})
            #         kgml_xdtd_graph_edges_dict.update({(row[0], 'biolink:quantifier_qualifier', row[1]):1})
            
            ## load kg2 tsv data
            # Read node header file
            print("Reading node header file...", flush=True)
            header_file = os.path.join(self.tsv_path, 'nodes_c_header.tsv')
            with open(header_file, 'r', encoding='utf-8') as header_tsv:
                header_reader = csv.reader(header_tsv, delimiter='\t')
                headers = next(header_reader)
                headers = [x.replace(':string[]','').replace(':ID','') for x in headers]
                
            # Read node file
            print("Reading node file...", flush=True)
            data_file = os.path.join(self.tsv_path, 'nodes_c.tsv')
            with open(data_file, 'r', encoding='utf-8') as data_tsv:
                data_reader = csv.reader(data_tsv, delimiter='\t')
                tsv_node_df = pd.DataFrame([row for row in data_reader])
                tsv_node_df.columns = headers
                tsv_node_df = tsv_node_df[['id','name','category','iri','description','all_categories','all_names','equivalent_curies','publications']]
                tsv_node_df = tsv_node_df.loc[tsv_node_df['id'].isin(list(kgml_xdtd_graph_nodes[0])),:].reset_index(drop=True)
    
            # Read edge header file
            print("Reading edge header file...", flush=True)
            header_file = os.path.join(self.tsv_path, 'edges_c_header.tsv')
            with open(header_file, 'r', encoding='utf-8') as header_tsv:
                header_reader = csv.reader(header_tsv, delimiter='\t')
                headers = next(header_reader)
                headers = [x.replace(':string[]','').replace(':ID','') for x in headers]
                
            # Read edge file
            print("Reading edge file...", flush=True)
            data_file = os.path.join(self.tsv_path, 'edges_c.tsv')
            with open(data_file, 'r', encoding='utf-8') as data_tsv:
                data_reader = csv.reader(data_tsv, delimiter='\t')
                tsv_edge_df = pd.DataFrame([row for row in data_reader])
                tsv_edge_df.columns = headers
                tsv_edge_df = tsv_edge_df[['subject','object','predicate','knowledge_source','publications','publications_info','kg2_ids']]
    
            ## Insert node information into database
            print("Inserting into NODE_MAPPING_TABLE...", flush=True)
            for row in tqdm(tsv_node_df.to_numpy()):
                ## insert into database
                insert_command = f"INSERT INTO NODE_MAPPING_TABLE values (?,?,?,?,?,?,?,?,?)"    
                self.connection.execute(insert_command, tuple(row))
            print(f"Inserting into NODE_MAPPING_TABLE is completed")
            self.connection.commit()
            
            ## Intert edge information into database
            print("Inserting into EDGE_MAPPING_TABLE...", flush=True)
            for row in tqdm(tsv_edge_df.to_numpy()):
                if (row[0], row[2], row[1]) in kgml_xdtd_graph_edges_dict:
                    ## intsert into database
                    row = [f"{row[0]}--{row[2]}--{row[1]}"] + list(row)
                    insert_command = f"INSERT INTO EDGE_MAPPING_TABLE values (?,?,?,?,?,?,?,?)"
                    self.connection.execute(insert_command, tuple(row))
            print(f"Inserting into EDGE_MAPPING_TABLE is completed", flush=True)
            self.connection.commit()

            print(f"Populating tables is completed", flush=True)


    def create_indexes(self):

        if self.success_con is True:
            print(f"Creating INDEXes on NODE_MAPPING_TABLE", flush=True)
            self.connection.execute(f"CREATE INDEX idx_NODE_MAPPING_TABLE_id ON NODE_MAPPING_TABLE(id)")
            self.connection.execute(f"CREATE INDEX idx_NODE_MAPPING_TABLE_name ON NODE_MAPPING_TABLE(name)")

            print(f"Creating INDEXes on EDGE_MAPPING_TABLE", flush=True)
            self.connection.execute(f"CREATE INDEX idx_EDGE_MAPPING_TABLE_triple ON EDGE_MAPPING_TABLE(triple)")
            self.connection.execute(f"CREATE INDEX idx_EDGE_MAPPING_TABLE_subject ON EDGE_MAPPING_TABLE(subject)")
            self.connection.execute(f"CREATE INDEX idx_EDGE_MAPPING_TABLE_object ON EDGE_MAPPING_TABLE(object)")
            self.connection.execute(f"CREATE INDEX idx_EDGE_MAPPING_TABLE_predicate ON EDGE_MAPPING_TABLE(predicate)")

            print(f"INFO: Creating INDEXes is completed", flush=True)
            
    def get_node_info(self, node_id = None, node_name = None):
        
        res = collections.namedtuple('res', ['id', 'name', 'category', 'iri', 'description', 'all_categories', 'all_names', 'equivalent_curies', 'publications'])
        
        ## connect to database
        cursor = self.connection.cursor()
        if node_id is not None and type(node_id) == str:
            query = f"SELECT * FROM NODE_MAPPING_TABLE WHERE id = '{node_id}'"
            cursor.execute(query)
            ## create a named tuple
            res = res._make(cursor.fetchone())
            return res
        elif node_name is not None and type(node_name) == str:
            query = f"SELECT * FROM NODE_MAPPING_TABLE WHERE name = '{node_name}'"
            cursor.execute(query)
            ## create a named tuple
            res = res._make(cursor.fetchone())
            return res
        else:
            return None
        
    def get_edge_info(self, triple_id = None, triple_name = None):

        res = collections.namedtuple('res', ['triple', 'subject', 'object', 'predicate', 'knowledge_source', 'publications', 'publications_info', 'kg2_ids'])
        
        ## connect to database
        cursor = self.connection.cursor()
        if triple_id is not None and type(triple_id) == tuple:
            subject_id, predicate, object_id = triple_id
            if predicate != 'SELF_LOOP_RELATION':
                query = f"SELECT * FROM EDGE_MAPPING_TABLE WHERE triple = '{subject_id}--{predicate}--{object_id}'"
                cursor.execute(query)
                ## create a named tuple
                res = res._make(cursor.fetchone())
            else:
                res = res._make((subject_id, object_id, predicate, None, None))
            return res
        elif triple_name is not None and type(triple_name) == tuple:
            subject_name, predicate, object_name = triple_name
            subject_info = self.get_node_info(node_name=subject_name)
            subject_id = subject_info.id
            object_info = self.get_node_info(node_name=object_name)
            object_id = object_info.id
            if predicate != 'SELF_LOOP_RELATION':
                query = f"SELECT * FROM EDGE_MAPPING_TABLE WHERE triple = '{subject_id}--{predicate}--{object_id}'"
                cursor.execute(query)
                ## create a named tuple
                res = res._make(cursor.fetchone())
            else:
                res = res._make(('{subject_id}--{predicate}--{object_id}', subject_id, object_id, predicate, None, None, None, None))
            return res
        else:
            return None
            

####################################################################################################

def main():
    parser = argparse.ArgumentParser(description="Tests or builds the KGML-xDTD model Mapping Database", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--build', action="store_true", required=False, help="If set, (re)build the index from scratch", default=False)
    parser.add_argument('--test', action="store_true", required=False, help="If set, run a test of database by doing several lookups", default=False)
    parser.add_argument('--tsv_path', type=str, required=True, help="Path to a folder containing the KG2 graph TSV files")
    parser.add_argument('--kgml_xdtd_data_path', type=str, required=True, help="Path to a folder containing the KGML-xDTD data files")
    parser.add_argument('--database_name', type=str, required=False, help="Name of the database file", default="ExplainableDTD_v1.0_KG2.8.0.db")
    parser.add_argument('--outdir', type=str, required=False, help="Path to the output directory", default=".")
    args = parser.parse_args()        

    if not args.build and not args.test:
        parser.print_help()
        sys.exit(2)

    # To (re)build
    if args.build:
        db = xDTDMappingDB(args.kgml_xdtd_data_path, args.tsv_path, args.database_name, args.outdir, mode='build', db_loc=None)
        print("==== Creating tables ====", flush=True)
        db.create_tables()
        print("==== Populating tables ====", flush=True)
        db.populate_table()
        print("==== Creating indexes ====", flush=True)
        db.create_indexes()
        exit(0)

    # To test
    if args.test:
        db = xDTDMappingDB(args.kgml_xdtd_data_path, args.tsv_path, args.database_name, args.outdir, mode='run', db_loc=args.outdir)

    print("==== Testing for search for node by name ====", flush=True)
    print(db.get_node_info(node_id='KEGG.ENZYME:6.2.1.73'), flush=True)
    # res(id='KEGG.ENZYME:6.2.1.73', name='L-tryptophan---[L-tryptophyl-carrier protein] ligase', category='biolink:MolecularEntity', iri='https://identifiers.org/kegg.enzyme:6.2.1.73', description='', all_categories='biolink:MolecularEntity', all_names='L-tryptophan---[L-tryptophyl-carrier protein] ligase', equivalent_curies='KEGG.ENZYME:6.2.1.73', publications='PMID:23437232')
    print(db.get_node_info(node_name='Accessory carpal bones'), flush=True)
    # res(id='UMLS:C0265609', name='Accessory carpal bones', category='biolink:Disease', iri='https://identifiers.org/umls:C0265609', description='The presence of more than the normal number of carpal bones. [HPO:curators]; The presence of more than the normal number of carpal bones.; UMLS Semantic Type: UMLSSC:T019', all_categories='biolink:Diseaseǂbiolink:PhenotypicFeature', all_names='Accessory carpal bones', equivalent_curies='HP:0004232ǂICD9:755.56ǂUMLS:C0265609', publications='')

    print("==== Testing for search for edge ====", flush=True)
    print(db.get_edge_info(triple_id=('KEGG.ENZYME:6.2.1.73', 'biolink:catalyzes', 'KEGG.REACTION:R12784')), flush=True)
    # res(triple='KEGG.ENZYME:6.2.1.73--biolink:catalyzes--KEGG.REACTION:R12784', subject='KEGG.ENZYME:6.2.1.73', object='KEGG.REACTION:R12784', predicate='biolink:catalyzes', knowledge_source='infores:kegg', publications='', publications_info='{}', kg2_ids='KEGG.REACTION:R12784---KEGG:reaction_to_enzyme---KEGG.ENZYME:6.2.1.73---KEGG_source:')
    print(db.get_edge_info(triple_name=('NITISINONE', 'biolink:entity_negatively_regulates_entity', 'HPD')), flush=True)
    # res(triple='CHEMBL.COMPOUND:CHEMBL1337--biolink:entity_negatively_regulates_entity--UniProtKB:P32754', subject='CHEMBL.COMPOUND:CHEMBL1337', object='UniProtKB:P32754', predicate='biolink:entity_negatively_regulates_entity', knowledge_source='infores:drugcentralǂinfores:chemblǂinfores:semmeddbǂinfores:drugbank', publications='PMID:10370811ǂPMID:14668946ǂPMID:12142814ǂPMID:15931605ǂPMID:25628464ǂPMID:15931360ǂhttp://www.accessdata.fda.gov/drugsatfda_docs/label/2014/021232s013lbl.pdfǂPMID:18422479ǂPMID:31611405ǂPMID:11752352ǂPMID:27305933ǂPMID:9728331', publications_info="{'PMID:9728331': {'publication date': '1998 Aug', 'sentence': 'NTBC is a potent inhibitor of 4-hydroxyphenylpyruvate dioxygenase and has been shown to efficiently prevent tyrosine degradation, and production of succinylacetone, in patients with tyrosinaemia.', 'subject score': 1000, 'object score': 1000}, 'PMID:15931360': {'publication date': '2004 Nov', 'sentence': 'Nitisinone, a potent inhibitor of 4-hydroxyphenylpyruvate dioxygenase, dramatically reduces production and urinary excretion of homogentisic acid; however, the long-term efficacy and side effects of such therapy are unknown.', 'subject score': 1000, 'object score': 1000}, 'PMID:27305933': {'publication date': '2017 09 01', 'sentence': 'Nitisinone or 2-(2-nitro-4-trifluoromethylbenzoyl)cyclohexane-1,3-dione is a reversible inhibitor of 4-hydroxyphenylpyruvate dioxygenase (HPPD), an enzyme important in tyrosine catabolism.', 'subject score': 1000, 'object score': 1000}, 'PMID:10370811': {'publication date': '1999 May', 'sentence': 'NTBC, which acts as an inhibitor of the 4-hydroxyphenylpyruvate dioxygenase, prevents the formation of toxic metabolites involved in hepatic, renal and neurologic lesions.', 'subject score': 1000, 'object score': 1000}, 'PMID:25628464': {'publication date': '2015 Sep', 'sentence': 'Treatment with the orphan drug, nitisinone, an inhibitor of 4-hydroxyphenylpyruvate dioxygenase has been shown to reduce urinary excretion of homogentisic acid.', 'subject score': 1000, 'object score': 1000}, 'PMID:31611405': {'publication date': '2019 Oct 29', 'sentence': 'Interestingly, these behavioral phenotypes became milder as the mice grew older and were completely rescued by the administration of NTBC [2-(2-nitro-4-trifluoromethylbenzoyl)-1,3-cyclohexanedione], an inhibitor of 4-hydroxyphenylpyruvate dioxygenase, which is upstream of FAH.', 'subject score': 1000, 'object score': 1000}}", kg2_ids='UMLS:C0173083---SEMMEDDB:inhibits---UMLS:C0000507---SEMMEDDB:ǂCHEMBL.COMPOUND:CHEMBL1337---CHEMBL.MECHANISM:inhibitor---CHEMBL.TARGET:CHEMBL1861---identifiers_org_registry:chembl.compoundǂDRUGBANK:DB00348---DRUGBANK:inhibitor---UniProtKB:P32754---identifiers_org_registry:drugbankǂDrugCentral:1944---DrugCentral:inhibitor---UniProtKB:P32754---DrugCentral:')

####################################################################################################

if __name__ == "__main__":
    main()