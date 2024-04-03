class PathListToGraphConverter:

    def __init__(self, source_node_name, destination_node_name):
        self.source_node_name = source_node_name
        self.destination_node_name = destination_node_name
        self.counter_to_generate_new_node_name = 0
        self.counter_to_generate_new_edge_name = 0
        self.node_name = "n00_"
        self.edge_name = "e00_"

    def generate_new_node_name(self):
        self.counter_to_generate_new_node_name += 1
        return f"{self.node_name}{self.counter_to_generate_new_node_name}"

    def generate_new_edge_name(self):
        self.counter_to_generate_new_edge_name += 1
        return f"{self.edge_name}{self.counter_to_generate_new_edge_name}"

    def convert(self, paths):
        nodes = {}
        edges = {}
        for path in paths:
            if len(path.links) < 2:
                # todo error log
                continue
            for i in range(0, len(path.links)):
                if i == 0:
                    if path.links[i].id not in nodes:
                        nodes[path.links[i].id] = self.source_node_name
                elif i == len(path.links) - 1:
                    if path.links[i].id not in nodes:
                        nodes[path.links[i].id] = self.destination_node_name
                    edge_exist = False
                    for key, edge in edges.items():
                        if (edge[0] == self.destination_node_name and edge[1] == nodes[path.links[i - 1].id]) \
                                or (edge[1] == self.destination_node_name and edge[0] == nodes[path.links[i - 1].id]):
                            edge_exist = True
                    if not edge_exist:
                        edges[self.generate_new_edge_name()] = (nodes[path.links[i - 1].id], self.destination_node_name)
                else:
                    if path.links[i].id not in nodes:
                        nodes[path.links[i].id] = self.generate_new_node_name()
                    edge_exist = False
                    for key, edge in edges.items():
                        if (edge[0] == nodes[path.links[i].id] and edge[1] == nodes[path.links[i - 1].id]) \
                                or (edge[1] == nodes[path.links[i].id] and edge[0] == nodes[path.links[i - 1].id]):
                            edge_exist = True
                    if not edge_exist:
                        edges[self.generate_new_edge_name()] = (nodes[path.links[i - 1].id], nodes[path.links[i].id])
        nodes = {value: key for key, value in nodes.items()}
        return nodes, edges
