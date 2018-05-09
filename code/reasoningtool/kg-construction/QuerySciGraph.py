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
        'node_properties': 'https://scigraph-ontology.monarchinitiative.org/scigraph/graph/{node_id}',
        'graph_neighbors': 'https://scigraph-ontology.monarchinitiative.org/scigraph/graph/neighbors/{node_id}',
        'cypher_query': 'https://scigraph-ontology.monarchinitiative.org/scigraph/cypher/execute.json'
    }

    @staticmethod
    def __access_api(url, params=None, headers=None):
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
            print('Status code ' + str(status_code) + ' for url: ' + res.url, file=sys.stderr)
            return None

        return res.json()

    @staticmethod
    def get_gene_ontology_curie_ids_for_uberon_curie_id(uberon_curie_id_str):
        results = QuerySciGraph.__access_api(QuerySciGraph.API_BASE_URL['graph_neighbors'].format(node_id=uberon_curie_id_str))
#        print(results)
        go_curie_id_str_dict = dict()
        if results is not None:
            res_edges = results.get("edges", None)
            if res_edges is not None:
                assert type(res_edges) == list
                for res_edge in res_edges:
                    object_curie_id = res_edge.get("obj", None)
                    if object_curie_id is not None:
                        if object_curie_id.startswith("GO:"):
                            edge_object_meta = res_edge.get("meta", None)
                            if edge_object_meta is not None:
                                assert type(edge_object_meta) == dict
                                edge_label = edge_object_meta.get("lbl", None)
                                if edge_label is not None:
                                    assert type(edge_label) == list
                                    go_dict = QuerySciGraph.query_get_ontology_node_category_and_term(object_curie_id)
                                    if len(go_dict) > 0:
                                        go_curie_id_str_dict.update({object_curie_id: {"predicate": edge_label[0],
                                                                                       "ontology": go_dict["category"],
                                                                                       "name": go_dict["name"]}})
        return go_curie_id_str_dict

    @staticmethod
    def get_gene_ontology_curie_ids_for_disease_curie_id(disease_curie_id_str):
        results = QuerySciGraph.__access_api(QuerySciGraph.API_BASE_URL['graph_neighbors'].format(node_id=disease_curie_id_str))
#        print(results)
        go_curie_id_str_dict = dict()
        mondo_curie_id_str = None
        is_mondo_bool = disease_curie_id_str.startswith("MONDO:")
        if results is not None:
            res_edges = results.get("edges", None)
            if res_edges is not None:
                assert type(res_edges) == list
                for res_edge in res_edges:
                    object_curie_id = res_edge.get("obj", None)
                    if object_curie_id is not None:
                        if object_curie_id.startswith("GO:"):
                            edge_object_meta = res_edge.get("meta", None)
                            if edge_object_meta is not None:
                                assert type(edge_object_meta) == dict
                                edge_label = edge_object_meta.get("lbl", None)
                                if edge_label is not None:
                                    assert type(edge_label) == list
                                    go_dict = QuerySciGraph.query_get_ontology_node_category_and_term(object_curie_id)
                                    if len(go_dict) > 0:
                                        go_curie_id_str_dict.update({object_curie_id: {"predicate": edge_label[0],
                                                                                       "ontology": go_dict["category"],
                                                                                       "name": go_dict["name"]}})
                        else:
                            if (not is_mondo_bool) and object_curie_id.startswith("MONDO:"):
                                edge_pred = res_edge.get("pred", None)
                                if edge_pred is not None and edge_pred == "equivalentClass":
                                    mondo_curie_id_str = object_curie_id
        if (not is_mondo_bool) and mondo_curie_id_str is not None:
            go_curie_id_str_dict.update(QuerySciGraph.get_gene_ontology_curie_ids_for_disease_curie_id(mondo_curie_id_str))
        return go_curie_id_str_dict

    
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
                assert type(res_nodes) == listq
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
        else:
            cypher_query = 'MATCH (dis:disease) WHERE ANY(item IN dis.`http://www.geneontology.org/formats/oboInOwl#hasDbXref` WHERE item = \'' + mesh_id + '\') RETURN dis.`http://www.geneontology.org/formats/oboInOwl#hasDbXref` as xref'
            
            url = QuerySciGraph.API_BASE_URL['cypher_query']
            results = QuerySciGraph.__access_api(url, params={'cypherQuery': cypher_query, 'limit': '10'})
            if results is not None:
                if len(results) > 0:
                    results_xref = results[0].get('xref', None)
                    if results_xref is not None:
                        disont_ids = set([x for x in results_xref if 'DOID:' in x])
        return disont_ids

    @staticmethod
    def query_get_ontology_node_category_and_term(ontology_term_id_str):
        results = QuerySciGraph.__access_api(QuerySciGraph.API_BASE_URL["node_properties"].format(node_id=ontology_term_id_str))
        res_dict = dict()
