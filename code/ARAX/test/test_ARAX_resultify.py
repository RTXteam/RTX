#!/usr/bin/env python3
# Usage:  python3 ARAX_resultify_testcases.py
#         python3 ARAX_resultify_testcases.py test_issue692

import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from typing import List, Union, Dict, Tuple, Set, Iterable

import ARAX_resultify
from ARAX_resultify import ARAXResultify
from ARAX_query import ARAXQuery

# is there a better way to import openapi_server?  Following SO posting 16981921
PACKAGE_PARENT = '../../UI/OpenAPI/python-flask-server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.result import Result
from openapi_server.models.message import Message


def _slim_kg(kg: KnowledgeGraph) -> KnowledgeGraph:
    slimmed_nodes = {node_key: Node(category=node.category,
                                    name=node.name,
                                    qnode_keys=node.qnode_keys) for node_key, node in kg.nodes.items()}
    slimmed_edges = {edge_key: Edge(subject=edge.subject,
                                    object=edge.object,
                                    category=edge.category,
                                    qedge_keys=edge.qedge_keys) for edge_key, edge in kg.edges.items()}
    return KnowledgeGraph(nodes=slimmed_nodes, edges=slimmed_edges)


def _create_nodes(kg_node_info: Iterable[Dict[str, any]]) -> Dict[str, Node]:
    nodes_dict = dict()
    for kg_node in kg_node_info:
        node = Node(category=kg_node.get("category"),
                    name=kg_node.get("name"))
        node.qnode_keys = kg_node["qnode_keys"]
        nodes_dict[kg_node["node_key"]] = node
    return nodes_dict


def _create_edges(kg_edge_info: Iterable[Dict[str, any]]) -> Dict[str, Edge]:
    edges_dict = dict()
    for kg_edge in kg_edge_info:
        edge = Edge(subject=kg_edge["subject"],
                    object=kg_edge["object"],
                    predicate=kg_edge.get("predicate"))
        edge.qedge_keys = kg_edge["qedge_keys"]
        edges_dict[kg_edge["edge_key"]] = edge
    return edges_dict


def _create_qnodes(qg_node_info: Iterable[Dict[str, any]]) -> Dict[str, QNode]:
    return {qnode_info["node_key"]: QNode(category=qnode_info['category'],
                                          is_set=qnode_info['is_set']) for qnode_info in qg_node_info}


def _create_qedges(qg_edge_info: Iterable[Dict[str, any]]) -> Dict[str, QEdge]:
    return {qedge_info["edge_key"]: QEdge(subject=qedge_info['subject'],
                                          object=qedge_info['object']) for qedge_info in qg_edge_info}


def _print_results_for_debug(results: List[Result]):
    print()
    for result in results:
        print(result.essence)
        for qnode_key, node_bindings_list in result.node_bindings.items():
            print(f" {qnode_key}:")
            for node_binding in node_bindings_list:
                print(f"  {node_binding.id}")
        for qedge_key, edge_bindings_list in result.edge_bindings.items():
            print(f" {qedge_key}:")
            for edge_binding in edge_bindings_list:
                print(f"  {edge_binding.id}")


def _get_result_node_keys_by_qg_key(result: Result) -> Dict[str, Set[str]]:
    return {qnode_key: {node_binding.id for node_binding in result.node_bindings[qnode_key]} for qnode_key in result.node_bindings}


def _get_result_edge_keys_by_qg_key(result: Result) -> Dict[str, Set[str]]:
    return {qedge_key: {edge_binding.id for edge_binding in result.edge_bindings[qedge_key]} for qedge_key in result.edge_bindings}


def _do_arax_query(actions_list: List[str], debug=False) -> Tuple[ARAXResponse, Message]:
    query = {"operations": {"actions": actions_list}}
    araxq = ARAXQuery()
    response = araxq.query(query)
    message = araxq.message
    if response.status != 'OK':
        if debug:
            _print_results_for_debug(message.results)
        print(response.show(level=response.DEBUG))
    return response, message


def _run_resultify_directly(query_graph: QueryGraph,
                            knowledge_graph: KnowledgeGraph,
                            ignore_edge_direction=True,
                            debug=False) -> Tuple[ARAXResponse, Message]:
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
    actions_list = [f"resultify(ignore_edge_direction={ignore_edge_direction})"]
    result = actions_parser.parse(actions_list)
    response.merge(result)
    actions = result.data['actions']
    assert result.status == 'OK'
    resultifier = ARAXResultify()
    message_original = Message(query_graph=query_graph,
                               knowledge_graph=knowledge_graph,
                               results=[])
    message = ARAXMessenger().from_dict(message_original.to_dict())
    # qnode_keys/qedge_keys are lost when grabbing message from_dict() - so we add them back
    for node_key, node in message_original.knowledge_graph.nodes.items():
        message.knowledge_graph.nodes[node_key].qnode_keys = node.qnode_keys
    for edge_key, edge in message_original.knowledge_graph.edges.items():
        message.knowledge_graph.edges[edge_key].qedge_keys = edge.qedge_keys
    response.envelope.message = message
    parameters = actions[0]['parameters']
    parameters['debug'] = 'true'
    resultifier.apply(response, parameters)
    if response.status != 'OK':
        if debug:
            _print_results_for_debug(message.results)
        print(response.show(level=response.DEBUG))
    return response, message


