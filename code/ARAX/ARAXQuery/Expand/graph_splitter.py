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


    def _traverse_outward(self, traversed_edges, traversed_nodes, path, node, distance):
        """Recursively traverses the tree, and returns the closest pinned node (if one is found), along with the distance to that node and the path to that node. The 'closest' node, however, may not be adjacent to the original given node. I.e. it may not have a distance of 1. This function should only be called via the wrapper function _find_nearest_pinned_node"""
        # utility function to get the node of an edge that hasn't been traversed
        get_untraversed_node = lambda edge: edge.subject if edge.subject not in traversed_nodes else edge.object
        # make deep copy of path to not interfere with other recursive calls
        path = [this_node for this_node in path]
        path.append(node)

        # positive base case, when we have found a pinned node, return the node and info pertaining to how it was found. Note that nodes adjacent to the original source node are ignored here.
        if self.qg.nodes[node].ids and distance > 1:
            return (node, distance, path)

        edges_to_traverse = eu.get_connected_qedge_keys(node, self.qg)
        # ensure we don't traverse the same edge multiple times with this
        edges_to_traverse -= traversed_edges
        # negative base case, when there are no more edges to traverse, return None for no found pinned node
        if len(edges_to_traverse) == 0:
            return None

        # recurse into each adjacent node, appending its nearest pinned node if it has one. If not, None will be appended to nearest_pinned_nodes
        nearest_pinned_nodes = []
        for edge_key in edges_to_traverse:
            node_to_add = get_untraversed_node(self.qg.edges[edge_key])
            print("node to add for edge:",edge_key," is:",node_to_add)
            traversed_edges.add(edge_key)
            traversed_nodes.add(node_to_add)
            nearest_pinned_nodes.append(self._traverse_outward(traversed_edges, traversed_nodes, path, node_to_add, distance+1))

        # filter the 'None' entries out of nearest_pinned_nodes
        nearest_pinned_nodes = [x for x in nearest_pinned_nodes if x != None]
        if len(nearest_pinned_nodes) == 0:
            return None

        # find the node tuple with the lowest 'distance' attribute and return it
        closest_pinned_node = nearest_pinned_nodes[0]
        for tuple in nearest_pinned_nodes:
            if tuple[1] < closest_pinned_node[1]:
                closest_pinned_node = tuple
        return closest_pinned_node


    def _find_nearest_pinned_node(self, source_node_key):
        """Starting at a given pinned node, this traverses the tree outward in all directions to find the nearest pinned node to the given node. This is intended as a wrapper for the recursive function _traverse_outward"""

        if not self.qg.nodes[source_node_key].ids:
            raise TypeError("Was given an unpinned node")

        closest_pinned_node = self._traverse_outward(set(), {source_node_key}, [], source_node_key, 0)

        if closest_pinned_node == None:
            raise TypeError("Could not find non-adjacent pinned node to pair with this pinned node")
        return closest_pinned_node[0], closest_pinned_node[2]


    def split(self, qg):
        self.qg = qg
        self.sorted_pinned_nodes = self._sort_pinned_nodes()

        if len(self.sorted_pinned_nodes) == 0:
            raise IndexError("There are no pinned nodes in this query graph")
        if len(self.sorted_pinned_nodes) == 1:
            raise TypeError("Cannot split a query graph with only one pinned node")

        start_node = self.sorted_pinned_nodes[0]
        print("start node:",start_node)

        self._find_nearest_pinned_node(start_node)
        # print("paired node:",paired_node)


def main():
    print("testing splitting")
    gs = GraphSplitter()
    # try:
    #     gs.split(demographs.query_graph_1)
    # except TypeError:
    #     pass
    gs.split(demographs.query_graph_11)
    print("done")


main()


# 1. Get ordered "priority list" of pinned nodes
# 2. If there is only one pinned node, return
# 3. Take first pinned node, traverse until finding a nearby pinned node (prefer higher priority nodes)
# 4. If this pair of nodes are directly connected, move on to find a new pair
# 5. With this pair of pinned nodes, find an unpinned node which is equidistant between the two pinned nodes (prefer further from higher priority node)
# 6. Split graph on unpinned node into two subgraphs. Run steps 2-6 on each subgraph
# 7. Join two subgraphs at unpinned node
