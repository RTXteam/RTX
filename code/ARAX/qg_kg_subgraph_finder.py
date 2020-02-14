import copy
import enum
import itertools
import pandas
'''
For a given (1) query graph (assumed small) which has both "fixed" nodes and placeholder
"query" nodes, and (2) knowledge graph, computes a "relevant" subgraph of the knowledge graph
containing the set of all possible nodes that could match the query graph, and then computes
the set of all subgraphs within the "relevant" KG that exactly match the query graph structure.

Limitations: running time is exponential in the number of query graph vertices. Self-loops
in the query graph are not supported.
'''

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'


MAX_NUMBER_OF_QUERY_NODES_PER_CATEGORY = 10


class NodeType(enum.Enum):
    FIXED = 0
    QUERY = 1
    KG = 2


class EdgeDir(enum.Enum):
    INCOMING = 1
    OUTGOING = 2
    BOTH = 3


class Node:
    def __init__(self,
                 p_type: NodeType,
                 p_category: str,
                 p_id: str,
                 p_index: int):
        self.node_type = p_type
        self.category = p_category
        self.node_id = p_id
        self.node_index = p_index

    def key(self):
        if self.node_type == NodeType.FIXED:
            return self.node_id
        else:
            return 'category:' + self.category

    def __str__(self):
        return self.node_id


class Edge:
    def __init__(self,
                 p_source: Node,
                 p_target: Node):
        self.source = p_source
        self.target = p_target

    def __str__(self):
        return(self.source.node_id + '->' + self.target.node_id)


class Graph:
    def __init__(self,
                 p_nodes: set,
                 p_edges: set):
        self.nodes = p_nodes
        self.edges = p_edges
        self.setup()

    def setup(self):
        self.fixed_nodes = dict()
        self.query_nodes = dict()
        self.nodes_by_id = dict()
        self.edges_by_node = dict()
        self.edges_by_key = dict()
        self.neighbors_incoming = dict()
        self.neighbors_outgoing = dict()
        for edge in self.edges:
            # first for the edge source
            edges_by_node_single = self.edges_by_node.get(edge.source, None)
            if edges_by_node_single is None:
                edges_by_node_single = []
            self.edges_by_node[edge.source] = edges_by_node_single
            edges_by_node_single.append(edge)
            # now by the edge target
            neighbors_incoming_node = self.neighbors_incoming.get(edge.target, None)
            if neighbors_incoming_node is None:
                neighbors_incoming_node = set()
                self.neighbors_incoming[edge.target] = neighbors_incoming_node
            neighbors_incoming_node.add(edge.source)
            neighbors_outgoing_node = self.neighbors_outgoing.get(edge.source, None)
            if neighbors_outgoing_node is None:
                neighbors_outgoing_node = set()
                self.neighbors_outgoing[edge.source] = neighbors_outgoing_node
            neighbors_outgoing_node.add(edge.target)
            edges_by_node_single = self.edges_by_node.get(edge.target, None)
            if edges_by_node_single is None:
                edges_by_node_single = []
            self.edges_by_node[edge.target] = edges_by_node_single
            edges_by_node_single.append(edge)
            self.edges_by_key[make_edge_key(edge.source,
                                            edge.target)] = edge
        for node in self.nodes:
            self.nodes_by_id[node.node_id] = node
            if node.node_type == NodeType.FIXED:
                self.fixed_nodes[node.node_id] = node
            elif node.node_type == NodeType.QUERY or node.node_type == NodeType.KG:
                node_category = node.category
                query_node_dict = self.query_nodes.get(node_category, None)
                if query_node_dict is None:
                    query_node_dict = dict()
                    self.query_nodes[node_category] = query_node_dict
                assert node.node_id not in query_node_dict
                query_node_dict[node.node_id] = node
            else:
                assert False

    def delete(self, p_nodes: set):
        self.nodes = [node for node in self.nodes if node not in p_nodes]
        self.edges = [edge for edge in self.edges if edge.source not in p_nodes and edge.target not in p_nodes]
        self.setup()
        return self

    def __str__(self):
        return("((" + ', '.join([str(node) for node in self.nodes]) + "), " + "\n" +
               " (" + '\n  '.join([str(edge) for edge in self.edges]) + "))")

    def subgraph_for_nodes(self,
                           nodes: set):
        subgraph_edges_set = set()
        for node in nodes:
            edges_list = self.edges_by_node[node]
            for edge in edges_list:
                if edge.source in nodes and edge.target in nodes:
                    subgraph_edges_set.add(edge)
        return Graph(nodes, subgraph_edges_set)

    def subgraph_for_nodes_by_id(self,
                                 nodes: set):
        return self.subgraph_for_nodes(set([self.nodes_by_id[node_id] for node_id in nodes]))

    def has_edge_category_category(self,
                                   node1: Node,
                                   node2: Node):
        return (make_edge_key(node1, node2) in self.edges_by_key) or \
               (make_edge_key(node2, node1) in self.edges_by_key)

    def neighbors(self,
                  p_node: Node,
                  mode: EdgeDir):  # mode: 1 = incoming, 2 = outgoing, 3 = both
        ret_nodes = []
        if mode == EdgeDir.INCOMING or mode == EdgeDir.BOTH:
            ret_nodes += [node for node in self.neighbors_incoming[p_node]]
        if mode == EdgeDir.OUTGOING or mode == EdgeDir.BOTH > 0:
            ret_nodes += [node for node in self.neighbors_outgoing[p_node]]
        return set(ret_nodes)

    def neighbors_id(self,
                     id: str,
                     mode: int):  # mode: 1 = incoming, 2 = outgoing, 3 = both
        self.neighbors(self.nodes_by_id[id], mode)

    def make_from_dicts(node_info: dict,
                        edge_info: dict):
        N = len(node_info['id'])  # if caller doesn't specify node types, just assume all are KG
        if node_info.get('type', None) is None:
            node_info['type'] = [NodeType.KG] * N
        return Graph.make_from_df(pandas.DataFrame(node_info),
                                  pandas.DataFrame(edge_info))

    def make_from_df(node_info: pandas.DataFrame,
                     edge_info: pandas.DataFrame):
        nodes = list()
        for index, row in node_info.iterrows():
            node_id = row['id']
            type_int = row['type']
            category = row['category']
            nodes.append(Node(NodeType(type_int),
                              category,
                              node_id,
                         index))
        edges = set()
        for index, row in edge_info.iterrows():
            source_id = row['source_id']
            target_id = row['target_id']
            edges.add(Edge(nodes[source_id],
                           nodes[target_id]))
        return Graph(set(nodes), edges)

    def contains_self_loop(self):
        for edge in self.edges:
            if edge.source == edge.target:
                return True
        return False


