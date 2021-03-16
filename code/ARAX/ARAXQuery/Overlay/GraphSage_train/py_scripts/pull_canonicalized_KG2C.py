import sys, os
import pandas as pd
from neo4j import GraphDatabase
import argparse
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

parser = argparse.ArgumentParser(description="pull canonicalized KG2", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--OutFolder', type=str, help="The path of output folder", default='~/RTX/code/reasoningtool/MLDrugRepurposing/kg2_5_0/kg2canonicalized_data/')
args = parser.parse_args()

output_path = args.OutFolder

## Connect to neo4j database
rtxc = RTXConfiguration()
rtxc.live = 'KG2c'
driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
session = driver.session()

######### Please ignore this part until Eric finds a better way to categorize these nodes with ambiguous node type ###########
# !Note: Before running the below code, please first check this DSL query, if there is returned value > 0, report error on github.
# !DSL query: match (z) where (('biolink:Disease' in z.all_categories or 'biolink:PhenotypicFeature' in z.all_categories or 'biolink:DiseaseOrPhenotypicFeature' in z.all_categories) and ('biolink:Drug' in z.all_categories or 'biolink:ChemicalSubstance' in z.all_categories)) return count(distinct z.id)
##############################################################################################################################


## Pull a dataframe of all of the graph edges excluding:
# the edges with one end node with all_categories including 'drug' and another end node with all_categories including 'disease'
# 'drug' here represents all nodes with cateory that is either 'biolink:Drug' or 'biolink:ChemicalSubstance'
# 'disease' here represents all nodes with cateory that is either 'biolink:Disease'. 'biolink:PhenotypicFeature' or 'biolink:DiseaseOrPhenotypicFeature'
query = "match (disease) where ('biolink:Disease' in disease.all_categories or 'biolink:PhenotypicFeature' in disease.all_categories or 'biolink:DiseaseOrPhenotypicFeature' in disease.all_categories) with collect(distinct disease.id) as disease_ids match (drug) where ('biolink:Drug' in drug.all_categories or 'biolink:ChemicalSubstance' in drug.all_categories) with collect(distinct drug.id) as drug_ids, disease_ids as disease_ids match (m1)-[]-(m2) where m1<>m2 and not (m1.id in drug_ids and m2.id in disease_ids) and not (m1.id in disease_ids and m2.id in drug_ids) with distinct m1 as node1, m2 as node2 return node1.id as source, node2.id as target"
res = session.run(query)
KG2_alledges = pd.DataFrame(res.data())
KG2_alledges.to_csv(output_path + 'graph_edges.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph nodes with category label
query = "match (n) with distinct n.id as id, n.name as name, n.category as category return id, name, category"
res = session.run(query)
KG2_allnodes_label = pd.DataFrame(res.data())
KG2_allnodes_label = KG2_allnodes_label.iloc[:, [0, 2]]
KG2_allnodes_label.to_csv(output_path + 'graph_nodes_label_remove_name.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph drug-associated nodes
query = f"match (n) where ('biolink:Drug' in n.all_categories) or ('biolink:ChemicalSubstance' in n.all_categories) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
drugs = pd.DataFrame(res.data())
drugs.to_csv(output_path + 'drugs.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph disease and phenotype nodes
query = "match (n) where ('biolink:PhenotypicFeature' in n.all_categories) or ('biolink:Disease' in n.all_categories) or ('biolink:DiseaseOrPhenotypicFeature' in n.all_categories) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
diseases = pd.DataFrame(res.data())
diseases.to_csv(output_path + 'diseases.txt', sep='\t', index=None)
