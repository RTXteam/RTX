#!/usr/bin/env python3

# Intended to test our more complicated workflows

import sys
import os
import pytest
from collections import Counter
from typing import List, Union

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/openapi_server/models")
from openapi_server.models.message import Message


def _do_arax_query(query: dict) -> List[Union[ARAXResponse, Message]]:
    araxq = ARAXQuery()
    response = araxq.query(query)
    if response.status != 'OK':
        print(response.show(level=response.DEBUG))
    return [response, response.envelope.message]


def _virtual_tester(message: Message, edge_predicate: str, relation: str, attribute_name: str, attribute_type: str, num_different_values=2):
    """
    Tests overlay functions that add virtual edges
    message: returned from _do_arax_query
    edge_predicate: the name of the virtual edge (eg. biolink:has_jaccard_index_with)
    relation: the relation you picked for the virtual_edge_relation (eg. N1)
    attribute_name: the attribute name to test (eg. 'jaccard_index')
    attribute_type: the attribute type (eg. 'EDAM-DATA:1234')
    num_different_values: the number of distinct values you wish to see have been added as attributes
    """
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert edge_predicate in edge_predicates_in_kg
    edges_of_interest = [x for x in message.knowledge_graph.edges.values()
                         if any(attribute.original_attribute_name == "virtual_relation_label" and attribute.value == relation
                                for attribute in x.attributes or [])]
    values = set()
    assert len(edges_of_interest) > 0
    for edge in edges_of_interest:
        assert 'primary_knowledge_source' in [source.resource_role for source in edge.sources]
        matching_attributes = [attribute for attribute in edge.attributes if attribute.original_attribute_name == attribute_name]
        assert matching_attributes
        values.add(matching_attributes[0].value)
        assert matching_attributes[0].attribute_type_id == attribute_type
    # make sure two or more values were added
    assert len(values) >= num_different_values


def test_option_group_id():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:3312, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:indicated_for, option_group_key=a, id=e00)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:contraindicated_for, option_group_key=1, id=e01)",
            "expand(edge_key=[e00,e01], kp=infores:retriever)",
        ]}}
    [response, message] = _do_arax_query(query)
    for key, edge in message.query_graph.edges.items():
        if key == 'e01':
            assert edge.option_group_id == '1'
        elif key == 'e00':
            assert edge.option_group_id == 'a'

def test_exclude():
    query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:3312, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:treats, key=e00)",
            "add_qedge(subject=n00, object=n01, predicates=biolink:contraindicated_for, exclude=true, key=e01)",
            "expand(edge_key=[e00,e01], kp=infores:retriever)",
        ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    for key, edge in message.query_graph.edges.items():
        if key == 'e01':
            assert edge.exclude
        if key == 'e00':
            assert not edge.exclude

@pytest.mark.slow
def test_example_2():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:14221, key=n00)",
        "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
        "expand(edge_key=[e00,e01], kp=infores:retriever)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=jaccard_index, direction=below, threshold=.01, remove_connected_nodes=t, qnode_keys=[n02])",  # Retriever jaccard values for this disease top out around 0.02
        "filter_kg(action=remove_edges_by_discrete_attribute,edge_attribute=provided_by, value=Pharos)",
        # "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1, threshold=0)",
        "resultify(ignore_edge_direction=true)",
        "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
        "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) > 0  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert message.results[0].essence is not None
    # _virtual_tester(message, 'biolink:probably_treats', 'P1', 'probability_treats', 'EDAM-DATA:0951', 2)
    _virtual_tester(message, 'biolink:has_jaccard_index_with', 'J1', 'jaccard_index', 'EDAM-DATA:1772', 2)


