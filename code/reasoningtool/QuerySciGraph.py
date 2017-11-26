""" This module defines the class QuerySciGraph which connects to APIs at
https://scigraph-ontology.monarchinitiative.org/scigraph/graph/neighbors/,
querying "sub phenotypes" for phenotypes.
"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import requests
import sys

class QuerySciGraph:
    TIMEOUT_SEC=120
    API_BASE_URL = {
        "graph_neighbors": "https://scigraph-ontology.monarchinitiative.org/scigraph/graph/neighbors/{node_id}"
    }

    @staticmethod
    def __access_api(url, params=None):
#        print(url)
        try:
            res = requests.get(url, params, timeout=QuerySciGraph.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QuerySciGraph for URL: ' + url, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        return res.json()
             
    '''returns the disease ontology IDs (DOID:NNNNN) for a given mesh ID in CURIE format, 'MESH:D012345'

    :param mesh_id: str containing the MeSH ID in CURIE format, i.e., MESH:D003550
    :return: set(str)
    '''
    @staticmethod
    def get_disont_ids_for_mesh_id(mesh_id):
        results = QuerySciGraph.__access_api(QuerySciGraph.API_BASE_URL['graph_neighbors'].format(node_id=mesh_id))
        disont_ids = set()
        if results is not None:
            res_nodes = results.get('nodes', None)
            if res_nodes is not None:
                assert type(res_nodes)==list
                for res_node in res_nodes:
                    id = res_node.get('id', None)
                    if id is not None:
                        if 'DOID:' in id:
                            disont_ids.add(id)
                        else:
                            meta = res_node.get('meta', None)
                            if meta is not None:
                                dbxrefs = meta.get('http://www.geneontology.org/formats/oboInOwl#hasDbXref', None)
                                if dbxrefs is not None:
                                    assert type(dbxrefs)==list
                                    for dbxref in dbxrefs:
                                        if 'DOID:' in dbxref:
                                            disont_ids.add(dbxref)
        return disont_ids
    
    @staticmethod
    def query_sub_phenotypes_for_phenotype(phenont_id):
        """
        Return a dict of `<id, label>`, where `id`s are all sub-phenotype of parameter `phenont_id`.

        E.g. input "HP:0000107" (Renal cyst),
        >>> QuerySciGraph.query_sub_phenotypes_for_phenotype("HP:0000107")
        {'HP:0100877': 'Renal diverticulum', 'HP:0000108': 'Renal corticomedullary cysts',
         'HP:0000803': 'Renal cortical cysts', 'HP:0000003': 'Multicystic kidney dysplasia',
         'HP:0008659': 'Multiple small medullary renal cysts', 'HP:0005562': 'Multiple renal cysts',
         'HP:0000800': 'Cystic renal dysplasia', 'HP:0012581': 'Solitary renal cyst'}
        """
        params = {
            # "depth": 1,
            # "blankNodes": "false",

            # Suppose `phenont_id` is X
            # If direction is INCOMING, find all Y that (sub {id: Y})-[:subClassOf]->(obj {id: X})
            # If direction is OUTGOING, find all Y that (sub {id: X})-[:subClassOf]->(obj {id: Y})
            "direction": "INCOMING",  # "OUTGOING" / "BOTH"
            "relationshipType": "subClassOf"
        }

        # param_str = "&".join(["{}={}".format(key, value) for key, value in params.items()])
        url = QuerySciGraph.API_BASE_URL["graph_neighbors"].format(node_id=phenont_id)
        json = QuerySciGraph.__access_api(url, params=params)
        sub_nodes_with_labels = dict()
        if json is not None:
            sub_edges = json['edges']  # Get all INCOMING edges
            sub_nodes = set(map(lambda e: e["sub"], sub_edges))  # Get all neighboring nodes (duplicates may exist; so set is used here)
            sub_nodes = set(filter(lambda s: s.startswith("HP:"), sub_nodes))  # Keep human phenotypes only
            
            sub_nodes_with_labels = dict([(node["id"], node['lbl']) for node in json['nodes'] if node["id"] in sub_nodes])
            
            if len(sub_nodes_with_labels) >= 200:
                print("[Warning][SciGraph] Found {} sub phenotypes for {}".format(len(sub_nodes_with_labels), phenont_id))

        return sub_nodes_with_labels

if __name__ == '__main__':
    print(QuerySciGraph.query_sub_phenotypes_for_phenotype('HP:12072'))
    print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D000856'))
    print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D015473'))
    print(QuerySciGraph.query_sub_phenotypes_for_phenotype("HP:0000107"))  # Renal cyst
    print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D015470'))
