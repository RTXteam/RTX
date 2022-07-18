import sys, os
import demographs
import expand_utilities as eu

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph

class GraphSplitter:
    """Used to split query graphs into more convenient fragments which can be expanded separately, and then recombined afterward along the unpinned nodes that the fragments share."""


    def __init__(self,qg=None):
        self.qg = qg
        self.sorted_pinned_nodes = None


    def _sort_pinned_nodes(self):
        """Sorts the pinned nodes in a graph. The resulting list of pinned nodes will be used to determine the order in which the graph is split. This ensures consistency when splitting the same graph multiple times."""
        pinned_nodes = [(key, node) for (key, node) in self.qg.nodes.items() if node.ids]
        # sort each node's curies to ensure consistency between queries
        for key, node in pinned_nodes:
            node.ids.sort()
        pinned_nodes.sort(key=lambda node_tuple: node_tuple[1].ids)
        pinned_nodes = [key for key, node in pinned_nodes]
        return pinned_nodes


    def _traverse_outward_recur(self, graph, found_nodes, traversed_edges, traversed_nodes, path, node):
        """Recursive function which radiates outwards, traversing all nodes in a graph which are connected to a given node, and adding them to a dictionary where the keys are node names and the values are the shortest path to the node from the originally given node."""
        # utility function to get the node of an edge that hasn't been traversed
        get_untraversed_node = lambda edge: edge.subject if edge.subject not in traversed_nodes else edge.object
        # make deep copy of path and traversed_edges to not interfere with other recursive calls
        path = [this_node for this_node in path]
        traversed_edges = {edge for edge in traversed_edges}
        path.append(node)

        # if new node is found, add it to dict and record shortest path to it
        if node not in found_nodes or len(path) < len(found_nodes[node]):
            found_nodes[node] = path

        edges_to_traverse = eu.get_connected_qedge_keys(node, graph)
        # ensure we don't traverse the same edge multiple times with this
        edges_to_traverse -= traversed_edges
        # base case, when there are no more edges to traverse, return None for no found nodes
        if len(edges_to_traverse) == 0:
            return

        # recur into each adjacent node from the given node
        for edge_key in edges_to_traverse:
            node_to_add = get_untraversed_node(graph.edges[edge_key])
            traversed_edges.add(edge_key)
            traversed_nodes.add(node_to_add)
            self._traverse_outward_recur(graph, found_nodes, traversed_edges, traversed_nodes, path, node_to_add)


    def _traverse_outward(self, graph, source_node):
        """Given a graph and a source node, returns a dict where the keys are the node names of all nodes connected to the source_node and the values are the shortest path from the source_node to the connected node"""
        connected_nodes = {}
        self._traverse_outward_recur(graph, connected_nodes, set(), {source_node}, [], source_node)
        return connected_nodes


    def _find_nearest_pinned_node(self, graph, source_node):
        """Given the graph and a source_node which is pinned, returns the pinned node with the shortest path to the source_node that includes at least one non-pinned node. For instance, this will not return a pinned node that is directly adjacent to the source_node or that has a path of only pinned nodes. Returns None if there are no nodes that fit these criteria"""
        if not graph.nodes[source_node].ids:
            raise TypeError("Was given an unpinned node")

        # populate pinned_nodes with tuples representing nodes connected to source_node of the form (node key, distance, [path])
        found_nodes = self._traverse_outward(graph, source_node)
        # found_pinned_nodes are the found nodes which are pinned (i.e. they have ids) and whose path to source_node contains at least one unpinned node
        has_valid_path = lambda path: any([not graph.nodes[node].ids for node in path])
        found_pinned_nodes = {node_key:path for (node_key,path) in found_nodes.items() if graph.nodes[node_key].ids and has_valid_path(path)}

        # return None if no valid nodes found
        if len(found_pinned_nodes) == 0:
            return None

        # gets the node with the lowest distance from source_node
        # if two nodes are tied, get the one with the higher priority
        nearest_pinned_node = list(found_pinned_nodes.keys())[0]
        for node_key in found_pinned_nodes:
            nearest_node_path = found_pinned_nodes[nearest_pinned_node]
            path = found_pinned_nodes[node_key]

            if len(path) < len(nearest_node_path):
                nearest_pinned_node = node_key
            elif len(path) == len(nearest_node_path):
                if node_key == self._higher_priority_node(node_key, nearest_pinned_node):
                    nearest_pinned_node = node_key

        # returns a tuple of the form (node key, [path])
        return (nearest_pinned_node, found_pinned_nodes[nearest_pinned_node])


    def _higher_priority_node(self, n1, n2):
        """Returns the node key with the higher priority level between the two."""
        for node in self.sorted_pinned_nodes:
            if node == n1:
                return n1
            if node == n2:
                return n2
        raise TypeError("Neither pinned node found in pinned nodes.")


    def _get_first_node(self, graph):
        """Returns highest ordered node in a subgraph. This is used to ensure consistency of fragmentation order if the same query is issued multiple times. Note that 'sorted_pinned_nodes' contains all of the pinned nodes in the query graph, and that 'graph' should be some subgraph of the query graph."""
        for node in self.sorted_pinned_nodes:
            if node in graph.nodes.keys():
                return node
        raise TypeError("Pinned node not found in graph. This means that the provided graph is not a subgraph of the querygraph")


    def _get_edge(self, graph, n1, n2):
        """Returns the edge in the graph that is between nodes n1 and n2 or None if no such edge exists"""
        for edgename in graph.edges:
            edge = graph.edges[edgename]
            if edge.subject == n1 and edge.object == n2:
                return edgename
            if edge.subject == n2 and edge.object == n1:
                return edgename
        return None


    def _frag_nodes_to_fragment(self, graph, nodes_set):
        """Given a graph and a set of node keys, instantiates and returns a QueryGraph which is a subgraph of the given graph"""
        # include all node entries of graph.nodes which exist in nodes_set
        nodes = {key:value for (key,value) in graph.nodes.items() if key in nodes_set}
        # include all edge entries whose subject and object are in nodes_set
        edges = {key:value for (key,value) in graph.edges.items() if value.subject in nodes_set and value.object in nodes_set}

        fragment = QueryGraph(nodes, edges)
        return fragment


    def _find_split(self, graph, path):
        """Given a graph and a path between two pinned nodes that contains at least one unpinned node, this function finds an edge on which to split the graph. Specifically, the edge to split on will be halfway between two pinned nodes in the path that is closest to the middle of the path. Returns the the two nodes that belong to this edge."""
        # ensure we are given a valid path
        if len(path) <= 2:
            raise Exception("Path is too short")
        start = path[0]
        end = path[len(path)-1]
        if not (graph.nodes[start].ids and graph.nodes[end].ids):
            raise Exception("Path is not bookended by pinned nodes")
        if not any([not graph.nodes[node_key].ids for node_key in path]):
            raise Exception("Path contains no unpinned nodes")

        # iterate forward through path until the last contiguous pinned_node
        start_idx = 0
        end_idx = len(path)-1
        for idx, node_key in enumerate(path):
            if not graph.nodes[node_key].ids:
                start_idx = idx
                break
        # iterate backward through path until the last contiguous pinned_node
        for idx, node_key in list(enumerate(path))[::-1]:
            if not graph.nodes[node_key].ids:
                end_idx = idx
                break

        # the midpoint is about halfway between the last contiguous pinned_nodes from each end of the path
        midpoint = start_idx + (end_idx-start_idx) // 2
        split_node = path[midpoint]
        adj_node = path[midpoint + 1]
        return split_node, adj_node


    def _split_into_two(self, graph):
        """Takes a graph, splits it and returns two graph fragments such that each fragment contains at least one unique pinned node and such that they share at least one unpinned node. If the graph has only one contiguous group of pinned nodes, it cannot be split with these criteria, and the graph is returned unsplit."""
        # find the node to split on by finding another pinned node, called 'paired_node', and then picking a node about halfway between start_node and paired_node
        start_node = self._get_first_node(graph)
        node_info = self._find_nearest_pinned_node(graph, start_node)
        if node_info == None:
            # if no nearest node was found, graph cannot be split
            return graph
        paired_node, path = node_info

        edges_removed = {}
        shared_nodes = set()
        # while start_node and paired_node are still conneted, remove edges
        while True:
            # split_node and adj_node are identified in order to yield an edge approximately halfway between start_node and paired_node. This edge will be removed in hopes that it will disconnect split_node and paired_node
            split_node, adj_node = self._find_split(graph, path)

            # split_node and the removed edge will be readded to frag2 later. split_node will be a shared node between frag1 and frag2
            edge_to_remove = self._get_edge(graph, split_node, adj_node)
            edges_removed[edge_to_remove] = graph.edges[edge_to_remove]
            shared_nodes.add(split_node)
            del graph.edges[edge_to_remove]

            # if paired_node is still in the fragment that contains start_node, set 'path' to be the new shortest path between them, and loop to remove another edge
            frag1_info = self._traverse_outward(graph, start_node)
            for node_key in frag1_info:
                if paired_node == node_key:
                    path = frag1_info[node_key]
                    break
            else:
                break

        # once start_node and paired_node are successfully disconnected after removing 1 or more edges, get the nodes belonging to each fragment
        frag1_nodes = set(frag1_info.keys())
        frag2_info = self._traverse_outward(graph, paired_node)
        frag2_nodes = set(frag2_info.keys())

        # readd edges to given graph now that fragments are already determined
        for edge in edges_removed:
            graph.edges[edge] = edges_removed[edge]
        # readd removed nodes to frag2
        frag2_nodes |= shared_nodes

        # convert these fragments into actual graphs
        frag1 = self._frag_nodes_to_fragment(graph, frag1_nodes)
        frag2 = self._frag_nodes_to_fragment(graph, frag2_nodes)

        return frag1, frag2


    def _split_recursive(self, graph):
        """Recursively splits a given graph into two fragments until it cannot be split anymore. Return a list of all the resulting fragments"""
        res = self._split_into_two(graph)
        # base case: if graph cannot be split, just return graph
        if res is graph:
            return [graph]
        # if graph was split into two fragments, try to split each fragment
        frag1, frag2 = res
        return self._split_recursive(frag1) + self._split_recursive(frag2)


    def split(self, qg):
        """Used to split a query graph into sub-query graph fragments. Specifically, each fragment will contain at least one unique pinned node, and at least one unpinned node that it shares with at least one other fragment. Acts as a wrapper for GraphSplitter._split_recursive."""
        self.qg = qg
        self.sorted_pinned_nodes = self._sort_pinned_nodes()

        if len(self.sorted_pinned_nodes) == 0:
            raise IndexError("There are no pinned nodes in this query graph. It cannot be split.")
        if eu.qg_is_disconnected(self.qg):
            raise TypeError("This query graph is disconnected. It may not be split.")

        fragments = self._split_recursive(self.qg)
        return fragments



def main():
    print("Testing Splitting")
    gs = GraphSplitter()
    # change this to the name of the query graph you want to split in demographs.py
    graph = demographs.query_graph_0
    for fragment in gs.split(graph):
        print("=========================")
        print(fragment)
    print("=========================")


if __name__ == "__main__":
    main()
