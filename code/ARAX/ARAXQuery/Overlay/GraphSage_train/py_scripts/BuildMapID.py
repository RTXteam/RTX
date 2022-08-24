## This script is used to map the raw training data to the drug and disease nodes in the graph via NodeSynonymizer
import pandas as pd
import argparse
import os
import sys

# import internal modules
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer
from multiprocessing import Pool

# The following parses the arguments entered into the terminal:
parser = argparse.ArgumentParser(description='This script is used to map the raw training data to the drug and disease nodes in the graph via NodeSynonymizer')
parser.add_argument("--path", type=str, help="The full path of raw training data folder")
parser.add_argument("--thread", type=int, help="Number of processes to use")

args = parser.parse_args()
nodesynonymizer = NodeSynonymizer()

def map_to_graph(row):

    if len(row) == 2:
        drug, disease = row
        try:
            res = nodesynonymizer.get_canonical_curies(drug)[drug]
        except:
            res = None
        preferred_drug_curie = res['preferred_curie'] if (res is not None) and (res['preferred_category']=='biolink:Drug' or res['preferred_category']=='biolink:SmallMolecule') else None
        try:
            res = nodesynonymizer.get_canonical_curies(disease)[disease]
        except:
            res = None
        preferred_disease_curie = res['preferred_curie'] if (res is not None) and (res['preferred_category']=='biolink:Disease' or res['preferred_category']=='biolink:PhenotypicFeature' or res['preferred_category']=='biolink:DiseaseOrPhenotypicFeature' or res['preferred_category']=='biolink:ClinicalFinding' or res['preferred_category']=='biolink:BehavioralFeature') else None
        return [preferred_drug_curie, preferred_disease_curie]
    elif len(row) == 3:
        count, drug, disease = row
        try:
            res = nodesynonymizer.get_canonical_curies(drug)[drug]
        except:
            res = None
        preferred_drug_curie = res['preferred_curie'] if (res is not None) and (res['preferred_category']=='biolink:Drug' or res['preferred_category']=='biolink:SmallMolecule') else None
        try:
            res = nodesynonymizer.get_canonical_curies(disease)[disease]
        except:
            res = None
        preferred_disease_curie = res['preferred_curie'] if (res is not None) and (res['preferred_category']=='biolink:Disease' or res['preferred_category']=='biolink:PhenotypicFeature' or res['preferred_category']=='biolink:DiseaseOrPhenotypicFeature' or res['preferred_category']=='biolink:ClinicalFinding' or res['preferred_category']=='biolink:BehavioralFeature') else None
        return [count, preferred_drug_curie, preferred_disease_curie]

def test(row):
    if len(row) == 2:
        print(row, flush=True)
    else:
        print(row, flush=True)

files = os.listdir(args.path)
for file_name in files:
    raw_data = pd.read_csv(args.path + '/' + file_name, sep='\t', header=0)
    with Pool(processes=args.thread) as executor:
        res = [elem for elem in executor.map(map_to_graph, raw_data.to_numpy())]
    res = pd.DataFrame(res)
    if res.shape[1] == 2:
        res = res.dropna().rename(columns={0:'source',1:'target'})
        res = res.drop_duplicates()
    elif res.shape[1] == 3:
        res = res.dropna().rename(columns={0:'count',1:'source',2:'target'})
        res = res.drop_duplicates()
    res.to_csv(args.path + '/' + file_name, sep='\t', index=None)
