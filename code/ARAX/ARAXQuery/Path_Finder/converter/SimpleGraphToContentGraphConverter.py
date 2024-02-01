class SimpleGraphToContentGraphConverter:

    def __init__(self, edge_extractor):
        self.nodes = {}
        self.edges = {}
        self.edge_extractor = edge_extractor

    def convert(self, nodes, edges):

        for edge_name, node_pair in edges.items():
            response = self.edge_extractor.get_edges(node_pair[0], nodes[node_pair[0]], node_pair[1], nodes[node_pair[1]], edge_name)
            self.nodes.update(response['nodes'])
            # for _, edge_response in response['edges'][edge_name].items():
            #     edge_response.append(node_pair[0])
            #     edge_response.append(node_pair[1])
            self.edges.update(response['edges'])

        return self.nodes, self.edges

