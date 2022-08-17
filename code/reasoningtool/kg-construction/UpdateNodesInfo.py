"""
This module defines the class UpdateNodesInfo. UpdateNodesInfo class is designed
to retrieve the node properties and update the properties on the Graphic model object.
The available methods include:

    update_anatomy_nodes : retrieve data from BioLink and update all anatomy nodes
    update_phenotype_nodes : retrieve data from BioLink and update all phenotype nodes
    update_microRNA_nodes : retrieve data from MyGene and update all microRNA nodes
    update_pathway_nodes : retrieve data from Reactome and update all pathway nodes
    update_protein_nodes : retrieve data from MyGene and update all protein nodes
    update_disease_nodes : retrieve data from BioLink and update all disease nodes

    update_anatomy_nodes_desc : update the descriptions of anatomical_entity nodes
    update_phenotype_nodes_desc : update the descriptions of phenotypic_feature nodes
    update_disease_nodes_desc : update the descriptions of disease nodes
    update_bio_process_nodes_desc : update the descriptions of biological_process nodes
    update_microRNA_nodes_desc : update the descriptions of microRNA nodes
    update_protein_nodes_desc : update the descriptions of protein nodes
    update_chemical_substance_desc : update the descriptions of chemical_substance nodes
    update_pathway_nodes_desc : update the descriptions of pathway nodes
    update_cellular_component_nodes_desc : update the descriptions of cellular_component nodes
    update_molecular_function_nodes_desc : update the descriptions of molecular_function nodes
    update_metabolite_nodes_desc : update the descriptions of metabolite nodes

Example of method name used from other packages.
    example of get_nodes_mtd_name : get_anatomy_nodes
    example of get_entity_mtd_name : get_anatomy_entity
    example of update_nodes_mtd_name : update_anatomy_nodes

How to run this module:
If you want to update the descriptions of all types of nodes, please use the default value of runfunc argument:
        $ cd [git repo]/code/reasoningtool/kg-construction
        $ python3 UpdateNodesInfo.py -u xxx -p xxx 1>stdout_desc.log 2>stderr_desc.log

If you want to update the descriptions of the specified nodes, please use the runfunc argument to specify the method:
        $ cd [git repo]/code/reasoningtool/kg-construction
        $ python3 UpdateNodesInfo.py -u xxx -p xxx --runfunc=update_disease_nodes_desc 1>stdout_desc.log 2>stderr_desc.log
"""

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import argparse
import sys
import os

from Neo4jConnection import Neo4jConnection
from QueryEBIOLS import QueryEBIOLS
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryMyChem import QueryMyChem
from QueryReactome import QueryReactome
from QueryKEGG import QueryKEGG
from QueryHMDB import QueryHMDB

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration

class UpdateNodesInfo:

    GET_QUERY_CLASS = {
        'anatomy': 'QueryBioLink',
        'phenotype': 'QueryBioLink',
        'microRNA': 'QueryMyGene',
        'pathway': 'QueryReactome',
        'protein': 'QueryMyGene',
        'disease': 'QueryBioLink',
        'chemical_substance': 'QueryMyChem',
        'bio_process': 'QueryBioLink'
    }

    def __init__(self, user, password, url ='bolt://localhost:7687'):
        self.neo4j_user = user
        self.neo4j_password = password
        self.neo4j_url = url

    def __update_nodes(self, node_type):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        get_nodes_mtd_name = "get_" + node_type + "_nodes"
        get_nodes_mtd = getattr(conn, get_nodes_mtd_name)
        nodes = get_nodes_mtd()
        print(len(nodes))

        from time import time
        t = time()

        nodes_array = []
        query_class_name = UpdateNodesInfo.GET_QUERY_CLASS[node_type]
        query_class = getattr(__import__(query_class_name), query_class_name)
        get_entity_mtd_name = "get_" + node_type + "_entity"
        get_entity_mtd = getattr(query_class, get_entity_mtd_name)
        query_instance = query_class()
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            if node_type == "protein" or node_type == "microRNA":
                get_entity_mtd = getattr(query_instance, get_entity_mtd_name)
            node['extended_info_json'] = get_entity_mtd(node_id)
            nodes_array.append(node)
            print(node_type + " node No. %d : %s" % (i, node_id))

        print("api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            update_nodes_mtd_name = "update_" + node_type + "_nodes"
            update_nodes_mtd = getattr(conn, update_nodes_mtd_name)
            update_nodes_mtd(nodes_array[start:end])

        print("total time: %f" % (time() - t))

        conn.close()

    def update_anatomy_nodes(self):
        self.__update_nodes('anatomy')

    def update_phenotype_nodes(self):
        self.__update_nodes('phenotype')

    def update_microRNA_nodes(self):
        self.__update_nodes('microRNA')

    def update_pathway_nodes(self):
        self.__update_nodes('pathway')

    def update_protein_nodes(self):
        self.__update_nodes('protein')

    def update_disease_nodes(self):
        self.__update_nodes('disease')

    def update_chemical_substance_nodes(self):
        self.__update_nodes('chemical_substance')

    def update_bio_process_nodes(self):
        self.__update_nodes('bio_process')

    def update_anatomy_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_anatomy_nodes()
        print("the number of anatomy nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            node['desc'] = QueryEBIOLS.get_anatomy_description(node_id)
            nodes_array.append(node)

        print("anatomy api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_anatomy_nodes_desc(nodes_array[start:end])

        print("anatomy total time: %f" % (time() - t))

        conn.close()

    def update_phenotype_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_phenotype_nodes()
        print("the number of phenotype nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            node['desc'] = QueryEBIOLS.get_phenotype_description(node_id)
            nodes_array.append(node)

        print("phenotype api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_phenotype_nodes_desc(nodes_array[start:end])

        print("phenotype total time: %f" % (time() - t))

        conn.close()

    def update_microRNA_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_microRNA_nodes()
        print("the number of microRNA nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        mg = QueryMyGene()
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            node['desc'] = mg.get_microRNA_desc(node_id)
            nodes_array.append(node)

        print("microRNA api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_microRNA_nodes_desc(nodes_array[start:end])

        print("microRNA total time: %f" % (time() - t))

        conn.close()

    def update_pathway_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_pathway_nodes()
        print("the number of pathway: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            node['desc'] = QueryReactome.get_pathway_desc(node_id)
            nodes_array.append(node)

        print("pathway api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_pathway_nodes_desc(nodes_array[start:end])

        print("pathway total time: %f" % (time() - t))

        conn.close()

    def update_protein_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_protein_nodes()
        print("the number of protein nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        mg = QueryMyGene()
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            node['desc'] = mg.get_protein_desc(node_id)
            nodes_array.append(node)

        print("protein api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_protein_nodes_desc(nodes_array[start:end])

        print("protein total time: %f" % (time() - t))

        conn.close()

    def update_disease_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_disease_nodes()
        print("the number of disease nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        qo = QueryOMIM()
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            if node_id[:4] == "OMIM":
                node['desc'] = qo.disease_mim_to_description(node_id)
            elif node_id[:4] == "DOID":
                node['desc'] = QueryEBIOLS.get_disease_description(node_id)
            nodes_array.append(node)

        print("disease api pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_disease_nodes_desc(nodes_array[start:end])

        print("disease total time: %f" % (time() - t))

        conn.close()

    def update_chemical_substance_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_chemical_substance_nodes()
        print("the number of chemical_substance nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            node['desc'] = QueryMyChem.get_chemical_substance_description(node_id)
            nodes_array.append(node)

        print("chemical_substance pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_chemical_substance_nodes_desc(nodes_array[start:end])

        print("chemical substance total time: %f" % (time() - t))

        conn.close()

    def update_bio_process_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_bio_process_nodes()
        print("the number of bio_process nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        for i, node_id in enumerate(nodes):
            node = dict()
            node['node_id'] = node_id
            node['desc'] = QueryEBIOLS.get_bio_process_description(node_id)
            nodes_array.append(node)

        print("bio_process pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_bio_process_nodes_desc(nodes_array[start:end])

        print("bio_process total time: %f" % (time() - t))

        conn.close()

    def update_cellular_component_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_cellular_component_nodes()
        print("the number of cellular_component nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        for i, node_id in enumerate(nodes):
            # print("no %d" % i)
            node = dict()
            node['node_id'] = node_id
            node['desc'] = QueryEBIOLS.get_cellular_component_description(node_id)
            nodes_array.append(node)

        print("cellular_component pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_cellular_component_nodes_desc(nodes_array[start:end])

        print("cellular_component total time: %f" % (time() - t))

        conn.close()

    def update_molecular_function_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_molecular_function_nodes()
        print("the number of molecular_function nodes: %d" % len(nodes))

        from time import time
        t = time()

        nodes_array = []
        for i, node_id in enumerate(nodes):
            # print("no %d" % i)
            node = dict()
            node['node_id'] = node_id
            node['desc'] = QueryEBIOLS.get_molecular_function_description(node_id)
            nodes_array.append(node)

        print("molecular_function pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_molecular_function_nodes_desc(nodes_array[start:end])

        print("molecular_function total time: %f" % (time() - t))

        conn.close()

    def update_metabolite_nodes_desc(self):
        conn = Neo4jConnection(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        nodes = conn.get_metabolite_nodes()
        print("the number of metabolite nodes: %d" % len(nodes))

        from time import time
        t = time()

        success_count = 0
        nodes_array = []
        for i, node_id in enumerate(nodes):
            # if i % 100 == 0:
            #     print("no %d" % i)
            node = dict()
            node['node_id'] = node_id
            hmdb_id = QueryKEGG.map_kegg_compound_to_hmdb_id(node_id)
            if hmdb_id:
                hmdb_url = 'http://www.hmdb.ca/metabolites/' + hmdb_id
                node['desc'] = QueryHMDB.get_compound_desc(hmdb_url)
                if node['desc'] != "None":
                    success_count += 1
            else:
                node['desc'] = 'None'
            nodes_array.append(node)
        print("success_count = " + str(success_count))
        print("metabolite pulling time: %f" % (time() - t))

        nodes_nums = len(nodes_array)
        chunk_size = 10000
        group_nums = nodes_nums // chunk_size + 1
        for i in range(group_nums):
            start = i * chunk_size
            end = (i + 1) * chunk_size if (i + 1) * chunk_size < nodes_nums else nodes_nums
            conn.update_metabolite_nodes_desc(nodes_array[start:end])

        print("metabolite total time: %f" % (time() - t))

        conn.close()

    def update_all(self):
        # UpdateNodesInfo.update_anatomy_nodes()
        # UpdateNodesInfo.update_phenotype_nodes()
        # UpdateNodesInfo.update_microRNA_nodes()
        # UpdateNodesInfo.update_pathway_nodes()
        # UpdateNodesInfo.update_protein_nodes()
        # UpdateNodesInfo.update_disease_nodes()
        # UpdateNodesInfo.update_chemical_substance_nodes()
        # UpdateNodesInfo.update_bio_process_nodes()
        self.update_anatomy_nodes_desc()
        self.update_phenotype_nodes_desc()
        self.update_disease_nodes_desc()
        self.update_bio_process_nodes_desc()
        self.update_microRNA_nodes_desc()
        self.update_protein_nodes_desc()
        self.update_chemical_substance_desc()
        self.update_pathway_nodes_desc()
        self.update_cellular_component_nodes_desc()
        self.update_molecular_function_nodes_desc()
        self.update_metabolite_nodes_desc()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='update the descriptions of nodes in th knowledge graph')
    # parser.add_argument("-a", "--address", help="The bolt url and port used to connect to the neo4j instance. (default:"
    #                                             "bolt://localhost:7687)",
    #                     default="bolt://localhost:7687")
    # parser.add_argument("-u", "--username", help="The username used to connect to the neo4j instance. (default: )",
    #                     default='')
    # parser.add_argument("-p", "--password", help="The password used to connect to the neo4j instance. (default: )",
    #                     default='')
    parser.add_argument('--live', help="The container name, which can be one of the following: Production, KG2, rtxdev, "
                             "staging. (default: Production)", default='Production')

    parser.add_argument('--runfunc', dest='runfunc')
    args = parser.parse_args()

    # create the RTXConfiguration object
    rtxConfig = RTXConfiguration()

    #   create UpdateNodesInfo object
    ui = UpdateNodesInfo(rtxConfig.neo4j_username, rtxConfig.neo4j_password, rtxConfig.neo4j_bolt)

    args_dict = vars(args)
    if args_dict.get('runfunc', None) is not None:
        run_function_name = args_dict['runfunc']
    else:
        run_function_name = 'update_all'

    try:
        run_function = getattr(ui, run_function_name)
    except AttributeError:
        sys.exit('In module UpdateNodesInfo.py, unable to find function named: ' + run_function_name)

    run_function()

