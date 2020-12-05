#!/usr/bin/env python3
# Usage:  python3 ARAX_resultify_testcases.py
#         python3 ARAX_resultify_testcases.py test_issue692

import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from response import Response
from typing import List, Union, Dict, Tuple

import ARAX_resultify
from ARAX_resultify import ARAXResultify
from ARAX_query import ARAXQuery

# is there a better way to import swagger_server?  Following SO posting 16981921
PACKAGE_PARENT = '../../UI/OpenAPI/python-flask-server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from swagger_server.models.edge import Edge
from swagger_server.models.node import Node
from swagger_server.models.q_edge import QEdge
from swagger_server.models.q_node import QNode
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.result import Result
from swagger_server.models.message import Message


def _slim_kg(kg: KnowledgeGraph) -> KnowledgeGraph:
    slimmed_nodes = [Node(id=node.id,
                          type=node.type,
                          name=node.name,
                          qnode_ids=node.qnode_ids) for node in kg.nodes]
    slimmed_edges = [Edge(id=edge.id,
                          source_id=edge.source_id,
                          target_id=edge.target_id,
                          type=edge.type,
                          qedge_ids=edge.qedge_ids) for edge in kg.edges]
    return KnowledgeGraph(nodes=slimmed_nodes, edges=slimmed_edges)


def _create_node(node_id: str, node_type: List[str], qnode_ids: List[str], node_name: str = None) -> Node:
    node = Node(id=node_id,
                type=node_type,
                name=node_name)
    node.qnode_ids = qnode_ids  # Must set outside initializer until (if?) qnode_ids is made an actual class attribute
    return node


def _create_edge(edge_id: str, source_id: str, target_id: str, qedge_ids: List[str], edge_type: str = None) -> Edge:
    edge = Edge(id=edge_id,
                source_id=source_id,
                target_id=target_id,
                type=edge_type)
    edge.qedge_ids = qedge_ids  # Must set outside initializer until (if?) qedge_ids is made an actual class attribute
    return edge


def _print_results_for_debug(results: List[Result]):
    print()
    for result in results:
        print(result.essence)
        for node_binding in result.node_bindings:
            print(f"  {node_binding.qg_id}: {node_binding.kg_id}")
        for edge_binding in result.edge_bindings:
            print(f"  {edge_binding.qg_id}: {edge_binding.kg_id}")


def _get_result_nodes_by_qg_id(result: Result, kg_nodes_map: Dict[str, Node], qg: QueryGraph) -> Dict[str, Dict[str, Node]]:
    return {qnode.id: {node_binding.kg_id: kg_nodes_map[node_binding.kg_id] for node_binding in result.node_bindings
                       if node_binding.qg_id == qnode.id} for qnode in qg.nodes}


def _get_result_edges_by_qg_id(result: Result, kg_edges_map: Dict[str, Edge], qg: QueryGraph) -> Dict[str, Dict[str, Edge]]:
    return {qedge.id: {edge_binding.kg_id: kg_edges_map[edge_binding.kg_id] for edge_binding in result.edge_bindings
                       if edge_binding.qg_id == qedge.id} for qedge in qg.edges}


def _do_arax_query(actions_list: List[str], debug=False) -> Tuple[Response, Message]:
    query = {"previous_message_processing_plan": {"processing_actions": actions_list}}
    araxq = ARAXQuery()
    response = araxq.query(query)
    message = araxq.message
    if response.status != 'OK' or debug:
        _print_results_for_debug(message.results)
        print(response.show(level=response.DEBUG))
    return response, message


def _run_resultify_directly(query_graph: QueryGraph,
                            knowledge_graph: KnowledgeGraph,
                            ignore_edge_direction=True,
                            debug=False) -> Tuple[Response, Message]:
    response = Response()
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
    actions_list = [f"resultify(ignore_edge_direction={ignore_edge_direction})"]
    result = actions_parser.parse(actions_list)
    response.merge(result)
    actions = result.data['actions']
    assert result.status == 'OK'
    resultifier = ARAXResultify()
    message = Message(query_graph=query_graph,
                      knowledge_graph=knowledge_graph,
                      results=[])
    parameters = actions[0]['parameters']
    parameters['debug'] = 'true'
    result = resultifier.apply(message, parameters)
    response.merge(result)
    if response.status != 'OK' or debug:
        _print_results_for_debug(message.results)
        print(response.show(level=response.DEBUG))
    return response, message


