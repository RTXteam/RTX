
''' This module defines the class Neo4jConnection. Neo4jConnection class is designed
to connect to Neo4j database and perform operations on a graphic model object. (e.g.,
retrieve node and update node)
'''

# BEGIN user_pass.json format
# {
#   "username":"xxx",
#   "password":"xxx"
# }
# END user_pass.json format

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

from Neo4jConnection import Neo4jConnection
import json
from QueryBioLinkExtended import QueryBioLinkExtended
from QueryProteinEntity import QueryProteinEntity

def update_anatomy_nodes():

    f = open('user_pass.json', 'r')
    user_data = f.read()
    f.close()
    user = json.loads(user_data)

    conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
    nodes = conn.get_anatomy_nodes()

    from time import time
    t = time()

    nodes_array = []
    for node_id in nodes:
        node = dict()
        node['node_id'] = node_id
        node['extended_info_json'] = QueryBioLinkExtended.get_anatomy_entity(node_id)
        nodes_array.append(node)

    print("api pulling time: %f" % (time()-t))

    nodes_nums = len(nodes_array)
    group_nums = nodes_nums // 10000 + 1
    for i in range(group_nums):
        start = i*10000
        end = (i + 1) * 10000 if (i + 1) * 10000 < nodes_nums else nodes_nums
        conn.update_anatomy_nodes(nodes_array[start:end])

    print("total time: %f" % (time()-t))

    conn.close()


def update_phenotype_nodes():

    f = open('user_pass.json', 'r')
    user_data = f.read()
    f.close()
    user = json.loads(user_data)

    conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
    nodes = conn.get_phenotype_nodes()

    from time import time
    t = time()

    nodes_array = []
    for node_id in nodes:
        node = dict()
        node['node_id'] = node_id
        node['extended_info_json'] = QueryBioLinkExtended.get_phenotype_entity(node_id)
        nodes_array.append(node)

    print("api pulling time: %f" % (time()-t))

    nodes_nums = len(nodes_array)
    group_nums = nodes_nums // 10000 + 1
    for i in range(group_nums):
        start = i*10000
        end = (i + 1) * 10000 if (i + 1) * 10000 < nodes_nums else nodes_nums
        conn.update_phenotype_nodes(nodes_array[start:end])

    print("total time: %f" % (time()-t))

    conn.close()


def update_protein_nodes():

    f = open('user_pass.json', 'r')
    user_data = f.read()
    f.close()
    user = json.loads(user_data)

    conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
    nodes = conn.get_protein_nodes()

    from time import time
    t = time()

    nodes_array = []
    for node_id in nodes:
        node = dict()
        node['node_id'] = node_id
        node['extended_info_json'] = QueryProteinEntity.get_protein_entity(node_id)
        nodes_array.append(node)

    print("api pulling time: %f" % (time()-t))

    nodes_nums = len(nodes_array)
    group_nums = nodes_nums // 10000 + 1
    for i in range(group_nums):
        start = i*10000
        end = (i + 1) * 10000 if (i + 1) * 10000 < nodes_nums else nodes_nums
        conn.update_protein_nodes(nodes_array[start:end])

    print("total time: %f" % (time()-t))

    conn.close()


def update_disease_nodes():

    f = open('user_pass.json', 'r')
    user_data = f.read()
    f.close()
    user = json.loads(user_data)

    conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
    nodes = conn.get_disease_nodes()

    from time import time
    t = time()

    nodes_array = []
    for node_id in nodes:
        node = dict()
        node['node_id'] = node_id
        node['extended_info_json'] = QueryBioLinkExtended.get_disease_entity(node_id)
        nodes_array.append(node)

    print("api pulling time: %f" % (time()-t))

    nodes_nums = len(nodes_array)
    group_nums = nodes_nums // 10000 + 1
    for i in range(group_nums):
        start = i*10000
        end = (i + 1) * 10000 if (i + 1) * 10000 < nodes_nums else nodes_nums
        conn.update_disease_nodes(nodes_array[start:end])

    print("total time: %f" % (time()-t))

    conn.close()

if __name__ == '__main__':

    # update_anatomy_nodes()
    # update_phenotype_nodes()
    update_protein_nodes()
    # update_disease_nodes()