@pytest.mark.slow
def test_example_3():
    query = {"operations": {"actions": [
        "add_qnode(name=MONDO:0005301, key=n00)", # CM: change "DOID:9406" to "MONDO:0005301" because DOID:9406 has no matched OMOP id.
        "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
        "add_qnode(categories=biolink:Protein, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=infores:retriever)",
        "filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",
        "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_keys=[n02])",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    #assert len(message.results) in [47, 48]  # :BUG: sometimes the workflow returns 47 results, sometimes 48 (!?)
    assert len(message.results) >= 60
    assert message.results[0].essence is not None
    _virtual_tester(message, 'biolink:occurs_together_in_literature_with', 'N1', 'normalized_google_distance', 'EDAM-DATA:2526', 2)

@pytest.mark.broken 
def test_FET_example_1():
    # This a FET 3-hop example: try to find the phenotypes of drugs connected to proteins connected to DOID:14330
    query = {"operations": {"actions": [
        "add_qnode(ids=MONDO:0005233, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:Gene, is_set=true, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever, prune_threshold=5)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1, rel_edge_key=e00)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_keys=[n01])",
        "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:interacts_with)",
        "expand(edge_key=e01, kp=infores:retriever, prune_threshold=5)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2, rel_edge_key=e01)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.005, remove_connected_nodes=t, qnode_keys=[n02])",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n03)",
        "add_qedge(subject=n02, object=n03, key=e02)",
        "expand(edge_key=e02, kp=infores:retriever, prune_threshold=5)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.predicate.find("fisher_exact_test") != -1]
    FET_edge_labels = set([attr.value for edge in FET_edges for attr in edge.attributes if attr.original_attribute_name == 'virtual_relation_label'])
    assert len(FET_edge_labels) == 2
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        FET_edge_attribute = [attr for attr in edge.attributes if attr.original_attribute_name == 'fisher_exact_test_p-value']
        assert 0 <= float(FET_edge_attribute[0].value) < 0.005
        assert FET_edge_attribute[0].attribute_type_id == 'EDAM-DATA:1669'

def test_FET_example_2():
    # This a FET 2-hop example: try to find the diseases that share the same protein with ibuprofen (CHEMBL.COMPOUND:CHEMBL521)
    query = {"operations": {"actions": [
        "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL1472, categories=biolink:ChemicalEntity)",
        "add_qnode(key=n01, categories=biolink:Protein)",
        "add_qedge(key=e00, subject=n00, object=n01)",
        "expand(edge_key=e00, kp=infores:retriever, prune_threshold=5)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_keys=[n01])",
        "add_qnode(categories=biolink:Disease, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=e01, kp=infores:retriever, prune_threshold=5)",
        "resultify()",
        "filter_results(action=limit_number_of_results, max_results=50)",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.predicate.find("fisher_exact_test") != -1]
    FET_edge_labels = set([attr.value for edge in FET_edges for attr in edge.attributes if attr.original_attribute_name == 'virtual_relation_label'])
    assert len(FET_edge_labels) == 1
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        FET_edge_attribute = [attr for attr in edge.attributes if attr.original_attribute_name == 'fisher_exact_test_p-value']
        assert 0 <= float(FET_edge_attribute[0].value) < 0.01
        assert FET_edge_attribute[0].attribute_type_id == 'EDAM-DATA:1669'

@pytest.mark.broken 
def test_FET_example_3():
    # This a FET 3-hop example: try to find the genes connected to diseases that share the same phenotypes of a given disease
    query = {"operations": {"actions": [
        "add_qnode(ids=MONDO:0001475, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever, prune_threshold=5)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1, rel_edge_key=e00)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n01])",
        "add_qnode(categories=biolink:Disease, key=n02)",
        "add_qedge(subject=n01,object=n02,key=e01)",
        "expand(edge_key=e01, kp=infores:retriever, prune_threshold=5)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2, rel_edge_key=e01)",
        "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_keys=[n02])",
        "add_qnode(categories=biolink:Gene, key=n03)",
        "add_qedge(subject=n02, object=n03, key=e02)",
        "expand(edge_key=e02, kp=infores:retriever, prune_threshold=5)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.predicate.find("fisher_exact_test") != -1]
    FET_edge_labels = set([attr.value for edge in FET_edges for attr in edge.attributes if attr.original_attribute_name == 'virtual_relation_label'])
    assert len(FET_edge_labels) == 2
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        FET_edge_attribute = [attr for attr in edge.attributes if attr.original_attribute_name == 'fisher_exact_test_p-value']
        assert 0 <= float(FET_edge_attribute[0].value) < 0.001
        assert FET_edge_attribute[0].attribute_type_id == 'EDAM-DATA:1669'

def test_FET_example_4():
    # This a FET 2-hop example collecting nodes and edges from Retriever: try to find the diseases that share the same protein with Parkinson disease（DOID:14330)
    query = {"operations": {"actions": [
        "add_qnode(ids=DOID:10718, key=n00, categories=biolink:Disease)",
        "add_qnode(categories=biolink:Protein, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=infores:retriever)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, virtual_relation_label=FET1, object_qnode_key=n01,rel_edge_id=e00)",
        "filter_kg(action=remove_edges_by_continuous_attribute,edge_attribute=fisher_exact_test_p-value,direction=above,threshold=0.001,remove_connected_nodes=t,qnode_keys=[n01])",
        "add_qnode(categories=biolink:Disease, key=n02)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=e01, kp=infores:retriever)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.n_results > 0
    edge_predicates_in_kg = Counter([x.predicate for x in message.knowledge_graph.edges.values()])
    assert 'biolink:has_fisher_exact_test_p_value_with' in edge_predicates_in_kg
    FET_edges = [x for x in message.knowledge_graph.edges.values() if x.predicate.find("fisher_exact_test") != -1]
    FET_edge_labels = set([attr.value for edge in FET_edges for attr in edge.attributes if attr.original_attribute_name == 'virtual_relation_label'])
    assert len(FET_edge_labels) == 1
    for edge in FET_edges:
        assert hasattr(edge, 'attributes')
        FET_edge_attribute = [attr for attr in edge.attributes if attr.original_attribute_name == 'fisher_exact_test_p-value']
        assert 0 <= float(FET_edge_attribute[0].value) < 0.001
        assert FET_edge_attribute[0].attribute_type_id == 'EDAM-DATA:1669'


def test_FET_ranking_1():
    query = {"operations": { "actions": [
            "create_message",
            "add_qnode(key=n00,ids=UniProtKB:P14136,categories=biolink:Protein)",
            "add_qnode(categories=biolink:BiologicalProcess, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00,kp=infores:retriever)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET)",
            "resultify()",
            "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    scores = [result.row_data[0] for result in message.results]
    assert min(scores) != max(scores)

@pytest.mark.slow
@pytest.mark.broken
def test_example_2_parkinsons():
    query = {"operations": { "actions": [
            "create_message",
            "add_qnode(name=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, predicates=biolink:physically_interacts_with)",
            "expand(edge_key=[e00,e01], kp=infores:retriever, prune_threshold=20)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",  # seems to work just fine
            "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=jaccard_index, direction=below, threshold=.008, remove_connected_nodes=t, qnode_keys=[n02])",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=false)",
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert len(message.results) == 15
    assert message.results[0].essence is not None
    _virtual_tester(response.envelope.message, 'biolink:has_jaccard_index_with', 'J1', 'jaccard_index', 'EDAM-DATA:1772', 2)


def test_FET_ranking_2():
    query = {"operations": {"actions": [
        "create_message",
        "add_qnode(key=n00,ids=[UniProtKB:P14136,UniProtKB:P35579],is_set=true,categories=biolink:Protein)",
        "add_qnode(categories=biolink:BiologicalProcess, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00,kp=infores:retriever)",
        "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET)",
        "resultify()",
        "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    fet_ranking_value = {}
    for result in message.results:
        for key, edge_bindings in result.analyses[0].edge_bindings.items():
            if key.startswith('FET'):
                for edge in edge_bindings:
                    for attribute in message.knowledge_graph.edges[edge.id].attributes:
                        if attribute.original_attribute_name == "fisher_exact_test_p-value":
                            if str(result.score) in fet_ranking_value:
                                fet_ranking_value[str(result.score)].append(float(attribute.value))
                            else:
                                fet_ranking_value[str(result.score)] = [float(attribute.value)]

    for fet_val, conf_list in fet_ranking_value.items():
        if len(conf_list) > 1:
            for diff in [abs(x - y) for i,x in enumerate(conf_list) for j,y in enumerate(conf_list) if i < j]:
                assert diff == 0


@pytest.mark.slow
def test_ranker_float_error_ex3():
    query={"message": {
            "query_graph": {
              "edges": {
                "e00": {
                  "object": "n01",
                  "subject": "n00"
                },
                "e01": {
                  "object": "n02",
                  "subject": "n01"
                }
              },
              "nodes": {
                "n00": {
                  "categories": [
                    "biolink:Disease"
                  ],
                  "ids": [
                    "DOID:14330"
                  ]
                },
                "n01": {
                  "categories": [
                    "biolink:NamedThing"
                  ]
                },
                "n02": {
                  "categories": [
                    "biolink:Disease"
                  ],
                  "ids": [
                    "DOID:8778"
                  ]
                }
              }
            }
          }
        }
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'


# Not working yet
# def test_example_3_hypopituitarism():
#     query = {"operations": { "actions": [
#             "create_message",
#             #"add_qnode(key=n00, curie=DOID:0050156)",  # idiopathic pulmonary fibrosis
#             "add_qnode(curie=DOID:9406, key=n00)",  # hypopituitarism, original demo example
#             "add_qnode(key=n01, categories=chemical_substance, is_set=true)",
#             "add_qnode(key=n02, categories=protein)",
#             "add_qedge(key=e00, subject=n00, object=n01)",
#             "add_qedge(key=e01, subject=n01, object=n02)",
#             "expand(edge_key=[e00,e01], kp=infores:retriever)",
#             "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
#             "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
#             "filter_kg(action=remove_edges_by_continuous_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=2, remove_connected_nodes=t, qnode_keys=[n01])",
#             "filter_kg(action=remove_orphaned_nodes, node_category=protein)",
#             "return(message=true, store=false)"
#     ]}}
#     [response, message] = _do_arax_query(query)
#     assert response.status == 'OK'
#     #assert len(message.results) == ?
#     assert message.results[0].essence is not None
#     _virtual_tester(message, 'biolink:has_observed_expected_ratio_with', 'C1', 'observed_expected_ratio', 'EDAM-DATA:0951', 2)
#     _virtual_tester(message, 'biolink:occurs_together_in_literature_with', 'N1', 'normalized_google_distance', 'EDAM-DATA:2526', 2)

@pytest.mark.slow
def test_example_3_issue_679():
    query = {"operations": { "actions": [
            "create_message",
            "add_qnode(name=DOID:9406, key=n00)",
            "add_qnode(categories=[biolink:ChemicalEntity], is_set=true, key=n01)",
            "add_qnode(categories=[biolink:Protein], key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand()",
            "filter_kg(action=remove_orphaned_nodes,node_category=biolink:Protein)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
            "filter_kg(action=remove_edges_by_continuous_attribute,edge_attribute=ngd,direction=above,threshold=0.85,remove_connected_nodes=true,qnode_keys=n02)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=false)"
    ]}}
    [response, message] = _do_arax_query(query)
    assert response.status == 'OK'
    assert message.results[0].essence is not None


if __name__ == "__main__":
    pytest.main(['-v'])