def make_edge_key(node1: Node,
                  node2: Node):
    return node1.key() + '->' + node2.key()


def match_small_kg_to_qg(qg: Graph,
                         small_kg: Graph):

    # do some basic consistency checking on qg and small_kg
    if len(qg.nodes) != len(small_kg.nodes):
        return False
    if len(small_kg.edges) < len(qg.edges):  # less than here b/c small_kg could have multiedges
        return False
    # for the nodes in small_kg, make a mapping between categories and sets of nodes
    kg_query_nodes_by_categories = dict()
    fixed_nodes_qg_to_kg_map = dict()
    for node in small_kg.nodes:
        corresponding_node_type = node.corresponding_node_type
        assert corresponding_node_type is not None
        if corresponding_node_type == NodeType.FIXED:
            qg_node = qg.nodes_by_id.get(node.node_id, None)
            if qg_node is None:
                # if small_kg is missing one of the "fixed" nodes of qg then small_kg does not match qg
                return False
            fixed_nodes_qg_to_kg_map[qg_node] = node
        elif corresponding_node_type == NodeType.QUERY:
            cat = node.category
            categ_set = kg_query_nodes_by_categories.get(cat, None)
            if categ_set is None:
                categ_set = set()
                kg_query_nodes_by_categories[cat] = categ_set
            categ_set.add(node)
        else:
            assert False  # future-proofing in case some new node type is defined
    kg_category_counts = {key: len(value) for key, value in kg_query_nodes_by_categories.items()}
    qg_category_counts = {key: len(value) for key, value in qg.query_nodes.items()}
    if kg_category_counts != qg_category_counts:
        # if the number of node categories present in small_kg is not the same as in the QG, it is not a match
        return False
    qg_query_node_lists = [list(qg.query_nodes[cat].values()) for cat in kg_query_nodes_by_categories.keys()]
    found_consistent_mapping = False  # assume that this node mapping is not consistent with the QG
    # loop over every possible ordering of nodes (within each category) in small_kg:
    for kg_query_node_lists in itertools.product(*[list(itertools.permutations(kg_query_nodes_by_categories[cat]))
                                                   for cat in kg_query_nodes_by_categories.keys()]):
        # examine one potential mapping of KG nodes to QG nodes, at a time (out of all possible mappings):
        # do some basic consistency checks
        assert len(qg_query_node_lists) == len(kg_query_node_lists)
        kg_node_list_lens = list(map(len, kg_query_node_lists))
        assert len([count for count in kg_node_list_lens if count > MAX_NUMBER_OF_QUERY_NODES_PER_CATEGORY]) == 0
        assert list(map(len, qg_query_node_lists)) == kg_node_list_lens
        # the mappings are two parallel lists-of-lists; flatten them while preserving order
        kg_query_nodes_flat = list(itertools.chain(*kg_query_node_lists))
        qg_query_nodes_flat = list(itertools.chain(*qg_query_node_lists))
        # check consistency of the flattened lists
        assert len(kg_query_nodes_flat) == len(qg_query_nodes_flat)
        # build up a mapping
        qg_to_kg_node_map = {qg_query_nodes_flat[i]: kg_query_nodes_flat[i] for i in range(0, len(qg_query_nodes_flat))}
        qg_to_kg_node_map.update(fixed_nodes_qg_to_kg_map)
        mapping_is_consistent = True
        # check each edge for consistency:
        for edge in qg.edges:
            kg_source = qg_to_kg_node_map[edge.source]
            kg_target = qg_to_kg_node_map[edge.target]
            edge_key = make_edge_key(kg_source, kg_target)
            if edge_key not in small_kg.edges_by_key:
                mapping_is_consistent = False
                break
        if mapping_is_consistent:
            found_consistent_mapping = True
            break
    return found_consistent_mapping