def _convert_shorthand_to_qg(shorthand_qnodes: Dict[str, str], shorthand_qedges: Dict[str, str]) -> QueryGraph:
    return QueryGraph(nodes={qnode_key: QNode(is_set=bool(is_set)) for qnode_key, is_set in shorthand_qnodes.items()},
                      edges={qedge_key: QEdge(subject=qnodes.split("--")[0],
                                              object=qnodes.split("--")[1]) for qedge_key, qnodes in shorthand_qedges.items()})


def _convert_shorthand_to_kg(shorthand_nodes: Dict[str, List[str]], shorthand_edges: Dict[str, List[str]]) -> KnowledgeGraph:
    nodes_dict = dict()
    for qnode_key, nodes_list in shorthand_nodes.items():
        for node_key in nodes_list:
            node = nodes_dict.get(node_key, Node())
            if not hasattr(node, "qnode_keys"):
                node.qnode_keys = []
            node.qnode_keys.append(qnode_key)
            nodes_dict[node_key] = node
    edges_dict = dict()
    for qedge_key, edges_list in shorthand_edges.items():
        for edge_key in edges_list:
            source_node_key = edge_key.split("--")[0]
            target_node_key = edge_key.split("--")[1]
            edge = edges_dict.get(edge_key, Edge(subject=source_node_key, object=target_node_key))
            if not hasattr(edge, "qedge_keys"):
                edge.qedge_keys = []
            edge.qedge_keys.append(qedge_key)
            edges_dict[f"{qedge_key}:{edge_key}"] = edge
    return KnowledgeGraph(nodes=nodes_dict, edges=edges_dict)


def _get_kg_edge_keys_using_node(node_key: str, kg: KnowledgeGraph) -> Set[str]:
    return {edge_key for edge_key, edge in kg.edges.items() if node_key in {edge.subject, edge.object}}


