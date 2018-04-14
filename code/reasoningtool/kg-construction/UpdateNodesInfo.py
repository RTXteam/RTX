''' This module defines the class UpdateNodesInfo. UpdateNodesInfo class is designed
to retrieve the node properties and update the properties on the Graphic model object.
The available methods include:

    update_anatomy_nodes : retrieve data from BioLink and update all anatomy nodes
    update_phenotype_nodes : retrieve data from BioLink and update all phenotype nodes
    update_microRNA_nodes : retrieve data from MyGene and update all microRNA nodes
    update_pathway_nodes : retrieve data from Reactome and update all pathway nodes
    update_protein_nodes : retrieve data from MyGene and update all protein nodes
    update_disease_nodes : retrieve data from BioLink and update all disease nodes

Example of method name used from other packages.
    example of get_nodes_mtd_name : get_anatomy_nodes
    example of get_entity_mtd_name : get_anatomy_entity
    example of update_nodes_mtd_name : update_anatomy_nodes
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


class UpdateNodesInfo:

    GET_QUERY_CLASS = {
        'anatomy': 'QueryBioLinkExtended',
        'phenotype': 'QueryBioLinkExtended',
        'microRNA': 'QueryMyGene',
        'pathway': 'QueryReactomeExtended',
        'protein': 'QueryMyGene',
        'disease': 'QueryBioLinkExtended',
    }

    @staticmethod
    def __update_nodes(node_type):

        f = open('user_pass.json', 'r')
        user_data = f.read()
        f.close()
        user = json.loads(user_data)

        conn = Neo4jConnection("bolt://localhost:7687", user['username'], user['password'])
        get_nodes_mtd_name = "get_" + node_type + "_nodes"
        get_nodes_mtd = getattr(conn, get_nodes_mtd_name)
        nodes = get_nodes_mtd()

        from time import time
        t = time()

        nodes_array = []
        for node_id in nodes:
            node = dict()
            node['node_id'] = node_id
            query_class_name = UpdateNodesInfo.GET_QUERY_CLASS[node_type]
            query_class = getattr(__import__(query_class_name), query_class_name)
            get_entity_mtd_name = "get_" + node_type + "_entity"
            get_entity_mtd = getattr(query_class, get_entity_mtd_name)
            node['extended_info_json'] = get_entity_mtd(node_id)
            nodes_array.append(node)

        print("api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        group_nums = nodes_nums // 10000 + 1
        for i in range(group_nums):
            start = i * 10000
            end = (i + 1) * 10000 if (i + 1) * 10000 < nodes_nums else nodes_nums
            update_nodes_mtd_name = "update_" + node_type + "_nodes"
            update_nodes_mtd = getattr(conn, update_nodes_mtd_name)
            update_nodes_mtd(nodes_array[start:end])

        print("total time: %f" % (time() - t))

        conn.close()

    @staticmethod
    def update_anatomy_nodes():
        UpdateNodesInfo.__update_nodes('anatomy')

    @staticmethod
    def update_phenotype_nodes():
        UpdateNodesInfo.__update_nodes('phenotype')

    @staticmethod
    def update_microRNA_nodes():
        UpdateNodesInfo.__update_nodes('microRNA')

    @staticmethod
    def update_pathway_nodes():
        UpdateNodesInfo.__update_nodes('pathway')

    @staticmethod
    def update_protein_nodes():
        UpdateNodesInfo.__update_nodes('protein')

    @staticmethod
    def update_disease_nodes():
        UpdateNodesInfo.__update_nodes('disease')

if __name__ == '__main__':

    UpdateNodesInfo.update_anatomy_nodes()
    UpdateNodesInfo.update_phenotype_nodes()
    UpdateNodesInfo.update_microRNA_nodes()
    UpdateNodesInfo.update_pathway_nodes()
    UpdateNodesInfo.update_protein_nodes()
    UpdateNodesInfo.update_disease_nodes()