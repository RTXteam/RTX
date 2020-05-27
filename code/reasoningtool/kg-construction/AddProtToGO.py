''' This module defines the class UpdateNodesName. UpdateNodesName class is designed
to retrieve the node name and update the name on the Graphic model object.
The available methods include:

*   update_protein_names

    Description: retrieve names from Uniprot and update protein nodes

How to run this module
        $ cd [git repo]/code/reasoningtool/kg-construction
        $ python3 UpdateNodesName.py
'''

# BEGIN config.json format
# {
#   "url":"bolt://localhost:7687"
#   "username":"xxx",
#   "password":"xxx"
# }
# END config.json format

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

from Neo4jConnection import Neo4jConnection
from QueryUniprotExtended import QueryUniprotExtended
import json
import sys
from time import time
from QueryMyGene import QueryMyGene
import requests_cache
import re, os

# configure requests package to use the "orangeboard.sqlite" cache
#requests_cache.install_cache('orangeboard')
# specifiy the path of orangeboard database
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
dbpath = os.path.sep.join([*pathlist[:(RTXindex+1)],'data','orangeboard'])
requests_cache.install_cache(dbpath)

t = time()

f = open('config.json', 'r')
config_data = f.read()
f.close()
config = json.loads(config_data)

mg = QueryMyGene()

conn = Neo4jConnection(config['url'], config['username'], config['password'])


def get_proteins(tx):
    result = tx.run("MATCH (n:protein) return n.id, n.UUID")
    return dict((record["n.id"], record["n.UUID"]) for record in result)


def get_molfunc(tx):
    result = tx.run("MATCH (n:molecular_function) return n.id, n.UUID")
    return dict((record["n.id"], record["n.UUID"]) for record in result)


def get_cellcomp(tx):
    result = tx.run("MATCH (n:cellular_component) return n.id, n.UUID")
    return dict((record["n.id"], record["n.UUID"]) for record in result)


def get_seed_node_uuid(tx):
    return next(iter(tx.run("MATCH (n:protein) return n.seed_node_uuid limit 1")))["n.seed_node_uuid"]


protein_dict = conn._driver.session().read_transaction(get_proteins)

molfunc_dict = conn._driver.session().read_transaction(get_molfunc)

cellcomp_dict = conn._driver.session().read_transaction(get_cellcomp)

seed_node_uuid = conn._driver.session().read_transaction(get_seed_node_uuid)

i = 0
for protein_curie_id, protein_uuid in protein_dict.items():
    protein_id = protein_curie_id.replace("UniProtKB:", "")
    gene_ont_info_dict = mg.get_gene_ontology_ids_for_uniprot_id(protein_id)
    for gene_ont_id, gene_ont_dict in gene_ont_info_dict.items():
        if gene_ont_dict['ont'] == 'molecular_function':
            if gene_ont_id in molfunc_dict:
                molfunc_uuid = molfunc_dict[gene_ont_id]
                if i % 100 == 0:
                    print("have inserted: " + str(i) + " relationships")
                i += 1
                cypher_query = "MATCH (a:protein),(b:molecular_function) WHERE a.id = \'" + protein_curie_id + "\' AND b.id=\'" + gene_ont_id + "\' CREATE (a)-[r:is_capable_of { is_defined_by: \'RTX\', predicate: \'is_capable_of\', provided_by: \'gene_ontology\', relation: \'is_capable_of\', seed_node_uuid: \'" + seed_node_uuid + "\', source_node_uuid: \'" + protein_uuid + "\', target_node_uuid: \'" + molfunc_uuid + "\'} ]->(b) RETURN type(r)"
#                    print(cypher_query)
                conn._driver.session().write_transaction(lambda tx: tx.run(cypher_query))
#                    print(cypher_query)
        else:
            if gene_ont_id in cellcomp_dict:
                cellcomp_uuid = cellcomp_dict[gene_ont_id]
                if i % 100 == 0:
                    print("have inserted: " + str(i) + " relationships")
                i += 1
                cypher_query = "MATCH (a:protein),(b:cellular_component) WHERE a.id = \'" + protein_curie_id + "\' AND b.id=\'" + gene_ont_id + "\' CREATE (a)-[r:expressed_in { is_defined_by: \'RTX\', predicate: \'expressed_in\', provided_by: \'gene_ontology\', relation: \'expressed_in\', seed_node_uuid: \'" + seed_node_uuid + "\', source_node_uuid: \'" + protein_uuid + "\', target_node_uuid: \'" + cellcomp_uuid + "\'} ]->(b) RETURN type(r)"
#                    print(cypher_query)
                conn._driver.session().write_transaction(lambda tx: tx.run(cypher_query))
#                    print(cypher_query)                


conn.close()