def _convert_shorthand_to_qg(shorthand_qnodes: Dict[str, str], shorthand_qedges: Dict[str, str]) -> QueryGraph:
    return QueryGraph(nodes=[QNode(id=qnode_id, is_set=bool(is_set))
                             for qnode_id, is_set in shorthand_qnodes.items()],
                      edges=[QEdge(id=qedge_id, source_id=qnodes.split("--")[0], target_id=qnodes.split("--")[1])
                             for qedge_id, qnodes in shorthand_qedges.items()])


def _convert_shorthand_to_kg(shorthand_nodes: Dict[str, List[str]], shorthand_edges: Dict[str, List[str]]) -> KnowledgeGraph:
    nodes_dict = dict()
    for qnode_id, nodes_list in shorthand_nodes.items():
        for node_id in nodes_list:
            node = nodes_dict.get(node_id, Node(id=node_id, qnode_ids=[]))
            node.qnode_ids.append(qnode_id)
            nodes_dict[node_id] = node
    edges_dict = dict()
    for qedge_id, edges_list in shorthand_edges.items():
        for edge_key in edges_list:
            source_node_id = edge_key.split("--")[0]
            target_node_id = edge_key.split("--")[1]
            edge = edges_dict.get(edge_key, Edge(id=edge_key, source_id=source_node_id, target_id=target_node_id, qedge_ids=[]))
            edge.qedge_ids.append(qedge_id)
            edges_dict[f"{qedge_id}:{edge_key}"] = edge
    return KnowledgeGraph(nodes=list(nodes_dict.values()), edges=list(edges_dict.values()))


def test01():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_ids': ['DOID:12345']},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']},
                    {'id': 'HP:67890',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']},
                    {'id': 'HP:34567',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'DOID:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke02',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'DOID:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke03',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:56789',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke04',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:67890',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:34567',
                     'qedge_ids': ['qe02']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': False},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph)

    assert len(results_list) == 2


def test02():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_ids': ['DOID:12345']},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']},
                    {'id': 'HP:67890',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']},
                    {'id': 'HP:34567',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'DOID:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke02',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'DOID:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke03',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:56789',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke04',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:67890',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:34567',
                     'qedge_ids': ['qe02']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': None},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph)
    assert len(results_list) == 2


def test03():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_ids': ['DOID:12345']},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']},
                    {'id': 'HP:67890',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']},
                    {'id': 'HP:34567',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n02']})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke02',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'DOID:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke03',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:56789',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke04',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:67890',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'HP:34567',
                     'qedge_ids': ['qe02']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': None},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph,
                                                            ignore_edge_direction=True)
    assert len(results_list) == 2


def test04():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_ids': ['DOID:12345']},
                    {'id': 'UniProtKB:56789',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'ChEMBL.COMPOUND:12345',
                     'type': 'chemical_substance',
                     'qnode_ids': ['n02']},
                    {'id': 'ChEMBL.COMPOUND:23456',
                     'type': 'chemical_substance',
                     'qnode_ids': ['n02']})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke02',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke03',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke04',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke06',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe02']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': True},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'chemical_substance',
                     'is_set': False})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n02',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph,
                                                            ignore_edge_direction=True)
    assert len(results_list) == 2


def test05():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_ids': ['DOID:12345']},
                    {'id': 'UniProtKB:56789',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'ChEMBL.COMPOUND:12345',
                     'type': 'chemical_substance',
                     'qnode_ids': ['n02']},
                    {'id': 'ChEMBL.COMPOUND:23456',
                     'type': 'chemical_substance',
                     'qnode_ids': ['n02']})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke02',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke03',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke04',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke06',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe02']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': True},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'chemical_substance',
                     'is_set': False},
                     )

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n02',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    message = Message(query_graph=query_graph,
                      knowledge_graph=knowledge_graph,
                      results=[])
    resultifier = ARAXResultify()
    input_parameters = {'ignore_edge_direction': 'true'}
    resultifier.apply(message, input_parameters)
    assert resultifier.response.status == 'OK'
    assert len(resultifier.message.results) == 2


