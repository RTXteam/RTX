import sys
import os
new_path = os.path.join(os.getcwd(), '..', 'kg-construction')
sys.path.insert(0, new_path)

new_path2 = os.path.join(os.getcwd(), '..', 'SemMedDB')
sys.path.insert(0, new_path2)

from SynonymMapper import SynonymMapper
from QueryMyChem import QueryMyChem
from DrugMapper import DrugMapper
from QueryUMLSApi import QueryUMLS
import requests
import pandas
import time
import requests_cache
import numpy
import urllib
import ast

requests_cache.install_cache('MyChemCache')

df = pandas.read_csv('data/drugs.csv')
df = df.loc[df["id"].str.upper().str.startswith('CHEMBL', na=False)].reset_index(drop=True)

def map_drug_to_ontology(chembl_id):
    """
    mapping between a drug and Disease Ontology IDs and/or Human Phenotype Ontology IDs corresponding to indications

    :param chembl_id: The CHEMBL ID for a drug

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
    sm = SynonymMapper()
    for indication in indications:
        if 'snomed_concept_id' in indication.keys():
            oxo_results = sm.get_all_from_oxo('SNOMEDCT:' + str(indication['snomed_concept_id']), ['DOID', 'OMIM', 'HP'])
            if oxo_results is not None:
                for oxo_result in oxo_results:
                    indication_onto_set.add(oxo_result)
            else:
                oxo_results = sm.get_all_from_oxo('SNOMEDCT:' + str(indication['snomed_concept_id']), ['UMLS'])
                if oxo_results is not None:
                    for oxo_result in oxo_results:
                        indication_onto_set.add(oxo_result)
    for contraindication in contraindications:
        if 'snomed_concept_id' in contraindication.keys():
            oxo_results = sm.get_all_from_oxo('SNOMEDCT:' + str(contraindication['snomed_concept_id']), ['DOID', 'OMIM', 'HP'])
            if oxo_results is not None:
                for oxo_result in oxo_results:
                    contraindication_onto_set.add(oxo_result)
            else:
                oxo_results = sm.get_all_from_oxo('SNOMEDCT:' + str(contraindication['snomed_concept_id']), ['UMLS'])
                if oxo_results is not None:
                    for oxo_result in oxo_results:
                        contraindication_onto_set.add(oxo_result)
    return {'indications': indication_onto_set, "contraindications": contraindication_onto_set}

# Initialized the lists used to create the dataframes
mychem_tp_list = []
mychem_tn_list = []
# UMLS targets will be seperated to be converted into DOID, HP, or OMIM
umls_tn_list = []
umls_tp_list = []

d = 0
for drug in df['id']:
    chembl_id = drug.split(':')[1]
    if not chembl_id.startswith('CHEMBL'):
        chembl_id = 'CHEMBL' + chembl_id
    elif curie_id.startswith('CHEMBL.COMPOUND'):
        curie_id = curie_id.split(':')[1]
    res = map_drug_to_ontology(chembl_id)
    # Load indications and contraintications into their respective lists
    for ind in res['indications']:
        if ind.startswith('UMLS:'):
            umls_tp_list += [[drug,ind.split(':')[1]]]
        else:
            mychem_tp_list += [[drug,ind]]
    for cont in res['contraindications']:
        if cont.startswith('UMLS:'):
            umls_tn_list += [[drug,cont.split(':')[1]]]
        else:
            mychem_tn_list += [[drug,cont]]
    d += 1
    # This prints percentage progress every 10%. Uncomment if you want this.
    #if d % int(len(df)/10 + 1) == 0:
    #    print(d/len(df))

# Convert lists to dataframes
tp_df = pandas.DataFrame(mychem_tp_list,columns = ['source','target'])
tn_df = pandas.DataFrame(mychem_tn_list,columns = ['source','target'])
umls_tp_df = pandas.DataFrame(umls_tp_list,columns = ['source','target'])
umls_tn_df = pandas.DataFrame(umls_tn_list,columns = ['source','target'])

# Save dataframes as csvs
tp_df.to_csv("data/mychem_tp.csv",index=False)
tn_df.to_csv("data/mychem_tn.csv",index=False)
umls_tp_df.to_csv("data/mychem_tp_umls.csv",index=False)
umls_tn_df.to_csv("data/mychem_tn_umls.csv",index=False)



