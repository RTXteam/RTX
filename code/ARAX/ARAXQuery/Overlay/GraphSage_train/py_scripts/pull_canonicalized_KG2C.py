import sys, os
import pandas as pd
from neo4j import GraphDatabase
import argparse
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

parser = argparse.ArgumentParser(description="pull canonicalized KG2", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--OutFolder', type=str, help="The path of output folder", default='~/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_5_0/kg2canonicalized_data/')
args = parser.parse_args()

output_path = args.OutFolder

## Connect to neo4j database
rtxc = RTXConfiguration()
rtxc.live = 'KG2C'
driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
session = driver.session()

## Pull a dataframe of all of the graph edges excluding 
# 1. the nodes which are both 'drug' and 'disease'
# 2. the nodes with type including 'drug' and 'disease' != preferred_type
# 3. all edges directly connecting 'drug' and 'disease'
query = "match (n) where (((n.preferred_type<>'biolink:Disease' and n.preferred_type<>'biolink:PhenotypicFeature' and n.preferred_type<>'biolink:DiseaseOrPhenotypicFeature') and ('biolink:Disease' in n.types or 'biolink:PhenotypicFeature' in n.types or 'biolink:DiseaseOrPhenotypicFeature' in n.types)) or ((n.preferred_type<>'biolink:Drug' and n.preferred_type<>'biolink:ChemicalSubstance') and ('biolink:Drug' in n.types or 'biolink:ChemicalSubstance' in n.types))) or (('biolink:Disease' in n.types or 'biolink:PhenotypicFeature' in n.types or 'biolink:DiseaseOrPhenotypicFeature' in n.types) and ('biolink:Drug' in n.types or 'biolink:ChemicalSubstance' in n.types)) with COLLECT(DISTINCT n.id) as exclude_id match (m1)-[]-(m2) where m1<>m2 and not m1.id in exclude_id and not m2.id in exclude_id and not ((m1.preferred_type='biolink:Disease' or m1.preferred_type='biolink:PhenotypicFeature' or m1.preferred_type='biolink:DiseaseOrPhenotypicFeature') and (m2.preferred_type='biolink:Drug' or m2.preferred_type='biolink:ChemicalSubstance')) and not ((m1.preferred_type='biolink:Drug' or m1.preferred_type='biolink:ChemicalSubstance') and (m2.preferred_type='biolink:Disease' or m2.preferred_type='biolink:PhenotypicFeature' or m2.preferred_type='biolink:DiseaseOrPhenotypicFeature')) with distinct m1 as node1, m2 as node2 return node1.id as source, node2.id as target"
res = session.run(query)
KG2_alledges = pd.DataFrame(res.data())
KG2_alledges.to_csv(output_path + 'graph_edges.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph nodes with category label
query = "match (n) with distinct n.id as id, n.name as name, n.preferred_type as category return id, name, category"
res = session.run(query)
KG2_allnodes_label = pd.DataFrame(res.data())
KG2_allnodes_label = KG2_allnodes_label.iloc[:, [0, 2]]
KG2_allnodes_label.to_csv(output_path + 'graph_nodes_label_remove_name.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph drug-associated nodes
query = f"match (n:`biolink:ChemicalSubstance`) with distinct n.id as id, n.name as name return id, name union match (n:`biolink:Drug`) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
drugs = pd.DataFrame(res.data())
drugs.to_csv(output_path + 'drugs.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph disease and phenotype nodes
query = "match (n:`biolink:PhenotypicFeature`) with distinct n.id as id, n.name as name return id, name union match (n:`biolink:Disease`) with distinct n.id as id, n.name as name return id, name union match (n:`biolink:DiseaseOrPhenotypicFeature`) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
diseases = pd.DataFrame(res.data())
diseases.to_csv(output_path + 'diseases.txt', sep='\t', index=None)