def test07():
    kg_node_info = ({'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_ids': ['DOID:12345']},
                    {'id': 'UniProtKB:56789',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'ChEMBL.COMPOUND:12345',
                     'type': 'chemical_substance',
                     'qnode_ids': ['n02']},
                    {'id': 'ChEMBL.COMPOUND:23456',
                     'type': 'chemical_substance',
                     'qnode_ids': ['n02']})

    kg_edge_info = ({'edge_id': 'ke01',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke02',
                     'source_id': 'ChEMBL.COMPOUND:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke03',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke04',
                     'source_id': 'ChEMBL.COMPOUND:23456',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke05',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:12345',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke06',
                     'source_id': 'DOID:12345',
                     'target_id': 'UniProtKB:23456',
                     'qedge_ids': ['qe02']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': True},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'chemical_substance',
                     'is_set': False})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n02',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n01'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    response = Response()
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
    actions_list = ['resultify(ignore_edge_direction=true)']
    result = actions_parser.parse(actions_list)
    response.merge(result)
    actions = result.data['actions']
    assert result.status == 'OK'
    resultifier = ARAXResultify()
    message = Message(query_graph=query_graph,
                      knowledge_graph=knowledge_graph,
                      results=[])
    parameters = actions[0]['parameters']
    parameters['debug'] = 'true'
    result = resultifier.apply(message, parameters)
    response.merge(result)
    assert len(message.results) == 2
    assert result.status == 'OK'