def test01():
    kg_node_info = ({'node_key': 'UniProtKB:12345',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'UniProtKB:23456',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'qnode_keys': ['DOID:12345']},
                    {'node_key': 'HP:56789',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']},
                    {'node_key': 'HP:67890',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']},
                    {'node_key': 'HP:34567',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']})

    kg_edge_info = ({'edge_key': 'ke01',
                     'subject': 'UniProtKB:12345',
                     'object': 'DOID:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke02',
                     'subject': 'UniProtKB:23456',
                     'object': 'DOID:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke03',
                     'subject': 'DOID:12345',
                     'object': 'HP:56789',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke04',
                     'subject': 'DOID:12345',
                     'object': 'HP:67890',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke05',
                     'subject': 'DOID:12345',
                     'object': 'HP:34567',
                     'qedge_keys': ['qe02']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'node_key': 'n01',
                     'category': 'protein',
                     'is_set': False},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n01',
                     'object': 'DOID:12345'},
                    {'edge_key': 'qe02',
                     'subject': 'DOID:12345',
                     'object': 'n02'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph)

    assert len(results_list) == 2


def test02():
    kg_node_info = ({'node_key': 'UniProtKB:12345',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'UniProtKB:23456',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'qnode_keys': ['DOID:12345']},
                    {'node_key': 'HP:56789',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']},
                    {'node_key': 'HP:67890',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']},
                    {'node_key': 'HP:34567',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']})

    kg_edge_info = ({'edge_key': 'ke01',
                     'subject': 'UniProtKB:12345',
                     'object': 'DOID:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke02',
                     'subject': 'UniProtKB:23456',
                     'object': 'DOID:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke03',
                     'subject': 'DOID:12345',
                     'object': 'HP:56789',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke04',
                     'subject': 'DOID:12345',
                     'object': 'HP:67890',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke05',
                     'subject': 'DOID:12345',
                     'object': 'HP:34567',
                     'qedge_keys': ['qe02']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'node_key': 'n01',
                     'category': 'protein',
                     'is_set': None},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n01',
                     'object': 'DOID:12345'},
                    {'edge_key': 'qe02',
                     'subject': 'DOID:12345',
                     'object': 'n02'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph)
    assert len(results_list) == 2


def test03():
    kg_node_info = ({'node_key': 'UniProtKB:12345',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'UniProtKB:23456',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'qnode_keys': ['DOID:12345']},
                    {'node_key': 'HP:56789',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']},
                    {'node_key': 'HP:67890',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']},
                    {'node_key': 'HP:34567',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n02']})

    kg_edge_info = ({'edge_key': 'ke01',
                     'subject': 'DOID:12345',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke02',
                     'subject': 'UniProtKB:23456',
                     'object': 'DOID:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke03',
                     'subject': 'DOID:12345',
                     'object': 'HP:56789',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke04',
                     'subject': 'DOID:12345',
                     'object': 'HP:67890',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke05',
                     'subject': 'DOID:12345',
                     'object': 'HP:34567',
                     'qedge_keys': ['qe02']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'node_key': 'n01',
                     'category': 'protein',
                     'is_set': None},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n01',
                     'object': 'DOID:12345'},
                    {'edge_key': 'qe02',
                     'subject': 'DOID:12345',
                     'object': 'n02'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph,
                                                            ignore_edge_direction=True)
    assert len(results_list) == 2


def test04():
    kg_node_info = ({'node_key': 'UniProtKB:12345',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'UniProtKB:23456',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'qnode_keys': ['DOID:12345']},
                    {'node_key': 'UniProtKB:56789',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'ChEMBL.COMPOUND:12345',
                     'category': 'chemical_substance',
                     'qnode_keys': ['n02']},
                    {'node_key': 'ChEMBL.COMPOUND:23456',
                     'category': 'chemical_substance',
                     'qnode_keys': ['n02']})

    kg_edge_info = ({'edge_key': 'ke01',
                     'subject': 'ChEMBL.COMPOUND:12345',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke02',
                     'subject': 'ChEMBL.COMPOUND:12345',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke03',
                     'subject': 'ChEMBL.COMPOUND:23456',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke04',
                     'subject': 'ChEMBL.COMPOUND:23456',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke05',
                     'subject': 'DOID:12345',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke06',
                     'subject': 'DOID:12345',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe02']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'node_key': 'n01',
                     'category': 'protein',
                     'is_set': True},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'chemical_substance',
                     'is_set': False})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n02',
                     'object': 'n01'},
                    {'edge_key': 'qe02',
                     'subject': 'DOID:12345',
                     'object': 'n01'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph,
                                                            ignore_edge_direction=True)
    assert len(results_list) == 2


def test05():
    kg_node_info = ({'node_key': 'UniProtKB:12345',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'UniProtKB:23456',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'qnode_keys': ['DOID:12345']},
                    {'node_key': 'UniProtKB:56789',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'ChEMBL.COMPOUND:12345',
                     'category': 'chemical_substance',
                     'qnode_keys': ['n02']},
                    {'node_key': 'ChEMBL.COMPOUND:23456',
                     'category': 'chemical_substance',
                     'qnode_keys': ['n02']})

    kg_edge_info = ({'edge_key': 'ke01',
                     'subject': 'ChEMBL.COMPOUND:12345',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke02',
                     'subject': 'ChEMBL.COMPOUND:12345',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke03',
                     'subject': 'ChEMBL.COMPOUND:23456',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke04',
                     'subject': 'ChEMBL.COMPOUND:23456',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke05',
                     'subject': 'DOID:12345',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke06',
                     'subject': 'DOID:12345',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe02']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)
    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'node_key': 'n01',
                     'category': 'protein',
                     'is_set': True},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'chemical_substance',
                     'is_set': False})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n02',
                     'object': 'n01'},
                    {'edge_key': 'qe02',
                     'subject': 'DOID:12345',
                     'object': 'n01'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    query_graph = QueryGraph(qg_nodes, qg_edges)

    response, message = _run_resultify_directly(query_graph, knowledge_graph, ignore_edge_direction=True)
    assert response.status == 'OK'
    assert len(message.results) == 2


def test07():
    kg_node_info = ({'node_key': 'UniProtKB:12345',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'UniProtKB:23456',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'qnode_keys': ['DOID:12345']},
                    {'node_key': 'UniProtKB:56789',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'ChEMBL.COMPOUND:12345',
                     'category': 'chemical_substance',
                     'qnode_keys': ['n02']},
                    {'node_key': 'ChEMBL.COMPOUND:23456',
                     'category': 'chemical_substance',
                     'qnode_keys': ['n02']})

    kg_edge_info = ({'edge_key': 'ke01',
                     'subject': 'ChEMBL.COMPOUND:12345',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke02',
                     'subject': 'ChEMBL.COMPOUND:12345',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke03',
                     'subject': 'ChEMBL.COMPOUND:23456',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke04',
                     'subject': 'ChEMBL.COMPOUND:23456',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke05',
                     'subject': 'DOID:12345',
                     'object': 'UniProtKB:12345',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke06',
                     'subject': 'DOID:12345',
                     'object': 'UniProtKB:23456',
                     'qedge_keys': ['qe02']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'node_key': 'n01',
                     'category': 'protein',
                     'is_set': True},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'chemical_substance',
                     'is_set': False})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n02',
                     'object': 'n01'},
                    {'edge_key': 'qe02',
                     'subject': 'DOID:12345',
                     'object': 'n01'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    query_graph = QueryGraph(qg_nodes, qg_edges)

    response, message = _run_resultify_directly(query_graph, knowledge_graph, ignore_edge_direction=True)
    assert len(message.results) == 2
    assert response.status == 'OK'


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
    n01_nodes = {node_key for node_key, node in message.knowledge_graph.nodes.items() if "n01" in node.qnode_keys}
    assert message.results and len(message.results) == len(n01_nodes)


@pytest.mark.slow
def test09():
    actions = [
        "add_qnode(name=DOID:731, key=n00, category=biolink:Disease, is_set=false)",
        "add_qnode(category=biolink:PhenotypicFeature, is_set=false, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG1)",
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
        "add_qnode(key=qg0, id=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(key=qg1, category=biolink:Protein)",
        "add_qedge(subject=qg1, object=qg0, key=qe0)",
        "expand(edge_key=qe0, kp=ARAX/KG1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    qg1_nodes = {node_key for node_key, node in message.knowledge_graph.nodes.items() if "qg1" in node.qnode_keys}
    assert message.results and len(message.results) == len(qg1_nodes)
    assert message.results[0].essence is not None


def test_bfs():
    qg_node_info = ({'node_key': 'n01',
                     'category': 'protein',
                     'is_set': None},
                    {'node_key': 'DOID:12345',
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'phenotypic_feature',
                     'is_set': True})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n01',
                     'object': 'DOID:12345'},
                    {'edge_key': 'qe02',
                     'subject': 'DOID:12345',
                     'object': 'n02'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    qg = QueryGraph(qg_nodes, qg_edges)
    adj_map = ARAX_resultify._make_adj_maps(qg, directed=False, droploops=True)['both']
    bfs_dists = ARAX_resultify._bfs_dists(adj_map, 'n01')
    assert bfs_dists == {'n01': 0, 'DOID:12345': 1, 'n02': 2}
    bfs_dists = ARAX_resultify._bfs_dists(adj_map, 'DOID:12345')
    assert bfs_dists == {'n01': 1, 'DOID:12345': 0, 'n02': 1}


def test_bfs_in_essence_code():
    kg_node_info = ({'node_key': 'DOID:12345',
                     'category': 'disease',
                     'qnode_keys': ['n00']},
                    {'node_key': 'UniProtKB:12345',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'UniProtKB:23456',
                     'category': 'protein',
                     'qnode_keys': ['n01']},
                    {'node_key': 'FOO:12345',
                     'category': 'gene',
                     'qnode_keys': ['n02']},
                    {'node_key': 'HP:56789',
                     'category': 'phenotypic_feature',
                     'qnode_keys': ['n03']})

    kg_edge_info = ({'edge_key': 'ke01',
                     'object': 'UniProtKB:12345',
                     'subject': 'DOID:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke02',
                     'object': 'UniProtKB:23456',
                     'subject': 'DOID:12345',
                     'qedge_keys': ['qe01']},
                    {'edge_key': 'ke03',
                     'subject': 'UniProtKB:12345',
                     'object': 'FOO:12345',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke04',
                     'subject': 'UniProtKB:23456',
                     'object': 'FOO:12345',
                     'qedge_keys': ['qe02']},
                    {'edge_key': 'ke05',
                     'subject': 'FOO:12345',
                     'object': 'HP:56789',
                     'qedge_keys': ['qe03']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)

    knowledge_graph = KnowledgeGraph(kg_nodes, kg_edges)

    qg_node_info = ({'node_key': 'n00',  # DOID:12345
                     'category': 'disease',
                     'is_set': False},
                    {'node_key': 'n01',
                     'category': 'protein',
                     'is_set': False},
                    {'node_key': 'n02',
                     'category': 'gene',
                     'is_set': False},
                    {'node_key': 'n03',  # HP:56789
                     'category': 'phenotypic_feature',
                     'is_set': False})

    qg_edge_info = ({'edge_key': 'qe01',
                     'subject': 'n00',
                     'object': 'n01'},
                    {'edge_key': 'qe02',
                     'subject': 'n01',
                     'object': 'n02'},
                    {'edge_key': 'qe03',
                     'subject': 'n02',
                     'object': 'n03'})

    qg_nodes = _create_qnodes(qg_node_info)
    qg_edges = _create_qedges(qg_edge_info)
    query_graph = QueryGraph(qg_nodes, qg_edges)

    results_list = ARAX_resultify._get_results_for_kg_by_qg(knowledge_graph,
                                                            query_graph)
    assert len(results_list) == 2
    assert results_list[0].essence is not None


@pytest.mark.slow
def test_issue680():
    actions = [
        "add_qnode(id=DOID:14330, key=n00, category=biolink:Disease)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicate=biolink:physically_interacts_with)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_key=n02)",
        "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)",
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert message.results[0].essence is not None
    kg = message.knowledge_graph
    for result in message.results:
        result_nodes_by_qg_id = _get_result_node_keys_by_qg_key(result)
        result_edges_by_qg_id = _get_result_edge_keys_by_qg_key(result)
        # Make sure all intermediate nodes are connected to at least one (real, not virtual) edge on BOTH sides
        for n01_node_key in result_nodes_by_qg_id['n01']:
            assert any(edge_key for edge_key in result_edges_by_qg_id['e00'] if
                       kg.edges[edge_key].subject == n01_node_key or kg.edges[edge_key].object == n01_node_key)
            assert any(edge_key for edge_key in result_edges_by_qg_id['e01'] if
                       kg.edges[edge_key].subject == n01_node_key or kg.edges[edge_key].object == n01_node_key)
        # Make sure all edges' nodes actually exist in this result (includes virtual and real edges)
        for qedge_key, edge_keys in result_edges_by_qg_id.items():
            qedge = message.query_graph.edges[qedge_key]
            for edge_key in edge_keys:
                edge = kg.edges[edge_key]
                assert (edge.subject in result_nodes_by_qg_id[qedge.subject] and edge.object in
                        result_nodes_by_qg_id[qedge.object]) or \
                       (edge.object in result_nodes_by_qg_id[qedge.subject] and edge.subject in
                        result_nodes_by_qg_id[qedge.object])


def test_issue686a():
    # Tests that an error is thrown when an invalid parameter is passed to resultify
    actions = [
        'add_qnode(key=qg0, id=CHEMBL.COMPOUND:CHEMBL112)',
        'expand(kp=ARAX/KG1)',
        'resultify(ignore_edge_direction=true, INVALID_PARAMETER_NAME=true)',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert 'INVALID_PARAMETER_NAME' in response.show()


def test_issue686b():
    # Tests that resultify can be called with no parameters passed in
    actions = [
        'add_qnode(key=qg0, id=CHEMBL.COMPOUND:CHEMBL112)',
        'expand(kp=ARAX/KG1)',
        'resultify()',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'


def test_issue686c():
    # Tests that setting ignore_edge_direction to an invalid value results in an error
    actions = [
        'add_qnode(key=qg0, id=CHEMBL.COMPOUND:CHEMBL112)',
        'expand(kp=ARAX/KG1)',
        'resultify(ignore_edge_direction=foo)',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status != 'OK' and 'foo' in response.show()


def test_issue687():
    # Tests that ignore_edge_direction need not be specified
    actions = [
        'add_qnode(key=qg0, id=CHEMBL.COMPOUND:CHEMBL112)',
        'expand(kp=ARAX/KG1)',
        'resultify(debug=true)',
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert message.results and len(message.results) == len(message.knowledge_graph.nodes)


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
        "add_qnode(name=MONDO:0005737, key=n0, category=biolink:Disease)",
        "add_qnode(category=biolink:Protein, key=n1)",
        "add_qnode(category=biolink:Disease, key=n2)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "add_qedge(subject=n1, object=n2, key=e1)",
        "expand(edge_key=[e0,e1], kp=ARAX/KG2)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    for result in message.results:
        found_e01 = result.edge_bindings.get('e1')
        assert found_e01


def test_issue731c():
    qg = QueryGraph(nodes={'n0': QNode(id='MONDO:0005737',
                                       category='biolink:Disease'),
                           'n1': QNode(category='biolink:Protein'),
                           'n2': QNode(category='biolink:Disease')},
                    edges={'e0': QEdge(subject='n0',
                                       object='n1'),
                           'e1': QEdge(subject='n1',
                                       object='n2')})
    kg_node_info = ({'node_key': 'MONDO:0005737',
                     'category': 'disease',
                     'qnode_keys': ['n0']},
                    {'node_key': 'UniProtKB:Q14943',
                     'category': 'protein',
                     'qnode_keys': ['n1']},
                    {'node_key': 'DOID:12297',
                     'category': 'disease',
                     'qnode_keys': ['n2']},
                    {'node_key': 'DOID:11077',
                     'category': 'disease',
                     'qnode_keys': ['n2']})
    kg_edge_info = ({'edge_key': 'UniProtKB:Q14943--MONDO:0005737',
                     'object': 'MONDO:0005737',
                     'subject': 'UniProtKB:Q14943',
                     'qedge_keys': ['e0']},
                    {'edge_key': 'DOID:12297--UniProtKB:Q14943',
                     'object': 'UniProtKB:Q14943',
                     'subject': 'DOID:12297',
                     'qedge_keys': ['e1']})

    kg_nodes = _create_nodes(kg_node_info)
    kg_edges = _create_edges(kg_edge_info)

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
    kg = KnowledgeGraph(nodes=dict(),
                        edges=dict())
    qg = QueryGraph(nodes=dict(),
                    edges=dict())
    results_list = ARAX_resultify._get_results_for_kg_by_qg(kg, qg)
    assert len(results_list) == 0


def test_issue692b():
    query_graph = QueryGraph(nodes=dict(), edges=dict())
    knowledge_graph = KnowledgeGraph(nodes=dict(), edges=dict())
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert 'no results returned; empty knowledge graph' in response.messages_list()[0]['message']


def test_issue720_1():
    # Test when same node fulfills different qnode_keys within same result
    actions = [
        "add_qnode(id=DOID:14330, key=n00)",
        "add_qnode(category=biolink:Protein, id=[UniProtKB:Q02878, UniProtKB:Q9BXM7], is_set=true, key=n01)",
        "add_qnode(category=biolink:Disease, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(kp=ARAX/KG1)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    n02_nodes_in_kg = [node for node in message.knowledge_graph.nodes.values() if "n02" in node.qnode_keys]
    assert message.results and len(message.results) == len(n02_nodes_in_kg)
    assert response.status == 'OK'


@pytest.mark.slow
def test_issue720_2():
    # Test when same node fulfills different qnode_keys within same result
    actions = [
        "add_qnode(id=UMLS:C0158779, key=n00)",
        "add_qnode(id=UMLS:C0578454, key=n01)",
        "add_qnode(key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(use_synonyms=false, kp=ARAX/KG2)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    n02_nodes_in_kg = [node for node in message.knowledge_graph.nodes.values() if "n02" in node.qnode_keys]
    assert message.results and len(message.results) == len(n02_nodes_in_kg)
    assert response.status == 'OK'


def test_issue720_3():
    # Tests when same node fulfills different qnode_keys in different results
    actions = [
        "add_qnode(key=n00, id=DOID:14330)",  # parkinson's
        "add_qnode(key=n01, category=biolink:Protein)",
        "add_qnode(key=n02, category=biolink:ChemicalSubstance, id=CHEMBL.COMPOUND:CHEMBL452076)",  # cilnidipine
        "add_qnode(key=n03, category=biolink:Protein)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "add_qedge(key=e01, subject=n01, object=n02)",
        "add_qedge(key=e02, subject=n02, object=n03)",
        "expand(use_synonyms=false, kp=ARAX/KG1)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    snca_id = "UniProtKB:P37840"
    found_result_where_syna_is_n01_and_not_n03 = False
    found_result_where_syna_is_n03_and_not_n01 = False
    for result in message.results:
        syna_as_n01 = any(node_binding for node_binding in result.node_bindings["n01"] if node_binding.id == snca_id)
        syna_as_n03 = any(node_binding for node_binding in result.node_bindings["n03"] if node_binding.id == snca_id)
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
    for result in message.results:
        result_n01_nodes = {node_binding.id for node_binding in result.node_bindings["n01"]}
        result_e01_edges = {edge_binding.id for edge_binding in result.edge_bindings["e01"]}
        result_e00_edges = {edge_binding.id for edge_binding in result.edge_bindings["e00"]}
        for n01_node_key in result_n01_nodes:
            kg_edges_using_this_node = _get_kg_edge_keys_using_node(n01_node_key, message.knowledge_graph)
            assert result_e01_edges.intersection(kg_edges_using_this_node)
            assert result_e00_edges.intersection(kg_edges_using_this_node)


def test_single_node():
    actions = [
        "add_qnode(name=ibuprofen, key=n00)",
        "expand(node_key=n00, kp=ARAX/KG1)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message.results) > 0


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
    kg_before_resultify = _convert_shorthand_to_kg(kg_nodes, kg_edges)
    response, message = _run_resultify_directly(query_graph, kg_before_resultify)
    kg = message.knowledge_graph
    assert response.status == 'OK'
    n02_nodes = {node_key for node_key, node in kg.nodes.items() if "n02" in node.qnode_keys}
    assert message.results and len(message.results) == len(n02_nodes)
    # Make sure every n01 node is connected to both an e01 edge and a parallel01 edge in each result
    for result in message.results:
        result_node_keys_by_qg_key = _get_result_node_keys_by_qg_key(result)
        result_edge_keys_by_qg_key = _get_result_edge_keys_by_qg_key(result)
        node_keys_used_by_e01_edges = {node_key for edge_key in result_edge_keys_by_qg_key['e01']
                                      for node_key in {kg.edges[edge_key].subject, kg.edges[edge_key].object}}
        node_keys_used_by_parallel01_edges = {node_key for edge_key in result_edge_keys_by_qg_key['parallel01']
                                             for node_key in {kg.edges[edge_key].subject, kg.edges[edge_key].object}}
        for node_key in result_node_keys_by_qg_key['n01']:
            assert node_key in node_keys_used_by_e01_edges
            assert node_key in node_keys_used_by_parallel01_edges


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
    returned_kg_node_keys = set(message.knowledge_graph.nodes)
    assert returned_kg_node_keys == {"DOID:11", "PR:110", "PR:111", "CHEBI:11"}
    orphan_edges = {edge_key for edge_key, edge in message.knowledge_graph.edges.items()
                    if not {edge.subject, edge.object}.issubset(returned_kg_node_keys)}
    assert not orphan_edges


def test_issue1119_a():
    # Run a query to identify chemical substances that are both indicated for and contraindicated for our disease
    actions = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:contraindicated_for, key=e01)",
        "expand(kp=ARAX/KG1)",
        "resultify()"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert message.results
    n01_nodes_contraindicated = {node_binding.id for result in message.results for node_binding in result.node_bindings["n01"]}

    # Verify those chemical substances aren't returned when we make the contraindicated_for edge kryptonite
    actions = [
        "add_qnode(name=DOID:3312, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:indicated_for, key=e00)",
        "add_qedge(subject=n00, object=n01, predicate=biolink:contraindicated_for, exclude=true, key=e01)",
        "expand(kp=ARAX/KG1)",
        "resultify()"
    ]
    kryptonite_response, kryptonite_message = _do_arax_query(actions)
    assert kryptonite_response.status == 'OK'
    assert kryptonite_message.results
    n01_nodes_kryptonite_query = {node_binding.id for result in kryptonite_message.results for node_binding in result.node_bindings["n01"]}
    assert not n01_nodes_contraindicated.intersection(n01_nodes_kryptonite_query)


@pytest.mark.slow
def test_issue1119_b():
    # Tests a perpendicular kryptonite qedge situation
    actions = [
        "add_qnode(id=DOID:3312, key=n00)",
        "add_qnode(category=biolink:Protein, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "add_qnode(category=biolink:Pathway, key=n03)",
        "add_qedge(subject=n01, object=n03, key=e02, exclude=true)",
        "expand(kp=ARAX/KG1)",
        "resultify()"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert message.results
    # Make sure the kryptonite edge and its leaf qnode don't appear in any results
    assert not any(result.node_bindings.get("n03") for result in message.results)
    assert not any(result.edge_bindings.get("e02") for result in message.results)


@pytest.mark.slow
def test_issue1119_c():
    # Test a simple one-hop query with one single-edge option group
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, category=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:positively_regulates)",
        "add_qedge(key=e01, subject=n00, object=n01, predicate=biolink:correlated_with, option_group_id=1)",
        "expand(kp=ARAX/KG2)",
        "resultify(debug=true)",
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert message.results
    assert all(result.edge_bindings.get("e00") for result in message.results)
    # Make sure at least one of our results has the "optional" group 1 edge
    results_with_optional_edge = [result for result in message.results if result.edge_bindings.get("e01")]
    assert results_with_optional_edge

    # Make sure the number of results is the same as if we asked only for the required portion
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, category=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:positively_regulates)",
        "expand(kp=ARAX/KG2)",
        "resultify(debug=true)",
    ]
    response, message_without_option_group = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message_without_option_group.results) == len(message.results)

    # And make sure the number of results with an option group edge makes sense
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        f"add_qnode(key=n01, id=[{', '.join([node_key for node_key, node in message.knowledge_graph.nodes.items() if 'n01' in node.qnode_keys])}])",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:correlated_with)",
        "expand(kp=ARAX/KG2)",
        # Note: skipping resultify here due to issue #1152
    ]
    response, message_option_edge_only = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(results_with_optional_edge) == len([node for node in message_option_edge_only.knowledge_graph.nodes.values()
                                                   if "n01" in node.qnode_keys])


@pytest.mark.slow
def test_issue1119_d():
    # Test one-hop query with multiple single-edge option groups and a required 'not' edge
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, category=biolink:ChemicalSubstance)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:positively_regulates)",
        "add_qedge(key=e01, subject=n00, object=n01, predicate=biolink:correlated_with, option_group_id=1)",
        "add_qedge(key=e02, subject=n00, object=n01, predicate=biolink:affects, option_group_id=2)",
        "add_qedge(key=e03, subject=n00, object=n01, exclude=True, predicate=biolink:contraindicated_for)",
        "expand(kp=ARAX/KG2)",
        "resultify(debug=true)",
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert message.results
    # Make sure every result has a required edge
    assert all(result.edge_bindings.get("e00") for result in message.results)
    assert not any(result.edge_bindings.get("e03") for result in message.results)
    # Make sure our "optional" edges appear in one or more results
    assert any(result for result in message.results if result.edge_bindings.get("e01"))
    assert any(result for result in message.results if result.edge_bindings.get("e02"))
    # Verify there are some results without any optional portion (happens to be true for this query)
    assert any(result for result in message.results if not {"e01", "e02"}.issubset(set(result.edge_bindings)))


@pytest.mark.slow
def test_issue1119_e():
    # Test (curie)--(curie) query where required portion is one-hop and there's one optional group that's two-hop
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, id=CHEBI:48607)",
        "add_qnode(key=n02, category=biolink:Protein, option_group_id=1, is_set=true)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:related_to)",
        "add_qedge(key=e01, subject=n00, object=n02, option_group_id=1, predicate=biolink:affects)",
        "add_qedge(key=e02, subject=n02, object=n01, option_group_id=1, predicate=biolink:physically_interacts_with)",
        "expand()",
        "resultify()",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert len(message.results) == 1
    intermediate_proteins_in_result = {node_binding.id for node_binding in message.results[0].node_bindings["n02"]}
    assert len(intermediate_proteins_in_result) > 1

    # Then make sure when we introduce a not edge on our option group, we see a reduction in the proteins in the result
    actions = [
        "add_qnode(key=n0, id=DOID:3312)",
        "add_qnode(key=n1, id=CHEBI:48607)",
        "add_qnode(key=group1_n1, category=biolink:Protein, option_group_id=1, is_set=true)",
        "add_qnode(key=group1_n2, id=UMLS:C0023692, option_group_id=1)",
        "add_qedge(key=e0, subject=n0, object=n1, predicate=biolink:related_to)",
        "add_qedge(key=group1_e1, subject=n0, object=group1_n1, option_group_id=1, predicate=biolink:affects)",
        "add_qedge(key=group1_e2, subject=group1_n1, object=n1, option_group_id=1, predicate=biolink:physically_interacts_with)",
        "add_qedge(key=group1_ex, subject=group1_n2, object=group1_n1, option_group_id=1, exclude=True)",
        "expand()",
        "resultify()",
        "return(message=true, store=false)"
    ]
    response_x, message_x = _do_arax_query(actions)
    assert response_x.status == 'OK'
    assert len(message_x.results) == 1
    intermediate_proteins_in_result_x = {node_binding.id for node_binding in message_x.results[0].node_bindings["group1_n1"]}
    assert len(intermediate_proteins_in_result) > len(intermediate_proteins_in_result_x)


@pytest.mark.slow
def test_issue1119_f():
    # Test (curie)--(curie) query where required portion is one-hop and there's one 3-hop optional group
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, id=CHEBI:48607)",
        "add_qnode(key=n02, category=biolink:Protein, option_group_id=1, is_set=true)",
        "add_qnode(key=n03, category=biolink:Gene, option_group_id=1, is_set=true)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:related_to)",
        "add_qedge(key=e01, subject=n00, object=n02, option_group_id=1, predicate=biolink:affects)",
        "add_qedge(key=e02, subject=n02, object=n03, option_group_id=1)",
        "add_qedge(key=e03, subject=n03, object=n01, option_group_id=1)",
        "expand()",
        "resultify()",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message.results) == 1
    n02_proteins = {node_binding.id for node_binding in message.results[0].node_bindings["n02"]}

    # Then introduce a not edge going from the option group to the required (start) node
    actions = [
        "add_qnode(key=n00, id=DOID:3312)",
        "add_qnode(key=n01, id=CHEBI:48607)",
        "add_qnode(key=n02, category=biolink:Protein, option_group_id=1, is_set=true)",
        "add_qnode(key=n03, category=biolink:Gene, option_group_id=1, is_set=true)",
        "add_qedge(key=e00, subject=n00, object=n01, predicate=biolink:related_to)",
        "add_qedge(key=e01, subject=n00, object=n02, option_group_id=1, predicate=biolink:affects)",
        "add_qedge(key=e02, subject=n02, object=n03, option_group_id=1)",
        "add_qedge(key=e03, subject=n03, object=n01, option_group_id=1)",
        "add_qedge(key=e0x, subject=n02, object=n00, option_group_id=1, predicate=biolink:prevents, exclude=True)",
        "expand()",
        "resultify()",
        "return(message=true, store=false)"
    ]
    response_x, message_x = _do_arax_query(actions)
    assert response_x.status == 'OK'
    assert len(message_x.results) == 1
    # Make sure this time we have fewer proteins included in our option group
    n02_proteins_x = {node_binding.id for node_binding in message_x.results[0].node_bindings["n02"]}
    assert len(n02_proteins_x) < len(n02_proteins)


def test_issue1146_a():
    actions = [
        "add_qnode(key=n0, id=MONDO:0001475, category=biolink:Disease)",
        "add_qnode(key=n2, category=biolink:ChemicalSubstance)",
        "add_qnode(key=n1, category=biolink:Protein, is_set=true)",
        "add_qedge(key=e0, subject=n2, object=n1, predicate=biolink:physically_interacts_with)",
        "add_qedge(key=e1, subject=n1, object=n0)",
        "expand(kp=ARAX/KG1)",
        "overlay(action=compute_ngd, virtual_relation_label=N2, subject_qnode_key=n0, object_qnode_key=n2)",
        "resultify(debug=true)",
        "filter_results(action=limit_number_of_results, max_results=4)",
    ]
    response, message = _do_arax_query(actions)
    assert response.status == 'OK'
    assert len(message.results) == 4
    # Make sure every n1 node is connected to an e1 and e0 edge
    for result in message.results:
        result_n1_nodes = {node_binding.id for node_binding in result.node_bindings["n1"]}
        result_e1_edges = {edge_binding.id for edge_binding in result.edge_bindings["e1"]}
        result_e0_edges = {edge_binding.id for edge_binding in result.edge_bindings["e0"]}
        for n1_node in result_n1_nodes:
            kg_edges_using_this_node = _get_kg_edge_keys_using_node(n1_node, message.knowledge_graph)
            assert result_e1_edges.intersection(kg_edges_using_this_node)
            assert result_e0_edges.intersection(kg_edges_using_this_node)


def test_disconnected_qg():
    # Ensure an (informative) error is thrown when the QG is disconnected (has more than one component)
    actions = [
        "add_qnode(name=ibuprofen, key=n00)",
        "add_qnode(name=acetaminophen, key=n01)",
        "add_qnode(category=biolink:Disease, key=n02)",
        "add_qedge(key=e00, subject=n01, object=n02)",
        "expand(kp=ARAX/KG1)",
        "resultify(debug=true)",
        "return(message=true, store=false)"
    ]
    response, message = _do_arax_query(actions)
    assert response.status != 'OK'
    assert "QG is disconnected" in response.show()


def test_recompute_qg_keys():
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
    assert message.results
    # Clear all qnode_keys/qedge_keys from the KG
    for node_key, node in message.knowledge_graph.nodes.items():
        node.qnode_keys = []
    for edge_key, edge in message.knowledge_graph.edges.items():
        edge.qedge_keys = []
    # Then recompute qg keys and make sure look ok
    resultifier = ARAXResultify()
    resultifier.recompute_qg_keys(response)
    assert response.status == 'OK'
    kg = response.envelope.message.knowledge_graph
    assert kg.nodes and kg.edges
    for node_key, node in kg.nodes.items():
        assert node.qnode_keys == ["n00"] if node_key in shorthand_kg_nodes["n00"] else ["n01"]
    for edge_key, edge in kg.edges.items():
        assert edge.qedge_keys == ["e00"]


def test_multi_node_edgeless_qg():
    shorthand_qnodes = {"n00": "",
                        "n01": ""}
    shorthand_qedges = {}
    query_graph = _convert_shorthand_to_qg(shorthand_qnodes, shorthand_qedges)
    shorthand_kg_nodes = {"n00": ["CHEMBL.COMPOUND:CHEMBL635"],
                          "n01": ["MESH:D052638"]}
    shorthand_kg_edges = {}
    knowledge_graph = _convert_shorthand_to_kg(shorthand_kg_nodes, shorthand_kg_edges)
    response, message = _run_resultify_directly(query_graph, knowledge_graph)
    assert response.status == 'OK'
    assert len(message.results) == 1


if __name__ == '__main__':
    pytest.main(['-v', 'test_ARAX_resultify.py'])
