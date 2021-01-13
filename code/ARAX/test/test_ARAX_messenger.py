#!/usr/bin/env python3

import sys
import os
import pytest

import copy
import json
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_messenger import ARAXMessenger


def test_create_message_basic():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    assert message.type == 'translator_reasoner_message'
    assert message.schema_version == '0.9.3'


def test_create_message_node_edge_types():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    assert isinstance(message.knowledge_graph.nodes, list)
    assert isinstance(message.knowledge_graph.edges, list)
    assert isinstance(message.query_graph.nodes, list)
    assert isinstance(message.query_graph.edges, list)


def test_add_qnode_basic():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message,{})
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, list)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes[0].id == 'n00'


def test_add_qnode_curie_scalar():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message, { 'curie': 'UniProtKB:P14136' })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, list)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes[0].id == 'n00'
    assert message.query_graph.nodes[0].curie == 'UniProtKB:P14136'


def test_add_qnode_curie_list():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message, { 'curie': ['UniProtKB:P14136','UniProtKB:P35579'] })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, list)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes[0].id == 'n00'
    assert len(message.query_graph.nodes[0].curie) == 2


def test_add_qnode_name():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message, { 'name': 'acetaminophen' })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, list)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes[0].id == 'n00'
    assert message.query_graph.nodes[0].curie == 'CHEMBL.COMPOUND:CHEMBL112'


def test_add_qnode_type():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message, { 'type': 'protein' })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, list)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes[0].id == 'n00'
    assert message.query_graph.nodes[0].type == 'protein'


def test_add_qnode_group_id_is_set_false():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message, { 'type': 'protein', 'is_set' : 'false', 'option_group_id' : '0' })
    assert response.status == 'ERROR'
    assert isinstance(message.query_graph.nodes, list)
    assert len(message.query_graph.nodes) == 0
    assert response.error_code == 'InputMismatch'

def test_add_qnode_bad_name():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message, { 'name': 'Big Bird' })
    assert response.status == 'ERROR'
    assert isinstance(message.query_graph.nodes, list)
    assert len(message.query_graph.nodes) == 0
    assert response.error_code == 'UnresolvableNodeName'


def test_add_qnode_bad_parameters():
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    bad_parameters_list = [
        { 'parameters': [ 'curie', 'PICKLES:123' ], 'error_code': 'ParametersNotDict' },
        { 'parameters': { 'curie': 'UniProtKB:P14136', 'is_set': 'true' }, 'error_code': 'CurieScalarButIsSetTrue' },
        { 'parameters': { 'pickles': 'on the side' }, 'error_code': 'UnknownParameter' },
    ]
    reference_message = copy.deepcopy(message)
    for bad_parameters in bad_parameters_list:
        message = copy.deepcopy(reference_message)
        print(bad_parameters)
        response = messenger.add_qnode(message, bad_parameters['parameters'])
        assert response.status == 'ERROR'
        assert len(message.query_graph.nodes) == 0
        assert response.error_code == bad_parameters['error_code']


def test_add_qedge_multitest():
    # Set up a message with two nodes
    messenger = ARAXMessenger()
    response = messenger.create_message()
    assert response.status == 'OK'
    message = response.data['message']
    response = messenger.add_qnode(message, { 'name': 'acetaminophen' })
    assert response.status == 'OK'
    response = messenger.add_qnode(message, { 'type': 'protein' })
    assert response.status == 'OK'

    # Set up a list of parameters to feed to add_qedge() and what the result should be
    parameters_list = [
        { 'status': 'ERROR', 'parameters': [ 'source_id', 'n00' ], 'error_code': 'ParametersNotDict' },
        { 'status': 'OK', 'parameters': { 'source_id': 'n00', 'target_id': 'n01' }, 'error_code': 'OK' },
        { 'status': 'OK', 'parameters': { 'source_id': 'n00', 'target_id': 'n01', 'id': 'e99' }, 'error_code': 'OK' },
        { 'status': 'OK', 'parameters': { 'source_id': 'n00', 'target_id': 'n01', 'id': 'e99', 'type': 'physically_interacts_with' }, 'error_code': 'OK' },
        { 'status': 'ERROR', 'parameters': { 'source_id': 'n00' }, 'error_code': 'MissingTargetId' },
        { 'status': 'ERROR', 'parameters': { 'target_id': 'n00' }, 'error_code': 'MissingSourceId' },
        { 'status': 'ERROR', 'parameters': { 'source_id': 'n99', 'target_id': 'n01' }, 'error_code': 'UnknownSourceId' },
        { 'status': 'ERROR', 'parameters': { 'source_id': 'n00', 'target_id': 'n99' }, 'error_code': 'UnknownTargetId' },
        { 'status': 'ERROR', 'parameters': { 'pickles': 'on the side' }, 'error_code': 'UnknownParameter' },
    ]

    # Loop over all the parameter sets and try to run it
    reference_message = copy.deepcopy(message)
    for parameters in parameters_list:
        message = copy.deepcopy(reference_message)
        print(parameters)
        response = messenger.add_qedge(message, parameters['parameters'])
        assert response.status == parameters['status']
        if parameters['status'] == 'OK':
            assert len(message.query_graph.edges) == 1
            continue
        assert len(message.query_graph.edges) == 0
        assert response.error_code == parameters['error_code']


if __name__ == "__main__": pytest.main(['-v'])