def check_kg_node_if_should_keep(kg: Graph,
                                 qg: Graph,
                                 kg_node: Node):
    if kg_node.node_id in qg.fixed_nodes:
        return NodeType.FIXED
    # we know that kg_node is not a fixed node
    node_category = kg_node.category
    if node_category not in qg.query_nodes:
        return None
    # get query_graph nodes that correspond to this node_category:
    category_nodes_dict = qg.query_nodes[node_category]
    for qg_node_id in category_nodes_dict:
        qg_node = qg.nodes_by_id[qg_node_id]
        if len(qg.neighbors(qg_node, 3)) == 0:
            # this is a lone node in the query graph; return True
            return NodeType.QUERY
    for node in kg.neighbors(kg_node, 3):
        if node.node_id in qg.fixed_nodes:
            return NodeType.QUERY
        if qg.has_edge_category_category(kg_node, node):
            return NodeType.QUERY
    return None


def prune_unneeded_nodes_and_mark_fixed_nodes(kg: Graph,
                                              qg: Graph):
    nodes_remove = []
    for node in kg.nodes:
        corresponding_node_type = check_kg_node_if_should_keep(kg, qg, node)
        if corresponding_node_type is not None:
            node.corresponding_node_type = corresponding_node_type
        else:
            nodes_remove.append(node)
    return kg.delete(nodes_remove)


def find_all_kg_subgraphs_for_qg(kg: Graph,
                                 qg: Graph):
    assert not qg.contains_self_loop()
    ret_subgraphs = []
    categories_to_counts_qg = {category: len(value) for category, value in qg.query_nodes.items()}
    assert len([count for count in categories_to_counts_qg.values() if count > MAX_NUMBER_OF_QUERY_NODES_PER_CATEGORY]) == 0
    kg_copy = copy.deepcopy(kg)
    kg_pruned = prune_unneeded_nodes_and_mark_fixed_nodes(kg_copy, qg)
    del kg_copy
    kg_fixed_nodes = set()
    kg_query_nodes = dict()
    for node in kg_pruned.nodes:
        if node.corresponding_node_type == NodeType.FIXED:
            kg_fixed_nodes.add(node)
        elif node.corresponding_node_type == NodeType.QUERY:
            category = node.category
            category_nodes_set = kg_query_nodes.get(category, None)
            if category_nodes_set is None:
                category_nodes_set = set()
                kg_query_nodes[category] = category_nodes_set
            category_nodes_set.add(node)
        else:
            assert False
    subgraph_nodes_set_set = set()
    for subgraph_nodes_list_list in itertools.product(*[list(itertools.permutations(kg_query_nodes[category],
                                                                                    categories_to_counts_qg[category]))
                                                        for category in categories_to_counts_qg.keys()]):
        subgraph_nodes_set = frozenset(itertools.chain(*subgraph_nodes_list_list))
        subgraph_nodes_set_set.add(subgraph_nodes_set)
    for subgraph_nodes_set in subgraph_nodes_set_set:
        subgraph_nodes_set_with_fixed = set()
        subgraph_nodes_set_with_fixed |= kg_fixed_nodes
        subgraph_nodes_set_with_fixed |= subgraph_nodes_set
        small_kg = kg_pruned.subgraph_for_nodes(subgraph_nodes_set_with_fixed)
        if match_small_kg_to_qg(qg, small_kg):
            ret_subgraphs.append(small_kg)
    return ret_subgraphs


