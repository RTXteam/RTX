import requests
import functools
import CachedMethods


class QuerySciGraph:
    API_BASE_URL = {
        "graph_neighbors": "https://scigraph-ontology.monarchinitiative.org/scigraph/graph/neighbors/{node_id}"
    }

    @staticmethod
    def __access_api(url, params=None):
        res = requests.get(url, params)

        print(res.url)

        assert 200 == res.status_code, "Status code result: {}; url: {}".format(res.status_code, res.url)

        return res.json()

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
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
        
        sub_edges = json['edges']  # Get all INCOMING edges
        sub_nodes = set(map(lambda e: e["sub"], sub_edges))  # Get all neighboring nodes (duplicates may exist; so set is used here)
        sub_nodes = set(filter(lambda s: s.startswith("HP:"), sub_nodes))  # Keep human phenotypes only

        sub_nodes_with_labels = dict([(node["id"], node['lbl']) for node in json['nodes'] if node["id"] in sub_nodes])

        return sub_nodes_with_labels

if __name__ == '__main__':
    print(QuerySciGraph.query_sub_phenotypes_for_phenotype("HP:0000107"))  # Renal cyst
