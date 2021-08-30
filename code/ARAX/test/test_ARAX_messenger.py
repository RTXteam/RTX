#!/usr/bin/env python3

import sys
import os
import pytest

import copy
import json
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_messenger import ARAXMessenger
from ARAX_response import ARAXResponse


def test_create_message_basic():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    assert response.envelope.type == 'translator_reasoner_response'
    assert response.envelope.schema_version == '1.1.0'


def test_create_message_node_edge_types():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    assert isinstance(message.knowledge_graph.nodes, dict)
    assert isinstance(message.knowledge_graph.edges, dict)
    assert isinstance(message.query_graph.nodes, dict)
    assert isinstance(message.query_graph.edges, dict)


def test_add_qnode_basic():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{})
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes['n00'].ids == None


def test_add_qnode_curie_scalar():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{ 'ids': ['UniProtKB:P14136'] })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 1
    assert len(message.query_graph.nodes['n00'].ids) == 1


def test_add_qnode_curie_list():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{ 'ids': ['UniProtKB:P14136','UniProtKB:P35579'] })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 1
    assert len(message.query_graph.nodes['n00'].ids) == 2


def test_add_qnode_name():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{ 'name': 'acetaminophen' })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes['n00'].ids[0] == 'CHEMBL.COMPOUND:CHEMBL112'


def test_add_qnode_type():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{ 'categories': ['biolink:Protein'] })
    assert response.status == 'OK'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 1
    assert message.query_graph.nodes['n00'].categories[0] == 'biolink:Protein'


def test_add_qnode_group_id_is_set_false():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{ 'categories': ['biolink:Protein'], 'is_set' : 'false', 'option_group_id' : '0' })
    assert response.status == 'ERROR'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 0
    assert response.error_code == 'InputMismatch'


def test_add_qnode_bad_name():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{ 'name': 'Big Bird' })
    assert response.status == 'ERROR'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 0
    assert response.error_code == 'UnresolvableNodeName'


def test_add_qnode_duplicate_key():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response, { 'key': 'n00', 'ids': [ 'CHEMBL.COMPOUND:CHEMBL112' ] } )
    assert response.status == 'OK'
    messenger.add_qnode(response, { 'key': 'n00', 'ids': [ 'CHEBI:46195' ] } )
    print(json.dumps(ast.literal_eval(repr(message.query_graph.nodes)), sort_keys=True, indent=2))
    assert response.status == 'ERROR'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.nodes) == 1
    assert response.error_code == 'QNodeDuplicateKey'


def test_add_qedge_duplicate_key():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response, { 'key': 'n00', 'ids': [ 'CHEMBL.COMPOUND:CHEMBL112' ] } )
    messenger.add_qnode(response, { 'key': 'n01', 'categories': [ 'biolink:Protein' ] } )
    messenger.add_qedge(response, { 'key': 'e00', 'subject': 'n00', 'object': 'n01' } )
    assert response.status == 'OK'
    messenger.add_qedge(response, { 'key': 'e00', 'subject': 'n00', 'object': 'n01', 'predicates': [ 'biolink:treats' ] } )
    print(json.dumps(ast.literal_eval(repr(message.query_graph.edges)), sort_keys=True, indent=2))
    assert response.status == 'ERROR'
    assert isinstance(message.query_graph.nodes, dict)
    assert len(message.query_graph.edges) == 1
    assert response.error_code == 'QEdgeDuplicateKey'


def test_add_qnode_bad_parameters():
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    bad_parameters_list = [
        { 'parameters': [ 'ids', 'PICKLES:123' ], 'error_code': 'ParametersNotDict' },
        { 'parameters': { 'pickles': 'on the side' }, 'error_code': 'UnknownParameter' },
        { 'parameters': { 'ids': 'n2', 'category': 'biolink:Disease' }, 'error_code': 'UnknownParameter' },
    ]
    template_response = copy.deepcopy(response)
    for bad_parameters in bad_parameters_list:
        response = copy.deepcopy(template_response)
        message = response.envelope.message
        print(bad_parameters)
        messenger.add_qnode(response, bad_parameters['parameters'])
        assert response.status == 'ERROR'
        assert len(message.query_graph.nodes) == 0
        assert response.error_code == bad_parameters['error_code']


def test_add_qedge_multitest():
    # Set up a message with two nodes
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    assert response.status == 'OK'
    message = response.envelope.message
    messenger.add_qnode(response,{ 'name': 'acetaminophen' })
    assert response.status == 'OK'
    messenger.add_qnode(response,{ 'categories': ['biolink:Protein'] })
    assert response.status == 'OK'

    # Set up a list of parameters to feed to add_qedge() and what the result should be
    parameters_list = [
        { 'status': 'ERROR', 'parameters': [ 'subject', 'n00' ], 'error_code': 'ParametersNotDict' },
        { 'status': 'OK', 'parameters': { 'subject': 'n00', 'object': 'n01' }, 'error_code': 'OK' },
        { 'status': 'OK', 'parameters': { 'subject': 'n00', 'object': 'n01', 'key': 'e99' }, 'error_code': 'OK' },
        { 'status': 'OK', 'parameters': { 'subject': 'n00', 'object': 'n01', 'key': 'e99', 'predicates': ['biolink:physically_interacts_with'] }, 'error_code': 'OK' },
        { 'status': 'ERROR', 'parameters': { 'subject': 'n00' }, 'error_code': 'MissingTargetKey' },
        { 'status': 'ERROR', 'parameters': { 'object': 'n00' }, 'error_code': 'MissingSourceKey' },
        { 'status': 'ERROR', 'parameters': { 'subject': 'n99', 'object': 'n01' }, 'error_code': 'UnknownSourceKey' },
        { 'status': 'ERROR', 'parameters': { 'subject': 'n00', 'object': 'n99' }, 'error_code': 'UnknownTargetKey' },
        { 'status': 'ERROR', 'parameters': { 'pickles': 'on the side' }, 'error_code': 'UnknownParameter' },
    ]

    # Loop over all the parameter sets and try to run it
    template_response = copy.deepcopy(response)
    for parameters in parameters_list:
        response = copy.deepcopy(template_response)
        message = response.envelope.message
        print(parameters)
        messenger.add_qedge(response, parameters['parameters'])
        assert response.status == parameters['status']
        if parameters['status'] == 'OK':
            assert len(message.query_graph.edges) == 1
            continue
        assert len(message.query_graph.edges) == 0
        assert response.error_code == parameters['error_code']


if __name__ == "__main__": pytest.main(['-v'])