#        print(results)
        if results is not None:
            results_nodes = results.get("nodes", None)
            if results_nodes is not None:
                assert type(results_nodes) == list
                for results_node in results_nodes:
                    assert type(results_node) == dict
                    results_node_meta = results_node.get("meta", None)
                    if results_node_meta is not None:
                        assert type(results_node_meta) == dict
                        results_category = results_node_meta.get("category", None)
                        if results_category is not None:
                            assert type(results_category) == list
                            category_str = results_category[0]
                            label = results_node.get("lbl", None)
                            if label is not None:
                                assert type(label) == str
                                res_dict.update({"name": label,
                                                 "category": category_str})
        return(res_dict)
                                                                
    @staticmethod
    def query_sub_ontology_terms_for_ontology_term(ontology_term_id):
        """
        Return a dict of `<id, label>`, where `id`s are all sub-phenotype of parameter `ontology_term_id`.

        E.g. input "HP:0000107" (Renal cyst),
        >>> QuerySciGraph.query_sub_phenotypes_for_phenotype("HP:0000107")
        {'HP:0100877': 'Renal diverticulum', 'HP:0000108': 'Renal corticomedullary cysts',
         'HP:0000803': 'Renal cortical cysts', 'HP:0000003': 'Multicystic kidney dysplasia',
         'HP:0008659': 'Multiple small medullary renal cysts', 'HP:0005562': 'Multiple renal cysts',
         'HP:0000800': 'Cystic renal dysplasia', 'HP:0012581': 'Solitary renal cyst'}
        """

        curie_prefix = ontology_term_id.split(":")[0]
        
        params = {
            # "depth": 1,
            # "blankNodes": "false",

            # Suppose `ontology_term_id` is X
            # If direction is INCOMING, find all Y that (sub {id: Y})-[:subClassOf]->(obj {id: X})
            # If direction is OUTGOING, find all Y that (sub {id: X})-[:subClassOf]->(obj {id: Y})
            "direction": "INCOMING",  # "OUTGOING" / "BOTH"
            "relationshipType": "subClassOf"
        }

        # param_str = "&".join(["{}={}".format(key, value) for key, value in params.items()])
        url = QuerySciGraph.API_BASE_URL["graph_neighbors"].format(node_id=ontology_term_id)
        json = QuerySciGraph.__access_api(url, params=params)
        sub_nodes_with_labels = dict()
        if json is not None:
            sub_edges = json['edges']  # Get all INCOMING edges
            sub_nodes = set(map(lambda e: e["sub"], sub_edges))  # Get all neighboring nodes (duplicates may exist; so set is used here)
            sub_nodes = set(filter(lambda s: s.startswith(curie_prefix + ":"), sub_nodes))  # Keep human phenotypes only
            
            sub_nodes_with_labels = dict([(node["id"], node['lbl']) for node in json['nodes'] if node["id"] in sub_nodes])
            
            if len(sub_nodes_with_labels) >= 200:
                print("[Warning][SciGraph] Found {} sub phenotypes for {}".format(len(sub_nodes_with_labels), ontology_term_id))

        return sub_nodes_with_labels


if __name__ == '__main__':
    print(QuerySciGraph.get_gene_ontology_curie_ids_for_uberon_curie_id("UBERON:0000171"))
    # print(QuerySciGraph.query_get_ontology_node_category_and_term("GO:0005777"))
    # print(QuerySciGraph.query_get_ontology_node_category_and_term("GO:XXXXXXX"))
    # print(QuerySciGraph.get_gene_ontology_curie_ids_for_disease_curie_id("MONDO:0019053"))
    # print(QuerySciGraph.get_gene_ontology_curie_ids_for_disease_curie_id("DOID:906"))
    # print(QuerySciGraph.query_sub_ontology_terms_for_ontology_term("GO:0005777"))
    # print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D005199'))
    # print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D006937'))
    # print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D000856'))
    # print(QuerySciGraph.query_sub_ontology_terms_for_ontology_term('HP:12072'))
    # print(QuerySciGraph.query_sub_ontology_terms_for_ontology_term('GO:1904685'))
    # print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D015473'))
    # print(QuerySciGraph.query_sub_ontology_terms_for_ontology_term("HP:0000107"))  # Renal cyst
    # print(QuerySciGraph.get_disont_ids_for_mesh_id('MESH:D015470'))
