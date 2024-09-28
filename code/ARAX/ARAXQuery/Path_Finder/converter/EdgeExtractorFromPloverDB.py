import requests


class EdgeExtractorFromPloverDB:

    def __init__(self, plover_url):
        self.plover_url = plover_url
        self.pairs_to_edge_ids = {}
        self.knowledge_graph = {'edges': {}, 'nodes': {}}

    def get_extractor_url(self):
        return self.plover_url

    def get_edges(self, pairs, arax_response):
        cached_pairs = []
        i = 0
        while i < len(pairs):
            edge_key_1 = f"{pairs[i][0]}--{pairs[i][1]}"
            edge_key_2 = f"{pairs[i][1]}--{pairs[i][0]}"
            if edge_key_1 in self.pairs_to_edge_ids:
                cached_pairs.append(edge_key_1)
                del pairs[i]
            elif edge_key_2 in self.pairs_to_edge_ids:
                cached_pairs.append(edge_key_2)
                del pairs[i]
            else:
                i += 1

        try:
            knowledge_graph = {'edges': {}, 'nodes': {}}
            if len(pairs) != 0:
                endpoint = "/get_edges"
                query = {"pairs": pairs}
                response = requests.post(self.plover_url + endpoint, headers={'accept': 'application/json'}, json=query)
                json = response.json()
                self.pairs_to_edge_ids.update(json["pairs_to_edge_ids"])
                knowledge_graph = json["knowledge_graph"]
                self.knowledge_graph['edges'].update(knowledge_graph['edges'])
                self.knowledge_graph['nodes'].update(knowledge_graph['nodes'])
            for cached_pair in cached_pairs:
                list_of_edges = self.pairs_to_edge_ids[cached_pair]
                cached_nodes = cached_pair.split("--")
                knowledge_graph['nodes'][cached_nodes[0]] = self.knowledge_graph['nodes'][cached_nodes[0]]
                knowledge_graph['nodes'][cached_nodes[1]] = self.knowledge_graph['nodes'][cached_nodes[1]]
                for edge in list_of_edges:
                    knowledge_graph['edges'][edge] = self.knowledge_graph['edges'][edge]
            return knowledge_graph
        except Exception as e:
            arax_response.warning(f"Cannot retrieve {query} from plover DB with error: {e}")
            return None
