import demographs
import expand_utilities as eu

class GraphSplitter:
    """Used to split query graphs into more convenient parts"""

    def __init__(self):
        self.qg = None
        self.sorted_pinned_nodes = None


    def _sort_pinned_nodes(self):
        pinned_nodes = [(key, node) for (key, node) in self.qg.nodes.items() if node.ids]
        # sort each node's curies to ensure consistency between queries
        for key, node in pinned_nodes:
            node.ids.sort()
        pinned_nodes.sort(key=lambda node_tuple: node_tuple[1].ids)
        pinned_nodes = [key for key, node in pinned_nodes]
        # print("pinned nodes\n","="*64,"\n",pinned_nodes)
        return pinned_nodes


    def _find_nearest_pinned_node(self, source_node_key):
        """Starting at a given pinned node, this traverses the tree outward in all directions to find the nearest pinned node to the given node"""

        if not self.qg.nodes[source_node_key].ids:
            raise TypeError("Was given an unpinned node")

        traversed_edges = set()
        traversed_nodes = {source_node_key}
        # gets the node of an edge that has not yet been traversed, used below
        get_untraversed_node = lambda edge: edge.subject if edge.subject not in traversed_nodes else edge.object

        edges_to_traverse = eu.get_connected_qedge_keys(source_node_key, self.qg)
        # edges_to_traverse = sorted(edges_to_traverse, key=lambda x: x

        # while there are untraversed edges, continuing traversing the tree
        distance = 1
        while edges_to_traverse:
            distance += 1
            # traverse "outward" in the graph by one edge in all directions
            # print("Main Loop\n","="*64,)
            next_edges_to_traverse = set()
            # one iteration here is expanding outward from one node
            for edge_key in edges_to_traverse:

                # if we found a pinned node at this edge, return!
                node_to_add = get_untraversed_node(self.qg.edges[edge_key])
                if self.qg.nodes[node_to_add].ids and distance != 1:
                    return node_to_add, distance

                # tracking what we've already traversed
                traversed_edges.add(edge_key)
                traversed_nodes.add(node_to_add)
                # defining the set of edges to traverse when we expand outward by one more edge in the next while loop run
                next_edges_to_traverse |= eu.get_connected_qedge_keys(node_to_add, self.qg)
                next_edges_to_traverse -= traversed_edges
                edges_to_traverse = next_edges_to_traverse
            # print("Edges to traverse at end of for loop: ", edges_to_traverse)
            # print("Edges traversed at end of for loop: ", traversed_edges)
            # print("Nodes traversed at the end of for loop: ", traversed_nodes)
        raise TypeError("Could not find non-adjacent pinned node to pair with this pinned node")


    def split(self, qg):
        self.qg = qg
        self.sorted_pinned_nodes = self._sort_pinned_nodes()

        if len(self.sorted_pinned_nodes) == 0:
            raise IndexError("There are no pinned nodes in this query graph")
        if len(self.sorted_pinned_nodes) == 1:
            raise TypeError("Cannot split a query graph with only one pinned node")

        start_node = self.sorted_pinned_nodes[0]
        print("start node:",start_node)

        paired_node, distance = self._find_nearest_pinned_node(start_node)
        print("paired node:",paired_node)


def main():
    print("testing splitting")
    gs = GraphSplitter()
    # try:
    #     gs.split(demographs.query_graph_1)
    # except TypeError:
    #     pass
    gs.split(demographs.query_graph_8)
    print("done")

main()


# 1. Get ordered "priority list" of pinned nodes
# 2. If there is only one pinned node, return
# 3. Take first pinned node, traverse until finding a nearby pinned node (prefer higher priority nodes)
# 4. If this pair of nodes are directly connected, move on to find a new pair
# 5. With this pair of pinned nodes, find an unpinned node which is equidistant between the two pinned nodes (prefer further from higher priority node)
# 6. Split graph on unpinned node into two subgraphs. Run steps 2-6 on each subgraph
# 7. Join two subgraphs at unpinned node