# ----------- CODE INTRON; MIGHT BE USEFUL LATER -----------
# def single_vertex_bfs(p_graph: Graph,
#                       p_start_node: Node,
#                       p_visitor: callable = None):
#     queue = collections.deque([p_start_node])
#     visited_res = dict()
#     first_res = None
#     if p_visitor is not None:
#         first_res = p_visitor(p_start_node)
#     visited_res[p_start_node] = first_res
#     while len(queue) > 0:
#         node = queue.popleft()
#         for neighbor in p_graph.neighbors(node):
#             neighbor_node = p_graph.nodes[neighbor]
#             if neighbor_node not in visited_res:
#                 queue.append(neighbor_node)
#                 visit_res = None
#                 if p_visitor is not None:
#                     visit_res = p_visitor(neighbor_node)
#                 visited_res[neighbor_node] = visit_res
#     return visited_res
# ----------- CODE INTRON; MIGHT BE USEFUL LATER -----------

def test1():
    query_graph = Graph.make_from_dicts(
        {'id': ['NCBIGene:123456', 'n01'],
         'type': [NodeType.FIXED, NodeType.QUERY],
         'category': ['gene', 'disease']},
        {'source_id': [1],
         'target_id': [0]})
    knowl_graph = Graph.make_from_dicts(
        {'id': ['NCBIGene:123456', 'DOID:23456', 'DOID:34567', 'HP:54321'],
         'category': ['gene', 'disease', 'disease', 'phenotypic feature']},
        {'source_id': [1, 2, 3],
         'target_id': [0, 0, 2]})
    kg_pruned = prune_unneeded_nodes_and_mark_fixed_nodes(copy.deepcopy(knowl_graph), query_graph)
    small_kg = kg_pruned.subgraph_for_nodes_by_id({'DOID:23456',
                                                   'NCBIGene:123456'})
    res = match_small_kg_to_qg(query_graph, small_kg)
    assert res


def test2():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'DOID:1'],
             'category':  ['gene', 'protein', 'protein', 'disease']},
            {'source_id': [0, 0, 1, 2],
             'target_id': [1, 2, 3, 3]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED],
                                         'category':  ['gene', 'protein', 'disease']},
                                        {'source_id': [0, 1],
                                         'target_id': [1, 2]})
    new_kg = prune_unneeded_nodes_and_mark_fixed_nodes(copy.deepcopy(new_kg),
                                                       query_graph)
    new_kg_subset = new_kg.subgraph_for_nodes_by_id({'NCBIGene:1', 'UniProtKB:2', 'DOID:1'})
    res = match_small_kg_to_qg(query_graph, new_kg_subset)
    assert res


def test3():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'DOID:1'],
             'category':  ['gene', 'protein', 'protein', 'disease']},
            {'source_id': [0, 0, 1, 2],
             'target_id': [1, 2, 3, 3]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED],
                                         'category':  ['gene', 'protein', 'disease']},
                                        {'source_id': [0, 1],
                                         'target_id': [1, 2]})
    new_kg = prune_unneeded_nodes_and_mark_fixed_nodes(copy.deepcopy(new_kg),
                                                       query_graph)
    new_kg_subset = new_kg.subgraph_for_nodes_by_id({'NCBIGene:1', 'UniProtKB:2', 'UniProtKB:1'})
    res = match_small_kg_to_qg(query_graph, new_kg_subset)
    assert not res