def test08():
    shorthand_qnodes = {"n00": "",
                        "n01": ""}
    shorthand_qedges = {"e00": "n00--n01"}
    query_graph = _convert_shorthand_to_qg(shorthand_qnodes, shorthand_qedges)
    shorthand_kg_nodes = {"n00": ["DOID:731"],
                          "n01": ["HP:01", "HP:02", "HP:03", "HP:04"]}
    shorthand_kg_edges = {"e00": ["DOID:731--HP:01", "DOID:731--HP:02", "DOID:731--HP:03", "DOID:731--HP:04"]}
    knowledge_graph = _convert_shorthand_to_kg(shorthand_kg_nodes, shorthand_kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    n01_nodes = {node.id for node in message.knowledge_graph.nodes if "n01" in node.qnode_ids}
    assert len(message.results) == len(n01_nodes)


@pytest.mark.slow
def test09():
    actions = [
        "add_qnode(name=DOID:731, id=n00, type=disease, is_set=false)",
        "add_qnode(type=phenotypic_feature, is_set=false, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "filter_results(action=limit_number_of_results, max_results=100)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message.results) == 100


def test10():
    resultifier = ARAXResultify()
    desc = resultifier.describe_me()
    assert "description" in desc[0]
    assert "ignore_edge_direction" in desc[0]["parameters"]


@pytest.mark.slow
def test_example1():
    actions = [
        "add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(id=qg1, type=protein)",
        "add_qedge(source_id=qg1, target_id=qg0, id=qe0)",
        "expand(edge_id=qe0)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message.results) == len({node.id for node in message.knowledge_graph.nodes if "qg1" in node.qnode_ids})
    assert message.results[0].essence is not None


def test_bfs():
    qg_node_info = ({'id': 'n01',
                     'type': 'protein',
                     'is_set': None},
                    {'id': 'DOID:12345',
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n01',
                     'target_id': 'DOID:12345'},
                    {'edge_id': 'qe02',
                     'source_id': 'DOID:12345',
                     'target_id': 'n02'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    qg = QueryGraph(qg_nodes, qg_edges)
    adj_map = ARAX_resultify._make_adj_maps(qg, directed=False, droploops=True)['both']
    bfs_dists = ARAX_resultify._bfs_dists(adj_map, 'n01')
    assert bfs_dists == {'n01': 0, 'DOID:12345': 1, 'n02': 2}
    bfs_dists = ARAX_resultify._bfs_dists(adj_map, 'DOID:12345')
    assert bfs_dists == {'n01': 1, 'DOID:12345': 0, 'n02': 1}


def test_bfs_in_essence_code():
    kg_node_info = ({'id': 'DOID:12345',
                     'type': 'disease',
                     'qnode_ids': ['n00']},
                    {'id': 'UniProtKB:12345',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'UniProtKB:23456',
                     'type': 'protein',
                     'qnode_ids': ['n01']},
                    {'id': 'FOO:12345',
                     'type': 'gene',
                     'qnode_ids': ['n02']},
                    {'id': 'HP:56789',
                     'type': 'phenotypic_feature',
                     'qnode_ids': ['n03']})

    kg_edge_info = ({'edge_id': 'ke01',
                     'target_id': 'UniProtKB:12345',
                     'source_id': 'DOID:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke02',
                     'target_id': 'UniProtKB:23456',
                     'source_id': 'DOID:12345',
                     'qedge_ids': ['qe01']},
                    {'edge_id': 'ke03',
                     'source_id': 'UniProtKB:12345',
                     'target_id': 'FOO:12345',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke04',
                     'source_id': 'UniProtKB:23456',
                     'target_id': 'FOO:12345',
                     'qedge_ids': ['qe02']},
                    {'edge_id': 'ke05',
                     'source_id': 'FOO:12345',
                     'target_id': 'HP:56789',
                     'qedge_ids': ['qe03']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'id': 'n00',  # DOID:12345
                     'type': 'disease',
                     'is_set': False},
                    {'id': 'n01',
                     'type': 'protein',
                     'is_set': False},
                    {'id': 'n02',
                     'type': 'gene',
                     'is_set': False},
                    {'id': 'n03',  # HP:56789
                     'type': 'phenotypic_feature',
                     'is_set': False})

    qg_edge_info = ({'edge_id': 'qe01',
                     'source_id': 'n00',
                     'target_id': 'n01'},
                    {'edge_id': 'qe02',
                     'source_id': 'n01',
                     'target_id': 'n02'},
                    {'edge_id': 'qe03',
                     'source_id': 'n02',
                     'target_id': 'n03'})

    qg_nodes = [QNode(id=node_info['id'],
                      type=ARAX_resultify.BIOLINK_ENTITY_TYPE_OBJECTS[node_info['type']],
                      is_set=node_info['is_set']) for node_info in qg_node_info]

    qg_edges = [QEdge(id=edge_info['edge_id'],
                      source_id=edge_info['source_id'],
                      target_id=edge_info['target_id']) for edge_info in qg_edge_info]

    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph)
    assert len(results_list) == 2
    assert results_list[0].essence is not None


@pytest.mark.slow
def test_issue680():
    actions = [
        "add_qnode(curie=DOID:14330, id=n00, type=disease)",
        "add_qnode(type=protein, is_set=true, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
        "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
        "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert message.results[0].essence is not None
    kg_edges_map = {edge.id: edge for edge in message.knowledge_graph.edges}
    kg_nodes_map = {node.id: node for node in message.knowledge_graph.nodes}
    for result in message.results:
        result_nodes_by_qg_id = _get_result_nodes_by_qg_id(result, kg_nodes_map, message.query_graph)
        result_edges_by_qg_id = _get_result_edges_by_qg_id(result, kg_edges_map, message.query_graph)
        # Make sure all intermediate nodes are connected to at least one (real, not virtual) edge on BOTH sides
        for n01_node_id in result_nodes_by_qg_id['n01']:
            assert any(edge for edge in result_edges_by_qg_id['e00'].values() if
                       edge.source_id == n01_node_id or edge.target_id == n01_node_id)
            assert any(edge for edge in result_edges_by_qg_id['e01'].values() if
                       edge.source_id == n01_node_id or edge.target_id == n01_node_id)
        # Make sure all edges' nodes actually exist in this result (includes virtual and real edges)
        for qedge_id, edges_map in result_edges_by_qg_id.items():
            qedge = next(qedge for qedge in message.query_graph.edges if qedge.id == qedge_id)
            for edge_id, edge in edges_map.items():
                assert (edge.source_id in result_nodes_by_qg_id[qedge.source_id] and edge.target_id in
                        result_nodes_by_qg_id[qedge.target_id]) or \
                       (edge.target_id in result_nodes_by_qg_id[qedge.source_id] and edge.source_id in
                        result_nodes_by_qg_id[qedge.target_id])


def test_issue686a():
    # Tests that an error is thrown when an invalid parameter is passed to resultify
    actions = [
        'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
        'expand()',
        'resultify(ignore_edge_direction=true, INVALID_PARAMETER_NAME=true)',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert 'INVALID_PARAMETER_NAME' in response.show()


def test_issue686b():
    # Tests that resultify can be called with no parameters passed in
    actions = [
        'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
        'expand()',
        'resultify()',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'


def test_issue686c():
    # Tests that setting ignore_edge_direction to an invalid value results in an error
    actions = [
        'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
        'expand()',
        'resultify(ignore_edge_direction=foo)',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status != 'OK' and 'foo' in response.show()


def test_issue687():
    # Tests that ignore_edge_direction need not be specified
    actions = [
        'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
        'expand()',
        'resultify(debug=true)',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message.results) == len(message.knowledge_graph.nodes)


def test_issue727():
    # Check resultify ignores edge direction appropriately
    shorthand_qnodes = {"n00": "",
                        "n01": ""}
    shorthand_qedges = {"e00": "n00--n01"}
    query_graph = _convert_shorthand_to_qg(shorthand_qnodes, shorthand_qedges)
    shorthand_kg_nodes = {"n00": ["DOID:111"],
                          "n01": ["PR:01", "PR:02"]}
    shorthand_kg_edges = {"e00": ["PR:01--DOID:111", "PR:02--DOID:111"]}  # Edges are reverse direction of QG
    knowledge_graph = _convert_shorthand_to_kg(shorthand_kg_nodes, shorthand_kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    assert len(message.results) == 2


def test_issue731():
    # Return no results if QG is unfulfilled
    shorthand_qnodes = {"n0": "",
                        "n1": "is_set",
                        "n2": ""}
    shorthand_qedges = {"e0": "n0--n1",
                        "e1": "n1--n2"}
    query_graph = _convert_shorthand_to_qg(shorthand_qnodes, shorthand_qedges)
    shorthand_kg_nodes = {"n0": [],
                          "n1": ["UniProtKB:123", "UniProtKB:124"],
                          "n2": ["DOID:122"]}
    shorthand_kg_edges = {"e0": [],
                          "e1": ["UniProtKB:123--DOID:122", "UniProtKB:124--DOID:122"]}
    knowledge_graph = _convert_shorthand_to_kg(shorthand_kg_nodes, shorthand_kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    assert len(message.results) == 0


@pytest.mark.slow
def test_issue731b():
    actions = [
        "add_qnode(name=MONDO:0005737, id=n0, type=disease)",
        "add_qnode(type=protein, id=n1)",
        "add_qnode(type=disease, id=n2)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(edge_id=[e0,e1], kp=ARAX/KG2)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    for result in message.results:
        found_e01 = any(edge_binding.qg_id == 'e1' for edge_binding in result.edge_bindings)
        assert found_e01


def test_issue731c():
    qg = QueryGraph(nodes=[QNode(curie='MONDO:0005737',
                                 id='n0',
                                 type='disease'),
                           QNode(id='n1',
                                 type='protein'),
                           QNode(id='n2',
                                 type='disease')],
                    edges=[QEdge(source_id='n0',
                                 target_id='n1',
                                 id='e0'),
                           QEdge(source_id='n1',
                                 target_id='n2',
                                 id='e1')])
    kg_node_info = ({'id': 'MONDO:0005737',
                     'type': 'disease',
                     'qnode_ids': ['n0']},
                    {'id': 'UniProtKB:Q14943',
                     'type': 'protein',
                     'qnode_ids': ['n1']},
                    {'id': 'DOID:12297',
                     'type': 'disease',
                     'qnode_ids': ['n2']},
                    {'id': 'DOID:11077',
                     'type': 'disease',
                     'qnode_ids': ['n2']})
    kg_edge_info = ({'edge_id': 'UniProtKB:Q14943--MONDO:0005737',
                     'target_id': 'MONDO:0005737',
                     'source_id': 'UniProtKB:Q14943',
                     'qedge_ids': ['e0']},
                    {'edge_id': 'DOID:12297--UniProtKB:Q14943',
                     'target_id': 'UniProtKB:Q14943',
                     'source_id': 'DOID:12297',
                     'qedge_ids': ['e1']})

    kg_nodes = [_create_node(node_id=node_info['id'],
                             node_type=[node_info['type']],
                             qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

    kg_edges = [_create_edge(edge_id=edge_info['edge_id'],
                             source_id=edge_info['source_id'],
                             target_id=edge_info['target_id'],
                             qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

    kg = KnowledgeGraph(nodes=kg_nodes, edges=kg_edges)
    results = ARAX_resultify._get_results_for_kg_by_qg(kg, qg)
    indexes_results_with_single_edge = [index for index, result in enumerate(results) if len(result.edge_bindings) == 1]
    assert len(indexes_results_with_single_edge) == 0


def test_issue740():
    # Tests that self-edges are handled properly
    shorthand_qnodes = {"n00": "",
                        "n01": ""}
    shorthand_qedges = {"e00": "n00--n01"}
    query_graph = _convert_shorthand_to_qg(shorthand_qnodes, shorthand_qedges)
    shorthand_kg_nodes = {"n00": ["UMLS:C0004572"],  # Babesia
                          "n01": ["HP:01", "HP:02", "UMLS:C0004572"]}
    shorthand_kg_edges = {"e00": ["UMLS:C0004572--HP:01", "UMLS:C0004572--HP:02", "UMLS:C0004572--UMLS:C0004572"]}
    knowledge_graph = _convert_shorthand_to_kg(shorthand_kg_nodes, shorthand_kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    assert len(message.results) == 3


def test_issue692():
    kg = KnowledgeGraph(nodes=[],
                        edges=[])
    qg = QueryGraph(nodes=[],
                    edges=[])
    results_list = ARAX_resultify._get_results_for_kg_by_qg(kg, qg)
    assert len(results_list) == 0


def test_issue692b():
    message = Message(query_graph=QueryGraph(nodes=[], edges=[]),
                      knowledge_graph=KnowledgeGraph(nodes=[], edges=[]))
    resultifier = ARAXResultify()
    response = resultifier.apply(message, {})
    assert 'WARNING: no results returned; empty knowledge graph' in response.messages_list()[0]


def test_issue720_1():
    # Test when same node fulfills different qnode_ids within same result
    actions = [
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(type=protein, curie=[UniProtKB:Q02878, UniProtKB:Q9BXM7], is_set=true, id=n01)",
        "add_qnode(type=disease, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand()",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    n02_nodes_in_kg = [node for node in message.knowledge_graph.nodes if "n02" in node.qnode_ids]
    assert len(message.results) == len(n02_nodes_in_kg)
    assert response.status == 'OK'


@pytest.mark.slow
def test_issue720_2():
    # Test when same node fulfills different qnode_ids within same result
    actions = [
        "add_qnode(curie=UMLS:C0158779, id=n00)",
        "add_qnode(curie=UMLS:C0578454, id=n01)",
        "add_qnode(id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(use_synonyms=false, kp=ARAX/KG2)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    n02_nodes_in_kg = [node for node in message.knowledge_graph.nodes if "n02" in node.qnode_ids]
    assert len(message.results) == len(n02_nodes_in_kg)
    assert response.status == 'OK'


def test_issue720_3():
    # Tests when same node fulfills different qnode_ids in different results
    actions = [
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein)",
        "add_qnode(id=n02, type=chemical_substance, curie=CHEMBL.COMPOUND:CHEMBL452076)",  # cilnidipine
        "add_qnode(id=n03, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "add_qedge(id=e01, source_id=n01, target_id=n02)",
        "add_qedge(id=e02, source_id=n02, target_id=n03)",
        "expand(use_synonyms=false)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    snca_id = "UniProtKB:P37840"
    found_result_where_syna_is_n01_and_not_n03 = False
    found_result_where_syna_is_n03_and_not_n01 = False
    for result in message.results:
        syna_as_n01 = any(node_binding for node_binding in result.node_bindings if node_binding.kg_id == snca_id and node_binding.qg_id == 'n01')
        syna_as_n03 = any(node_binding for node_binding in result.node_bindings if node_binding.kg_id == snca_id and node_binding.qg_id == 'n03')
        if syna_as_n01 and not syna_as_n03:
            found_result_where_syna_is_n01_and_not_n03 = True
        elif syna_as_n03 and not syna_as_n01:
            found_result_where_syna_is_n03_and_not_n01 = True
    assert found_result_where_syna_is_n01_and_not_n03 and found_result_where_syna_is_n03_and_not_n01


def test_issue833_extraneous_intermediate_nodes():
    # Test for extraneous intermediate nodes
    shorthand_qnodes = {"n00": "",
                        "n01": "is_set",
                        "n02": "is_set",
                        "n03": ""}
    shorthand_qedges = {"e00": "n00--n01",
                        "e01": "n01--n02",
                        "e02": "n02--n03"}
    query_graph = _convert_shorthand_to_qg(shorthand_qnodes, shorthand_qedges)
    shorthand_kg_nodes = {"n00": ["DOID:1056"],
                          "n01": ["UniProtKB:111", "UniProtKB:222"],
                          "n02": ["MONDO:111", "MONDO:222"],  # Last one is dead-end
                          "n03": ["CHEBI:111"]}
    shorthand_kg_edges = {"e00": ["DOID:1056--UniProtKB:111", "DOID:1056--UniProtKB:222"],
                          "e01": ["UniProtKB:111--MONDO:111", "UniProtKB:222--MONDO:222"],
                          "e02": ["MONDO:111--CHEBI:111"]}
    knowledge_graph = _convert_shorthand_to_kg(shorthand_kg_nodes, shorthand_kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    kg_nodes_map = {node.id: node for node in message.knowledge_graph.nodes}
    kg_edges_map = {edge.id: edge for edge in message.knowledge_graph.edges}
    assert len(message.results) == 1
    for result in message.results:
        result_nodes_by_qg_id = _get_result_nodes_by_qg_id(result, kg_nodes_map, message.query_graph)
        result_edges_by_qg_id = _get_result_edges_by_qg_id(result, kg_edges_map, message.query_graph)
        # Make sure all intermediate nodes are connected to at least one (real, not virtual) edge on BOTH sides
        for n01_node_id in result_nodes_by_qg_id['n01']:
            assert any(edge for edge in result_edges_by_qg_id['e00'].values() if
                       edge.source_id == n01_node_id or edge.target_id == n01_node_id)
            assert any(edge for edge in result_edges_by_qg_id['e01'].values() if
                       edge.source_id == n01_node_id or edge.target_id == n01_node_id)
        # Make sure all edges' nodes actually exist in this result (includes virtual and real edges)
        for qedge_id, edges_map in result_edges_by_qg_id.items():
            qedge = next(qedge for qedge in message.query_graph.edges if qedge.id == qedge_id)
            for edge_id, edge in edges_map.items():
                assert (edge.source_id in result_nodes_by_qg_id[qedge.source_id] and edge.target_id in
                        result_nodes_by_qg_id[qedge.target_id]) or \
                       (edge.target_id in result_nodes_by_qg_id[qedge.source_id] and edge.source_id in
                        result_nodes_by_qg_id[qedge.target_id])


def test_single_node():
    actions = [
        "add_qnode(name=ibuprofen, id=n00)",
        "expand(node_id=n00)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    n00_nodes_in_kg = [node for node in message.knowledge_graph.nodes if "n00" in node.qnode_ids]
    assert len(message.results) == len(n00_nodes_in_kg)


def test_parallel_edges_between_nodes():
    qg_nodes = {"n00": "",
                "n01": "is_set",
                "n02": ""}
    qg_edges = {"e00": "n00--n01",
                "e01": "n01--n02",
                "parallel01": "n01--n02"}
    query_graph = _convert_shorthand_to_qg(qg_nodes, qg_edges)
    kg_nodes = {"n00": ["DOID:11830"],
                "n01": ["UniProtKB:P39060", "UniProtKB:P20849"],
                "n02": ["CHEBI:85164", "CHEBI:29057"]}
    kg_edges = {"e00": ["DOID:11830--UniProtKB:P39060", "DOID:11830--UniProtKB:P20849"],
                "e01": ["UniProtKB:P39060--CHEBI:85164", "UniProtKB:P20849--CHEBI:29057"],
                "parallel01": ["UniProtKB:P39060--CHEBI:85164", "UniProtKB:P20849--CHEBI:29057", "UniProtKB:P39060--CHEBI:29057"]}
    knowledge_graph = _convert_shorthand_to_kg(kg_nodes, kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    kg_nodes_map = {node.id: node for node in message.knowledge_graph.nodes}
    kg_edges_map = {edge.id: edge for edge in message.knowledge_graph.edges}
    n02_nodes = {node_id for node_id, node in kg_nodes_map.items() if "n02" in node.qnode_ids}
    assert len(message.results) == len(n02_nodes)
    # Make sure every n01 node is connected to both an e01 edge and a parallel01 edge in each result
    for result in message.results:
        result_nodes_by_qg_id = _get_result_nodes_by_qg_id(result, kg_nodes_map, message.query_graph)
        result_edges_by_qg_id = _get_result_edges_by_qg_id(result, kg_edges_map, message.query_graph)
        node_ids_used_by_e01_edges = {edge.source_id for edge in result_edges_by_qg_id['e01'].values()}.union({edge.target_id for edge in result_edges_by_qg_id['e01'].values()})
        node_ids_used_by_parallel01_edges = {edge.source_id for edge in result_edges_by_qg_id['parallel01'].values()}.union({edge.target_id for edge in result_edges_by_qg_id['parallel01'].values()})
        for node_id in result_nodes_by_qg_id['n01']:
            assert node_id in node_ids_used_by_e01_edges
            assert node_id in node_ids_used_by_parallel01_edges


def test_issue912_clean_up_kg():
    # Tests that the returned knowledge graph contains only nodes used in the results
    qg_nodes = {"n00": "",
                "n01": "is_set",
                "n02": ""}
    qg_edges = {"e00": "n00--n01",
                "e01": "n01--n02"}
    query_graph = _convert_shorthand_to_qg(qg_nodes, qg_edges)
    kg_nodes = {"n00": ["DOID:11", "DOID:NotConnected"],
                "n01": ["PR:110", "PR:111", "PR:DeadEnd"],
                "n02": ["CHEBI:11", "CHEBI:NotConnected"]}
    kg_edges = {"e00": ["DOID:11--PR:110", "DOID:11--PR:111", "DOID:11--PR:DeadEnd"],
                "e01": ["PR:110--CHEBI:11", "PR:111--CHEBI:11"]}
    knowledge_graph = _convert_shorthand_to_kg(kg_nodes, kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    assert len(message.results) == 1
    returned_kg_node_ids = {node.id for node in message.knowledge_graph.nodes}
    assert returned_kg_node_ids == {"DOID:11", "PR:110", "PR:111", "CHEBI:11"}
    orphan_edges = {edge.id for edge in message.knowledge_graph.edges if not {edge.source_id, edge.target_id}.issubset(returned_kg_node_ids)}
    assert not orphan_edges


def test_issue1146():
    actions = [
        "add_qnode(id=n0, curie=MONDO:0001475, type=disease)",
        "add_qnode(id=n2, type=chemical_substance)",
        "add_qnode(id=n1, type=protein, is_set=true)",
        "add_qedge(id=e0, source_id=n2, target_id=n1, type=physically_interacts_with)",
        "add_qedge(id=e1, source_id=n1, target_id=n0)",
        "expand(kp=ARAX/KG1)",
        "overlay(action=compute_ngd, virtual_relation_label=N2, source_qnode_id=n0, target_qnode_id=n2)",
        "resultify(debug=true)",
        "filter_results(action=limit_number_of_results, max_results=4)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message.results) == 4
    # Make sure every n1 node is connected to an e1 and e0 edge
    for result in message.results:
        result_n1_nodes = {node_binding.kg_id for node_binding in result.node_bindings if node_binding.qg_id == "n1"}
        result_e1_edges = {edge_binding.kg_id for edge_binding in result.edge_bindings if edge_binding.qg_id == "e1"}
        result_e0_edges = {edge_binding.kg_id for edge_binding in result.edge_bindings if edge_binding.qg_id == "e0"}
        for n1_node in result_n1_nodes:
            kg_edges_using_this_node = {edge.id for edge in message.knowledge_graph.edges if n1_node in {edge.source_id, edge.target_id}}
            assert result_e1_edges.intersection(kg_edges_using_this_node)
            assert result_e0_edges.intersection(kg_edges_using_this_node)


if __name__ == '__main__':
    pytest.main(['-v', 'test_ARAX_resultify.py'])
