import sys, os
import pandas as pd
import pickle
from neo4j import GraphDatabase
import argparse
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer
fpath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])

parser = argparse.ArgumentParser(description="Generate a .pkl file for OMOP_mapping_parallel.py to map concepts", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--NodeDescriptionFile', type=str, help="The path of Node Descriptions file", default='~/RTX/data/KGmetadata/NodeNamesDescriptions_KG2.tsv')
parser.add_argument("--CurieType", type=str, help="A list of interested curie type", default="['biolink:Disease', 'biolink:PhenotypicFeature', 'biolink:ChemicalSubstance', 'biolink:Drug', 'biolink:DiseaseOrPhenotypicFeature']")
parser.add_argument('--OutFile', type=str, help="The path of output .pkl file", default='~/RTX/code/ARAX/KnowledgeSources/COHD_local/data/preferred_synonyms_kg2_5_0.pkl')
args = parser.parse_args()

curie_type = eval(args.CurieType)
NodeNamesDescriptions = pd.read_csv(args.NodeDescriptionFile, sep='\t', header=None, names=['curie', 'name', 'full_name', 'type'])
NodeNamesDescriptions = NodeNamesDescriptions.loc[NodeNamesDescriptions.type.isin(curie_type),:].reset_index(drop=True)

preferred_synonyms = dict()
synonymizer = NodeSynonymizer()

for curie in NodeNamesDescriptions['curie']:
    preferred_curie = synonymizer.get_canonical_curies(curies=curie)[curie]
    if preferred_curie is None:
        print(f"{curie} doesn't have preferred curies", flush=True)
    else:
        if preferred_curie['preferred_curie'] not in preferred_synonyms:
            preferred_synonyms[preferred_curie['preferred_curie']] = dict()
            preferred_synonyms[preferred_curie['preferred_curie']]['preferred_name'] = preferred_curie['preferred_name']
            preferred_synonyms[preferred_curie['preferred_curie']]['preferred_type'] = preferred_curie['preferred_category']
            preferred_synonyms[preferred_curie['preferred_curie']]['synonyms'] = [curie]
        else:
            synonyms = set(preferred_synonyms[preferred_curie['preferred_curie']]['synonyms'])
            synonyms.update(set([curie]))
            preferred_synonyms[preferred_curie['preferred_curie']]['synonyms'] = list(synonyms)

with open(args.OutFile, "wb") as file:
    pickle.dump(preferred_synonyms, file)

