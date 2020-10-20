import sys, os
import pandas as pd
from neo4j import GraphDatabase
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

output_path = '~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2_3_4/kg2canonicalized_data/'

## Connect to neo4j database
rtxc = RTXConfiguration()
driver = GraphDatabase.driver("bolt://kg2canonicalized2.rtx.ai:7687", auth=(rtxc.neo4j_username, rtxc.neo4j_password))
session = driver.session()

## Pull a dataframe of all of the graph edges excluding 
# 1. the nodes which are both 'drug' and 'disease'
# 2. the nodes with type including 'drug' and 'disease' != preferred_type
# 3. all edges directly connecting 'drug' and 'disease'
query = "match (n) where (((n.preferred_type<>'disease' and n.preferred_type<>'phenotypic_feature' and n.preferred_type<>'disease_or_phenotypic_feature') and ('disease' in n.types or 'phenotypic_feature' in n.types or 'disease_or_phenotypic_feature' in n.types)) or ((n.preferred_type<>'drug' and n.preferred_type<>'chemical_substance') and ('drug' in n.types or 'chemical_substance' in n.types))) or (('disease' in n.types or 'phenotypic_feature' in n.types or 'disease_or_phenotypic_feature' in n.types) and ('drug' in n.types or 'chemical_substance' in n.types)) with COLLECT(DISTINCT n.id) as exclude_id match (m1)-[]-(m2) where m1<>m2 and not m1.id in exclude_id and not m2.id in exclude_id and not ((m1.preferred_type='disease' or m1.preferred_type='phenotypic_feature' or m1.preferred_type='disease_or_phenotypic_feature') and (m2.preferred_type='drug' or m2.preferred_type='chemical_substance')) and not ((m1.preferred_type='drug' or m1.preferred_type='chemical_substance') and (m2.preferred_type='disease' or m2.preferred_type='phenotypic_feature' or m2.preferred_type='disease_or_phenotypic_feature')) with distinct m1 as node1, m2 as node2 return node1.id as source, node2.id as target"
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
query = f"match (n:chemical_substance) with distinct n.id as id, n.name as name return id, name union match (n:drug) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
drugs = pd.DataFrame(res.data())
drugs.to_csv(output_path + 'drugs.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph disease and phenotype nodes
query = "match (n:phenotypic_feature) with distinct n.id as id, n.name as name return id, name union match (n:disease) with distinct n.id as id, n.name as name return id, name union match (n:disease_or_phenotypic_feature) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
diseases = pd.DataFrame(res.data())
diseases.to_csv(output_path + 'diseases.txt', sep='\t', index=None)
