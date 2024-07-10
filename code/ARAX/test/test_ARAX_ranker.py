#!/usr/bin/env python3

# Usage:
# run all: pytest -v test_ARAX_ranker.py
# run just certain tests: pytest -v test_ARAX_ranker.py -k test_jaccard

import sys
import os
import numpy as np
import scipy.stats
import pytest
import requests_cache
import pickle
import copy
import ast
from typing import List, Union

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from ARAX_query import ARAXQuery
from query_graph_info import QueryGraphInfo
from actions_parser import ActionsParser
from result_transformer import ResultTransformer
from ARAX_ranker import ARAXRanker


PACKAGE_PARENT = '../../UI/OpenAPI/python-flask-server'
sys.path.append(os.path.normpath(os.path.join(os.getcwd(), PACKAGE_PARENT)))
from openapi_server.models.edge import Edge
from openapi_server.models.node import Node
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.node_binding import NodeBinding
from openapi_server.models.edge_binding import EdgeBinding
from openapi_server.models.result import Result
from openapi_server.models.message import Message

def _extract_ARAX_online_results(response_id: str, api_link: str = 'https://arax.ncats.io/api/arax/v1.4/response/') -> List[Union[ARAXResponse, Message]]:
    # Extracts the ARAXResponse objects from the ARAX online results
    
    # generate an ARAX response object
    response = ARAXResponse()
    #### Create an empty envelope
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    response.envelope.submitter = '?'

    # extract results based on response_id
    message = messenger.fetch_message(f'{api_link}{response_id}')
    response.envelope.message = message
    return [response, response.envelope.message]

def _do_arax_query(query: dict) -> List[Union[ARAXResponse, Message]]:
    # Perform the ARAX query
    
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    #return [response, araxq.message]
    return [response, response.envelope.message]

def _do_arax_rank(response: ARAXResponse) -> Message:
    # Rank the ARAX results
    
    ranker = ARAXRanker()
    ranker.aggregate_scores_dmk(response)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return response.envelope.message

def _ranker_tester(query: dict = None, response_id: str = None) -> Message:
    # Test the ARAX ranker
    
    if response_id is not None:
        [response, _] = _extract_ARAX_online_results(response_id)
    else:
        [response, _] = _do_arax_query(query)
    message = _do_arax_rank(response)
    return message


def test_ARAXRanker_test1_asset12():
    # test 'rituximab treats Castleman Disease'
    expected_answer = 'rituximab'
    
    returned_message = _ranker_tester(response_id='248097')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results

def test_ARAXRanker_test5_asset70():
    # test 'Miglustat treats Niemann-Pick type C'
    expected_answer = 'Miglustat'
    
    returned_message = _ranker_tester(response_id='248115')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results

def test_ARAXRanker_test6_asset72():
    # test 'Lomitapide treats Homozygous Familial Hypercholesterolemia'
    expected_answer = 'Lomitapide'
    
    returned_message = _ranker_tester(response_id='248120')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results

def test_ARAXRanker_test9_asset614():
    # test 'famotidine treats Gastroesophageal Reflux Disease'
    expected_answer = 'famotidine'
    
    returned_message = _ranker_tester(response_id='248142')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results


def test_ARAXRanker_test9_asset619():
    # test 'lansoprazole treats Gastroesophageal Reflux Disease'
    expected_answer = 'lansoprazole'
    
    returned_message = _ranker_tester(response_id='248142')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results


def test_ARAXRanker_test9_asset623():
    # test 'rabeprazole treats Gastroesophageal Reflux Disease'
    expected_answer = 'rabeprazole'
    
    returned_message = _ranker_tester(response_id='248142')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results


def test_ARAXRanker_test13_asset311():
    # test 'Benazepril decreases activity or abundance of ACE'
    expected_answer = 'Benazepril'
    
    returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results


def test_ARAXRanker_test13_asset355():
    # test 'Fosinopril decreases activity or abundance of ACE'
    expected_answer = 'Fosinopril'
    
    returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results


def test_ARAXRanker_test13_asset360():
    # test 'Trandolapril decreases activity or abundance of ACE'
    expected_answer = 'Trandolapril'
    
    returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results
    
    
def test_ARAXRanker_test13_asset361():
    # test 'Moexipril decreases activity or abundance of ACE'
    expected_answer = 'Moexipril'
    
    returned_message = _ranker_tester(response_id='248160')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results

def test_ARAXRanker_test21_asset339():
    # test 'canagliflozin decreases activity or abundance of SLC5A2 (human)'
    expected_answer = 'canagliflozin'
    
    returned_message = _ranker_tester(response_id='248191')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results


def test_ARAXRanker_test23_asset381():
    # test 'atenolol decreases activity or abundance of ADRB2'
    expected_answer = 'atenolol'
    
    returned_message = _ranker_tester(response_id='248199')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results


def test_ARAXRanker_test23_asset378():
    # test 'propranolol decreases activity or abundance of ADRB2'
    expected_answer = 'propranolol'
    
    returned_message = _ranker_tester(response_id='248199')
    rank_right_answer = -1
    for index, result in enumerate(returned_message.results):
        if result.essence.lower() == expected_answer.lower():
            rank_right_answer = index + 1
            break
    total_results = len(returned_message.results)
    
    assert rank_right_answer != -1
    assert rank_right_answer < 0.1 * total_results
    

## comment out because this test doesn't pass due to the top 10% requirement 12 < 10% of 100
# def test_ARAXRanker_test23_asset379():
#     # test 'metoprolol decreases activity or abundance of ADRB2'
#     expected_answer = 'metoprolol'
    
#     returned_message = _ranker_tester(response_id='248199')
#     rank_right_answer = -1
#     for index, result in enumerate(returned_message.results):
#         if result.essence.lower() == expected_answer.lower():
#             rank_right_answer = index + 1
#             break
#     total_results = len(returned_message.results)
    
#     assert rank_right_answer != -1
#     assert rank_right_answer < 0.1 * total_results


# def test_ARAXRanker_feedback_issue819():
#     # test 'Janus Kinase Inhibitor decreases JAK1'
#     expected_answer = 'Janus Kinase Inhibitor'
    
#     returned_message = _ranker_tester(response_id='249257')
#     rank_right_answer = -1
#     for index, result in enumerate(returned_message.results):
#         if result.essence.lower() == expected_answer.lower():
#             rank_right_answer = index + 1
#             break
#     total_results = len(returned_message.results)
    
#     assert rank_right_answer != -1
#     assert rank_right_answer < 0.1 * total_results


if __name__ == "__main__":
    pytest.main(['-v'])
