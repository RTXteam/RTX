import concurrent.futures


class SimpleGraphToContentGraphConverter:

    def __init__(self, edge_extractor):
        self.nodes = {}
        self.edges = {}
        self.edge_extractor = edge_extractor

    def process_edge(self, edge_name, node_pair, nodes, edge_extractor, arax_response):
        result = edge_extractor.get_edges(node_pair[0], nodes[node_pair[0]], node_pair[1], nodes[node_pair[1]],
                                          edge_name, arax_response)
        if result:
            return result['nodes'], result['edges']
        return None, None

    def convert(self, nodes, edges, arax_response):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.process_edge, edge_name, node_pair, nodes, self.edge_extractor,
                                arax_response): edge_name
                for edge_name, node_pair in edges.items()
            }

            for future in concurrent.futures.as_completed(futures):
                nodes_result, edges_result = future.result()
                if nodes_result and edges_result:
                    self.nodes.update(nodes_result)
                    self.edges.update(edges_result)

        return self.nodes, self.edges
