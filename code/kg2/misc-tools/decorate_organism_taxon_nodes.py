#!/usr/bin/env python3
''' Decorates organism taxon nodes with the organism types

    Usage: decorate_organisms.py [-u <neo4j user>] [-p <neo4j password>] [-b <neo4j bolt address>]
'''

import argparse
import neo4j
import getpass
import sys
import os
import json
import ontobio


pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

# sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
# print(os.path.dirname(os.path.abspath(__file__))+"/../../")
# sys.path.append(os.getcwd()+"/..")
from RTXConfiguration import RTXConfiguration

__author__ = 'Finn Womack'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Erica Wood', 'Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

laymen_names = {
"Cryptophyceae":"microbial",
"Sar":"microbial",
"Amoebozoa":"microbial",
"Metamonada":"microbial",
"Glaucocystophyceae":"microbial",
"Discoba":"microbial",
"Viridiplantae":"plant",
"Fungi":"fungi",
"Choanoflagellata":"microbial",
"Filasterea":"microbial",
"Metazoa":"animal",
"Opisthokonta incertae sedis":"microbial",
"Ichthyosporea":"microbial",
"Haptista":"microbial",
"Rhodophyta":"microbial"
}


def query_partition(node_id_list, batch_size, organism):
    for i in range(0, len(node_id_list), batch_size):
        yield f"MATCH (n:`biolink:OrganismTaxon`) where n.id in {node_id_list[i:i + batch_size]} SET n.organism_type = '"+organism+"' RETURN n.organism_type"
        #yield " union ".join([f"MATCH (n:organism_taxon {{ id: '{node_id}' }}) SET n.organism_type = '"+organism+"' RETURN n.organism_type" for node_id in node_id_list[i:i + batch_size]])

class DecorateOTNodes:
    def __init__(self, neo4j_user, neo4j_password, neo4j_bolt, neo4j_live, taxslim):
        if None in [neo4j_user, neo4j_password, neo4j_bolt]:
            RTXConfig = RTXConfiguration()
            RTXConfig.live = neo4j_live
        if neo4j_user is None:
            self.neo4j_user = RTXConfig.neo4j_username
        else:
            self.neo4j_user = neo4j_user
        if neo4j_password is None:
            self.neo4j_password = RTXConfig.neo4j_password
        else:
            self.neo4j_password = neo4j_password
        if neo4j_bolt is None:
            self.neo4j_bolt = RTXConfig.neo4j_bolt
        else:
            self.neo4j_bolt = neo4j_bolt
        self.driver = neo4j.GraphDatabase.driver(self.neo4j_bolt, auth=(self.neo4j_user, self.neo4j_password))
        self.ont = ontobio.ontol_factory.OntologyFactory().create(taxslim)

    def run_query(self,query):
        """
        :param query: a cypher statement as a string to run
        """
        # Start a neo4j session, run a query, then close the session
        with self.driver.session() as session:
            res = session.run(query)
        return res

    def test_read_only(self):
        query = 'call dbms.listConfig() yield name, value where name = "dbms.read_only" return value'
        res = self.run_query(query)
        data = res.data()
        return data[0]['value'] != 'false'


    def label_microbes(self, batch):
        # Create a list of dictionaries where each key is "labels(n)"
        # and each value is a list containing a node label
        microbe_node_ansestors = {
            "bacteria":"NCBITaxon:2",
            "archaea":"NCBITaxon:2157",
            "virus":"NCBITaxon:10239",
        }
        for ansestor, ansestor_id in microbe_node_ansestors.items():
            node_ids = set()
            node_ids = node_ids.union(set(self.ont.descendants(ansestor_id)))
            node_ids.add(ansestor_id)
            node_ids = list(node_ids)
            for query in query_partition(node_ids, batch, ansestor):
                self.run_query(query)

    def label_vertibrates(self, batch):
        # Create a list of dictionaries where each key is "labels(n)"
        # and each value is a list containing a node label
        node_ids = set()
        vertibrate_node_ansestors = {
            "Vertebrata":"NCBITaxon:7742"
        }
        for ansestor_id in vertibrate_node_ansestors.values():
            node_ids = node_ids.union(set(self.ont.descendants(ansestor_id)))
            node_ids.add(ansestor_id)
        node_ids = list(node_ids)
        for query in query_partition(node_ids, batch, 'vertebrate'):
            self.run_query(query)

    def label_eukaryotes(self, batch):
        eukaryote_node_ansestors = {}
        for child in self.ont.children("NCBITaxon:2759"):
            if child not in ["NCBITaxon:33154"]:
                eukaryote_node_ansestors[self.ont.label(child)]=child
            else:
                for grandchild in self.ont.children(child):
                    eukaryote_node_ansestors[self.ont.label(grandchild)]=grandchild
        for ansestor, ansestor_id in eukaryote_node_ansestors.items():
            node_ids = set()
            node_ids = node_ids.union(set(self.ont.descendants(ansestor_id)))
            node_ids.add(ansestor_id)
            node_ids = list(node_ids)
            for query in query_partition(node_ids, batch, laymen_names[ansestor]):
                self.run_query(query)



    def decorate_organisms(self, batch):
        self.label_eukaryotes(batch)
        self.label_microbes(batch)
        #self.label_vertibrates(batch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--user", type=str, help="Neo4j Username", default=None, required=False)
    parser.add_argument("-p", "--password", help="Neo4j Password", type=str, default=None, required=False)
    parser.add_argument("-b", "--bolt", help="Neo4j bolt address", type=str, default=None, required=False)
    parser.add_argument("-t", "--taxslim", type=str, help="The path to the taxslim owl file", default=None, required=True)
    parser.add_argument("-l", "--live", type=str, help="Live parameter for RTXConfiguration", default="local", required=False)
    parser.add_argument("-c", "--config", type=str, help="config.json file location. If included will read from this as opposed to using RTXConfiguration.", default=None, required=False)
    parser.add_argument("--batch", type=int, help="The batch size for neo4j set querries", default=500, required=False)
    arguments = parser.parse_args()
    
    if arguments.config is not None:
        #print(arguments.config)
        with open(arguments.config, 'r') as fid:
            config_data = json.load(fid)
        if 'Contextual' in config_data:
            config_data_kg2_neo4j = config_data['Contextual']['KG2']['neo4j']
            neo4j_user = config_data_kg2_neo4j['username']
            neo4j_password = config_data_kg2_neo4j['password']
        else:
            config_data_kg2_neo4j = config_data['KG2']['neo4j']
            neo4j_user = config_data_kg2_neo4j['username']
            neo4j_password = config_data_kg2_neo4j['password']
        if arguments.password is None:
            arguments.password = neo4j_password
        if arguments.user is None:
            arguments.user = neo4j_user

    decorator = DecorateOTNodes(arguments.user, arguments.password, arguments.bolt, arguments.live, arguments.taxslim)

    if decorator.test_read_only():
        print("WARNING: neo4j database is set to read-only and thus nodes will not update", file=sys.stderr)
    else:
        decorator.decorate_organisms(arguments.batch)