def test4():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'DOID:1'],
             'category':  ['gene', 'protein', 'protein', 'disease']},
            {'source_id': [0, 0, 1, 2],
             'target_id': [1, 2, 3, 3]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED],
                                         'category':  ['gene', 'protein', 'disease']},
                                        {'source_id': [0, 1],
                                         'target_id': [1, 2]})
    subgraphs = find_all_kg_subgraphs_for_qg(new_kg, query_graph)
    assert len(subgraphs) == 2


def test5():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'DOID:1', 'HP:1', 'HP:2'],
             'category':  ['gene', 'protein', 'protein', 'disease', 'phenotypic feature', 'phenotypic feature']},
            {'source_id': [0, 0, 1, 2, 3, 3],
             'target_id': [1, 2, 3, 3, 4, 5]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1', 'n02'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED, NodeType.QUERY],
                                         'category':  ['gene', 'protein', 'disease', 'phenotypic feature']},
                                        {'source_id': [0, 1, 2],
                                         'target_id': [1, 2, 3]})
    subgraphs = find_all_kg_subgraphs_for_qg(new_kg, query_graph)
    assert len(subgraphs) == 4


def test6():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'REACTOME:1', 'REACTOME:2', 'DOID:1'],
             'category':  ['gene', 'protein', 'protein', 'pathway', 'pathway', 'disease']},
            {'source_id': [0, 0, 1, 2, 3, 4],
             'target_id': [1, 2, 3, 4, 5, 5]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1', 'n02'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED, NodeType.QUERY],
                                         'category':  ['gene', 'protein', 'disease', 'pathway']},
                                        {'source_id': [0, 1, 3],
                                         'target_id': [1, 3, 2]})
    subgraphs = find_all_kg_subgraphs_for_qg(new_kg, query_graph)
    assert len(subgraphs) == 2


def test7():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'REACTOME:1', 'REACTOME:2', 'DOID:1'],
             'category':  ['gene', 'protein', 'protein', 'pathway', 'pathway', 'disease']},
            {'source_id': [0, 0, 1, 2, 1, 2, 3, 4],
             'target_id': [1, 2, 3, 4, 4, 3, 5, 5]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1', 'n02'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED, NodeType.QUERY],
                                         'category':  ['gene', 'protein', 'disease', 'pathway']},
                                        {'source_id': [0, 1, 3],
                                         'target_id': [1, 3, 2]})
    subgraphs = find_all_kg_subgraphs_for_qg(new_kg, query_graph)
    assert len(subgraphs) == 4


def test8():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'REACTOME:1', 'REACTOME:2', 'DOID:1'],
             'category':  ['gene', 'protein', 'protein', 'pathway', 'pathway', 'disease']},
            {'source_id': [0, 0, 1, 2, 3, 4, 1],
             'target_id': [1, 2, 3, 4, 5, 5, 1]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1', 'n02'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED, NodeType.QUERY],
                                         'category':  ['gene', 'protein', 'disease', 'pathway']},
                                        {'source_id': [0, 1, 3],
                                         'target_id': [1, 3, 2]})
    subgraphs = find_all_kg_subgraphs_for_qg(new_kg, query_graph)
    assert len(subgraphs) == 2


def test9():
    new_kg = Graph.make_from_dicts(
            {'id':        ['NCBIGene:1', 'UniProtKB:1', 'UniProtKB:2', 'REACTOME:1', 'REACTOME:2', 'DOID:1'],
             'category':  ['gene', 'protein', 'protein', 'pathway', 'pathway', 'disease']},
            {'source_id': [0, 0, 1, 2, 3, 4, 1],
             'target_id': [1, 2, 3, 4, 5, 5, 1]})
    query_graph = Graph.make_from_dicts({'id':        ['NCBIGene:1', 'n01', 'DOID:1', 'n02'],
                                         'type':      [NodeType.FIXED, NodeType.QUERY, NodeType.FIXED, NodeType.QUERY],
                                         'category':  ['gene', 'protein', 'disease', 'pathway']},
                                        {'source_id': [0, 1, 3, 1],
                                         'target_id': [1, 3, 2, 1]})
    try:
        find_all_kg_subgraphs_for_qg(new_kg, query_graph)
    except AssertionError:
        return
    assert False


if __name__ == '__main__':
    test1()
    test2()
    test3()
    test4()
    test5()
    test6()
    test7()
    test8()
    test9()

