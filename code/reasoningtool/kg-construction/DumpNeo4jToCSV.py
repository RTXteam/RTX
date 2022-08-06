'''Dumps the knowledge graph from Neo4j to CSV or TSV format files

'''

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Yao Yao', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import argparse
import neo4j.v1
import sys, os

from BioNetExpander import BioNetExpander
from Orangeboard import Orangeboard

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration


def run_cypher(query, parameters=None):
    return driver.session().run(query, parameters)


def make_nodes_file(filename='nodes.csv', separator=','):
    query_result = run_cypher('match (n) return n')
    base_set = set('Base')
    nodes_file = open(filename, 'w')
    for record in query_result:
        for result_tuple in record.items():
            node = result_tuple[1]
            node_labels = node.labels
            node_labels.remove('Base')
            node_properties = node.properties
            node_uuid = node_properties['UUID']
            nodetype = next(iter(node_labels))
            nodename = node_properties['name']
            nodes_file.write('node' + separator + node_uuid + separator + nodetype + separator + nodename + '\n')
    nodes_file.close()


def make_rels_file(filename='rels.csv', separator=','):
    assert ':' not in separator
    query_result = run_cypher('match (n)-[r]-(m) return n.UUID, m.UUID, r LIMIT 10000')
    rels_set = set()
    rels_file = open(filename, 'w')
    for record in query_result:
        source_node_uuid = record[0]
        target_node_uuid = record[1]
        rel = record[2]
        rel_properties = rel.properties
        reltype = rel.type
        reltype_dir = BioNetExpander.MASTER_REL_IS_DIRECTED[reltype]
        sourcedb = rel_properties['provided_by']
        rel_key = Orangeboard.make_rel_dict_key(source_node_uuid, target_node_uuid, reltype_dir)
        if rel_key not in rels_set:
            rels_set.add(rel_key)
            rels_file.write('rel' + separator + source_node_uuid + separator + target_node_uuid + separator + sourcedb + ':' + reltype + '\n')
    rels_file.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    # parser.add_argument("-a", "--address", help="The bolt url and port used to connect to the neo4j instance. (default:"
    #                                             "bolt://localhost:7687)",
    #                     default="bolt://localhost:7687")
    # parser.add_argument("-u", "--username", help="The username used to connect to the neo4j instance. (default: )",
    #                     default='')
    # parser.add_argument("-p", "--password", help="The password used to connect to the neo4j instance. (default: )",
    #                     default='')
    parser.add_argument('--live', help="The container name, which can be one of the following: Production, KG2, rtxdev, "
                             "staging. (default: Production)", default='Production')
    args = parser.parse_args()

    # if args.username == '' or args.password == '':
    #     print('usage: DumpNeo4jToCSV.py [-h] [-a URL] [-u USERNAME] [-p PASSWORD]')
    #     print('DumpNeo4jToCSV.py: error: invalid username or password')
    #     exit(0)

    # create the RTXConfiguration object
    rtxConfig = RTXConfiguration()

    driver = neo4j.v1.GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
    make_nodes_file()
    make_rels_file()
