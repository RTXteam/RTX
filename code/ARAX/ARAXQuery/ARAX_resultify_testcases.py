#!/usr/bin/env python3
# Usage:  python3 ARAX_resultify_testcases.py
#         python3 ARAX_resultify_testcases.py test_issue692

import os
import sys
import unittest
from response import Response
from typing import List, Union

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
from swagger_server.models.node_binding import NodeBinding
from swagger_server.models.edge_binding import EdgeBinding
from swagger_server.models.biolink_entity import BiolinkEntity
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


def _create_edge(source_id: str, target_id: str, qedge_ids: List[str], edge_id: str = None, edge_type: str = None) -> Edge:
    edge = Edge(id=edge_id,
                source_id=source_id,
                target_id=target_id,
                type=edge_type)
    edge.qedge_ids = qedge_ids  # Must set outside initializer until (if?) qedge_ids is made an actual class attribute
    return edge


def _do_arax_query(query: str) -> List[Union[Response, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    return [response, araxq.message]


class TestARAXResultify(unittest.TestCase):
    def test01(self):
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
                         'qedge_ids': ['qe02']},
                        {'edge_id': 'ke06',
                         'source_id': 'HP:56789',
                         'target_id': 'HP:67890',
                         'qedge_ids': None})

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

    def test02(self):
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
                         'qedge_ids': ['qe02']},
                        {'edge_id': 'ke06',
                         'source_id': 'HP:56789',
                         'target_id': 'HP:67890',
                         'qedge_ids': None})

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

    def test03(self):
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
                         'qedge_ids': ['qe02']},
                        {'edge_id': 'ke06',
                         'source_id': 'HP:56789',
                         'target_id': 'HP:67890',
                         'qedge_ids': None})

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

    def test04(self):
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
                         'qedge_ids': ['qe02']},
                        {'edge_id': 'ke08',
                         'source_id': 'UniProtKB:12345',
                         'target_id': 'UniProtKB:23456',
                         'qedge_ids': None})

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
                         'is_set': True})

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
                                                                qg_nodes_override_treat_is_set_as_false={'n02'},
                                                                ignore_edge_direction=True)
        assert len(results_list) == 2

    def test05(self):
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
                         'qedge_ids': ['qe02']},
                        {'edge_id': 'ke08',
                         'source_id': 'UniProtKB:12345',
                         'target_id': 'UniProtKB:23456',
                         'qedge_ids': None})

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
                         'is_set': True})

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
        input_parameters = {'ignore_edge_direction': 'true',
                            'force_isset_false': ['n02']}
        resultifier.apply(message, input_parameters)
        assert resultifier.response.status == 'OK'
        assert len(resultifier.message.results) == 2

    def test06(self):
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
                         'qedge_ids': ['qe02']},
                        {'edge_id': 'ke08',
                         'source_id': 'UniProtKB:12345',
                         'target_id': 'UniProtKB:23456',
                         'qedge_ids': None})

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
                         'is_set': True})

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
        input_parameters = {'ignore_edge_direction': 'true',
                            'force_isset_false': ['n07']}
        resultifier.apply(message, input_parameters)
        assert resultifier.response.status != 'OK'
        assert len(resultifier.message.results) == 0

    def test07(self):
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
                         'qedge_ids': ['qe02']},
                        {'edge_id': 'ke08',
                         'source_id': 'UniProtKB:12345',
                         'target_id': 'UniProtKB:23456',
                         'qedge_ids': None})

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
                         'is_set': True})

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
        actions_list = ['resultify(ignore_edge_direction=true,force_isset_false=[n02])']
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

    def test08(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(type=disease, curie=DOID:731, id=n00)",
            "add_qnode(type=phenotypic_feature, is_set=false, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'
        assert len(message.results) == 3223

    def test09(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                "add_qnode(name=DOID:731, id=n00, type=disease, is_set=false)",
                "add_qnode(type=phenotypic_feature, is_set=false, id=n01)",
                "add_qedge(source_id=n00, target_id=n01, id=e00)",
                "expand(edge_id=e00)",
                "resultify(ignore_edge_direction=true, debug=true)",
                "filter_results(action=limit_number_of_results, max_results=100)",
                "return(message=true, store=false)"]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'
        assert len(message.results) == 100

    def test10(self):
        resultifier = ARAXResultify()
        desc = resultifier.describe_me()
        assert 'brief_description' in desc[0]
        assert 'force_isset_false' in desc[0]
        assert 'ignore_edge_direction' in desc[0]

    def test_example1(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
                                                          'create_message',
                                                          'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
                                                          'add_qnode(id=qg1, type=protein)',
                                                          'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
                                                          'expand(edge_id=qe0)',
                                                          'resultify(ignore_edge_direction=true, debug=true)',
                                                          "filter_results(action=limit_number_of_results, max_results=10)",
                                                          "return(message=true, store=true)",
                                                      ]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'
        assert len(message.results) == 10
        assert message.results[0].essence is not None

    def test_example2(self):
        # NOTE: This test is currently failing due to Filter error (#784)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
            "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_edge_type=P1)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)",
        ]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'
        assert len(message.results) == 38
        assert message.results[0].essence is not None

    def test_bfs(self):
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

    def test_bfs_in_essence_code(self):
        # FIXME: This test is currently failing because the KG data is flawed (edges use nodes of the wrong qnode_ids)
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
                         'qnode_ids': ['HP:56789']},
                        {'id': 'FOO:12345',
                         'type': 'gene',
                         'qnode_ids': ['n02']})

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

        qg_node_info = ({'id': 'n01',
                         'type': 'protein',
                         'is_set': False},
                        {'id': 'DOID:12345',
                         'type': 'disease',
                         'is_set': False},
                        {'id': 'HP:56789',
                         'type': 'phenotypic_feature',
                         'is_set': False},
                        {'id': 'n02',
                         'type': 'gene',
                         'is_set': False})

        qg_edge_info = ({'edge_id': 'qe01',
                         'source_id': 'DOID:12345',
                         'target_id': 'n01'},
                        {'edge_id': 'qe02',
                         'source_id': 'n02',
                         'target_id': 'HP:56789'},
                        {'edge_id': 'qe03',
                         'source_id': 'n01',
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
        assert results_list[0].essence is not None

    def test_issue680(self):
        # NOTE: This test is currently failing due to Filter error (#784)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
            "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_edge_type=P1)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "filter_results(action=limit_number_of_results, max_results=1)",
            "return(message=true, store=false)",
        ]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'
        assert len(message.results) == 1
        result = message.results[0]
        resgraph = result.result_graph
        count_drug_prot = 0
        count_disease_prot = 0
        for edge in resgraph.edges:
            if edge.target_id.startswith("CHEMBL.") and edge.source_id.startswith("UniProtKB:"):
                count_drug_prot += 1
            if edge.target_id.startswith("DOID:") and edge.source_id.startswith("UniProtKB:"):
                count_disease_prot += 1
        assert count_drug_prot == count_disease_prot
        assert result.essence is not None

    def test_issue686a(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
            'create_message',
            'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
            'add_qnode(id=qg1, type=protein)',
            'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
            'expand(edge_id=qe0)',
            'resultify(ignore_edge_direction=true, INVALID_PARAMETER_NAME=true)'
        ]}}
        [response, message] = _do_arax_query(query)
        assert 'INVALID_PARAMETER_NAME' in response.show()

    def test_issue686b(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
            'create_message',
            'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
            'add_qnode(id=qg1, type=protein)',
            'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
            'add_qedge(source_id=qg0, target_id=qg1, id=qe0)',
            'expand(edge_id=qe0)',
            'resultify()'
        ]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'

    def test_issue686c(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
            'create_message',
            'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
            'add_qnode(id=qg1, type=protein)',
            'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
            'add_qedge(source_id=qg0, target_id=qg1, id=qe0)',
            'expand(edge_id=qe0)',
            'resultify(ignore_edge_direction=foo)'
        ]}}
        [response, message] = _do_arax_query(query)
        assert response.status != 'OK' and 'foo' in response.show()

    def test_issue687(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
            'create_message',
            'add_qnode(id=qg0, curie=CHEMBL.COMPOUND:CHEMBL112)',
            'add_qnode(id=qg1, type=protein)',
            'add_qedge(source_id=qg1, target_id=qg0, id=qe0)',
            'add_qedge(source_id=qg0, target_id=qg1, id=qe1)',
            'expand(edge_id=qe0)',
            'resultify(debug=true)',
            "return(message=true, store=true)"
        ]}}
        _do_arax_query(query)

    def test_issue727(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
            "add_qnode(name=CHEMBL.COMPOUND:CHEMBL1276308, id=n00)",
            "add_qnode(type=protein, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "resultify()"]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'

    def test_issue731(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                "add_qnode(name=MONDO:0005737, id=n0, type=disease)",
                "add_qnode(type=protein, id=n1)",
                "add_qnode(type=disease, id=n2)",
                "add_qedge(source_id=n0, target_id=n1, id=e0)",
                "add_qedge(source_id=n1, target_id=n2, id=e1)",
                "expand(edge_id=[e0,e1], kp=ARAX/KG2)",
                "resultify(debug=true)"]}}
        [response, message] = _do_arax_query(query)
        assert response.status == 'OK'
        assert len(message.results) >= 81

    def test_issue731b(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
                "add_qnode(name=MONDO:0005737, id=n0, type=disease)",
                "add_qnode(type=protein, id=n1)",
                "add_qnode(type=disease, id=n2)",
                "add_qedge(source_id=n0, target_id=n1, id=e0)",
                "add_qedge(source_id=n1, target_id=n2, id=e1)",
                "expand(edge_id=[e0,e1], kp=ARAX/KG2)",
                "resultify(debug=true)"]}}
        [response, message] = _do_arax_query(query)
        for result in message.results:
            result_graph = result.result_graph
            found_e01 = False
            for edge in result_graph.edges:
                if 'e1' in edge.qedge_ids:
                    found_e01 = True
                    continue
            assert found_e01

    def test_issue731c(self):
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
        kg_edge_info = ({'target_id': 'MONDO:0005737',
                         'source_id': 'UniProtKB:Q14943',
                         'qedge_ids': ['e0']},
                        {'target_id': 'UniProtKB:Q14943',
                         'source_id': 'DOID:12297',
                         'qedge_ids': ['e1']})

        kg_nodes = [_create_node(node_id=node_info['id'],
                                 node_type=[node_info['type']],
                                 qnode_ids=node_info['qnode_ids']) for node_info in kg_node_info]

        kg_edges = [_create_edge(source_id=edge_info['source_id'],
                                 target_id=edge_info['target_id'],
                                 qedge_ids=edge_info['qedge_ids']) for edge_info in kg_edge_info]

        kg = KnowledgeGraph(nodes=kg_nodes, edges=kg_edges)
        results = ARAX_resultify._get_results_for_kg_by_qg(kg, qg)
        indexes_results_with_single_edge = [index for index, result in enumerate(results) if len(result.result_graph.edges) == 1]
        assert len(indexes_results_with_single_edge) == 0

    def test_issue740(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
                "add_qnode(name=babesia, id=n00)",
                "add_qnode(id=n01)",
                "add_qedge(source_id=n00, target_id=n01, id=e00)",
                "expand(edge_id=e00, kp=ARAX/KG2)",
                "resultify()"]}}
        [response, message] = _do_arax_query(query)
        n01_nodes_in_kg = [node for node in message.knowledge_graph.nodes if "n01" in node.qnode_ids]
        assert len(message.results) == len(n01_nodes_in_kg)
        assert response.status == 'OK'

    def test_issue692(self):
        kg = KnowledgeGraph(nodes=[],
                            edges=[])
        qg = QueryGraph(nodes=[],
                        edges=[])
        results_list = ARAX_resultify._get_results_for_kg_by_qg(kg, qg)
        assert len(results_list) == 0

    def test_issue692b(self):
        message = Message(query_graph=QueryGraph(nodes=[], edges=[]),
                          knowledge_graph=KnowledgeGraph(nodes=[], edges=[]))
        resultifier = ARAXResultify()
        response = resultifier.apply(message, {})
        assert 'WARNING: no results returned; empty knowledge graph' in response.messages_list()[0]

    def test_issue720(self):
        query = {"previous_message_processing_plan": {"processing_actions": [
                "add_qnode(curie=DOID:14330, id=n00)",
                "add_qnode(type=protein, curie=[UniProtKB:Q02878, UniProtKB:Q9BXM7], is_set=true, id=n01)",
                "add_qnode(type=disease, id=n02)",
                "add_qedge(source_id=n00, target_id=n01, id=e00)",
                "add_qedge(source_id=n01, target_id=n02, id=e01)",
                "expand()",
                "resultify(debug=true)"]}}
        [response, message] = _do_arax_query(query)
        n02_nodes_in_kg = [node for node in message.knowledge_graph.nodes if "n02" in node.qnode_ids]
        assert len(message.results) == len(n02_nodes_in_kg)
        assert response.status == 'OK'

    # ----------- set this up as a test suite at some point? ----------
    # def _run_module_leveltests(self):
    #     self.test01()
    #     self.test02()
    #     self.test03()
    #     self.test04()
    #     self.test_bfs()
    #     self.test_bfs_in_essence_code()
    #     self.test_issue731c()
    #     self.test_issue692()
    #     self.test_issue692b()

    # ----------- set this up as a test suite at some point? ----------
    # def _run_arax_classtests(self):
    #     self.test05()
    #     self.test06()
    #     self.test07()
    #     self.test08()
    #     self.test09()
    #     self.test10()
    #     self.test_example1()
    #     self.test_example2()
    #     self.test_issue680()
    # #   self.test_example3()  # this has been commented out because the test takes a long time to run
    #     self.test_issue686a()
    #     self.test_issue686b()
    #     self.test_issue686c()
    #     self.test_issue687()
    #     self.test_issue727()
    #     self.test_issue731()
    #     self.test_issue731b()
    #     self.test_issue740()


def test_example3():
    query = {"previous_message_processing_plan": {"processing_actions": [
        "add_qnode(name=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01])",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_edge_type=C1, source_qnode_id=n00, target_qnode_id=n01)",
        ("filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, "
         "direction=below, threshold=3, remove_connected_nodes=t, qnode_id=n01)"),
        "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
        "overlay(action=compute_ngd, virtual_edge_type=N1, source_qnode_id=n01, target_qnode_id=n02)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=ngd, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n02)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=true)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) in [47, 48]  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert message.results[0].essence is not None


def main():
    if len(sys.argv) > 1:
        tester = TestARAXResultify()
        for func_name in sys.argv[1:len(sys.argv)]:
            getattr(TestARAXResultify, func_name)(tester)
    else:
        unittest.main(verbosity=2)


if __name__ == '__main__':
    main()
