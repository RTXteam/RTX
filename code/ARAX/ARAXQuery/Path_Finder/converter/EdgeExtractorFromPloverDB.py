import requests


class EdgeExtractorFromPloverDB:

    def __init__(self, plover_url):
        self.plover_url = plover_url
        self.edges = {}
        self.nodes = {}

    def get_extractor_url(self):
        return self.plover_url

    def get_edges(self, node1_name, node1_id, node2_name, node2_id, edge_name, arax_response):
        edge_key_1 = f"{node1_id}_{node2_id}"
        edge_key_2 = f"{node2_id}_{node1_id}"
        if edge_key_1 in self.edges:
            return self.edges[edge_key_1]
        if edge_key_2 in self.edges:
            return self.edges[edge_key_2]
        endpoint = "/query"
        data = {
            "edges": {
                edge_name: {
                    "subject": node1_name,
                    "object": node2_name
                }
            },
            "nodes": {
                node1_name: {
                    "ids": [node1_id, node2_id]
                },
                node2_name: {
                    "ids": [node1_id, node2_id]
                }
            },
            "include_metadata": True,
            "respect_predicate_symmetry": True
        }
        try:
            response = requests.post(self.plover_url + endpoint, headers={'accept': 'application/json'}, json=data)
            json = response.json()
            self.edges[edge_key_1] = json
            return json
        except Exception as e:
            arax_response.warning(f"Cannot retrieve {data} from plover DB with error: {e}")
            return None
