import requests


class EdgeExtractorFromPloverDB:

    def __init__(self, plover_url):
        self.plover_url = plover_url

    def get_edges(self, node1_name, node1_id, node2_name, node2_id, edge_name, arax_response):
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
            return json
        except Exception as e:
            arax_response.warning(f"Cannot retrieve {data} from plover DB with error: {e}")
            return None
