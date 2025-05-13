import requests


class PloverDBRepo:

    def __init__(self, plover_url):
        self.plover_url = plover_url

    def get_neighbors(self, node_ids):
        endpoint = "/get_neighbors"
        data = {"node_ids": node_ids, "categories": ["biolink:NamedThing"]}
        response = requests.post(
            self.plover_url + endpoint,
            headers={'accept': 'application/json'},
            json=data,
            timeout=10)
        response.raise_for_status()
        return response.json()
