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

How to run this module
        $ cd [git repo]/code/reasoningtool/kg-construction
        $ python3 UpdateNodesInfo.py
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
import json
from QueryEBIOLS import QueryEBIOLS
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryMyChem import QueryMyChem
from QueryReactome import QueryReactome
from QueryKEGG import QueryKEGG
from QueryPubChem import QueryPubChem
from QueryHMDB import QueryHMDB


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

    @staticmethod
    def __update_nodes(node_type):

        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_chemical_substance_nodes():
        UpdateNodesInfo.__update_nodes('chemical_substance')

    @staticmethod
    def update_bio_process_nodes():
        UpdateNodesInfo.__update_nodes('bio_process')

    @staticmethod
    def update_anatomy_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_phenotype_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_microRNA_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_pathway_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_protein_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_disease_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_chemical_substance_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_bio_process_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_cellular_component_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_molecular_function_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
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

    @staticmethod
    def update_metabolite_nodes_desc():
        f = open('config.json', 'r')
        config_data = f.read()
        f.close()
        config = json.loads(config_data)

        conn = Neo4jConnection(config['url'], config['username'], config['password'])
        nodes = conn.get_metabolite_nodes()
        print("the number of metabolite nodes: %d" % len(nodes))

        from time import time
        t = time()

        none_count = 0;
        nodes_array = []
        for i, node_id in enumerate(nodes):
            # print("no %d" % i)
            node = dict()
            node['node_id'] = node_id
            # print(node_id)
            pubchem_id = QueryKEGG.map_kegg_compound_to_pub_chem_id(node_id)
            hmdb_url = QueryPubChem.get_description_url(pubchem_id)
            # if hmdb_url is None:
            #     print('# %d hmdb url is None' % i)
            node['desc'] = QueryHMDB.get_compound_desc(hmdb_url)
            if node['desc'] == "None":
                none_count += 1
            nodes_array.append(node)

        print("none count = " + str(none_count))
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


if __name__ == '__main__':

    # UpdateNodesInfo.update_anatomy_nodes()
    # UpdateNodesInfo.update_phenotype_nodes()
    # UpdateNodesInfo.update_microRNA_nodes()
    # UpdateNodesInfo.update_pathway_nodes()
    # UpdateNodesInfo.update_protein_nodes()
    # UpdateNodesInfo.update_disease_nodes()
    # UpdateNodesInfo.update_chemical_substance_nodes()
    # UpdateNodesInfo.update_bio_process_nodes()

    UpdateNodesInfo.update_anatomy_nodes_desc()
    UpdateNodesInfo.update_phenotype_nodes_desc()
    UpdateNodesInfo.update_disease_nodes_desc()
    UpdateNodesInfo.update_bio_process_nodes_desc()
    UpdateNodesInfo.update_microRNA_nodes_desc()
    UpdateNodesInfo.update_protein_nodes_desc()
    UpdateNodesInfo.update_chemical_substance_desc()
    UpdateNodesInfo.update_pathway_nodes_desc()
    UpdateNodesInfo.update_cellular_component_nodes_desc()
    UpdateNodesInfo.update_molecular_function_nodes_desc()
    UpdateNodesInfo.update_metabolite_nodes_desc()

