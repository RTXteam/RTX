#!/bin/env python3
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery/")
from response import Response
from actions_parser import ActionsParser
from ARAX_messenger import ARAXMessenger
from ARAX_expander import ARAXExpander
from ARAX_resultify import ARAXResultify


# Utility functions

def run_query_and_conduct_standard_testing(actions_list, num_allowed_retries=2, do_standard_testing=True):
    response = Response()
    actions_parser = ActionsParser()

    # Parse the raw action_list into commands and parameters
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    actions = result.data['actions']

    messenger = ARAXMessenger()
    expander = ARAXExpander()
    resultifier = ARAXResultify()

    # Run each action
    for action in actions:
        if action['command'] == 'create_message':
            result = messenger.create_message()
            message = result.data['message']
            response.data = result.data
        elif action['command'] == 'add_qnode':
            result = messenger.add_qnode(message, action['parameters'])
        elif action['command'] == 'add_qedge':
            result = messenger.add_qedge(message, action['parameters'])
        elif action['command'] == 'expand':
            result = expander.apply(message, action['parameters'])
        elif action['command'] == 'resultify':
            result = resultifier.apply(message, action['parameters'])
        elif action['command'] == 'return':
            break
        else:
            response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
            print(response.show(level=Response.DEBUG))
            return None, None

        # Merge down this result and end if we're in an error state
        response.merge(result)
        if result.status != 'OK':
            # Try again if we ran into the intermittent neo4j connection issue (#649)
            if (result.error_code == 'ConnectionResetError' or result.error_code == 'OSError') and num_allowed_retries > 0:
                return run_query_and_conduct_standard_testing(actions_list, num_allowed_retries - 1)
            else:
                # print(message.knowledge_graph)
                print(response.show(level=Response.DEBUG))
                return None, None

    # print(response.show(level=Response.DEBUG))
    kg_in_dict_form = convert_list_kg_to_dict_kg(message.knowledge_graph)
    print_counts_by_qgid(kg_in_dict_form)
    if do_standard_testing:
        conduct_standard_testing(kg_in_dict_form, message.query_graph)
    return kg_in_dict_form


def convert_list_kg_to_dict_kg(knowledge_graph):
    dict_kg = {'nodes': dict(), 'edges': dict()}
    for node in knowledge_graph.nodes:
        if node.qnode_id not in dict_kg['nodes']:
            dict_kg['nodes'][node.qnode_id] = dict()
        dict_kg['nodes'][node.qnode_id][node.id] = node
    for edge in knowledge_graph.edges:
        if edge.qedge_id not in dict_kg['edges']:
            dict_kg['edges'][edge.qedge_id] = dict()
        dict_kg['edges'][edge.qedge_id][edge.id] = edge
    return dict_kg


def conduct_standard_testing(kg_in_dict_form, query_graph):
    check_for_orphans(kg_in_dict_form)
    check_all_qg_ids_fulfilled(kg_in_dict_form, query_graph)


def print_counts_by_qgid(kg_in_dict_form):
    if kg_in_dict_form['nodes'] or kg_in_dict_form['edges']:
        for qnode_id, corresponding_nodes in sorted(kg_in_dict_form['nodes'].items()):
            print(f"  {qnode_id}: {len(corresponding_nodes)}")
        for qedge_id, corresponding_edges in sorted(kg_in_dict_form['edges'].items()):
            print(f"  {qedge_id}: {len(corresponding_edges)}")
    else:
        print("  KG is empty")


def print_nodes(kg_in_dict_form):
    for qnode_id, nodes in kg_in_dict_form['nodes'].items():
        for node_key, node in nodes.items():
            print(f"{node.qnode_id}, {node.type}, {node.id}, {node.name}")


def print_edges(kg_in_dict_form):
    for qedge_id, edges in kg_in_dict_form['edges'].items():
        for edge_key, edge in edges.items():
            print(f"{edge.qedge_id}, {edge.id}, {edge.source_id}--{edge.type}->{edge.target_id}")


def print_node_counts_by_prefix(kg_in_dict_form):
    nodes_by_prefix = dict()
    for qnode_id, nodes in kg_in_dict_form['nodes'].items():
        for node_key, node in nodes.items():
            prefix = node.id.split(':')[0]
            if prefix in nodes_by_prefix.keys():
                nodes_by_prefix[prefix] += 1
            else:
                nodes_by_prefix[prefix] = 1
    print(nodes_by_prefix)


def check_for_orphans(kg_in_dict_form):
    node_ids = set()
    node_ids_used_by_edges = set()
    for qnode_id, nodes in kg_in_dict_form['nodes'].items():
        for node_key, node in nodes.items():
            node_ids.add(node_key)
    for qedge_id, edges in kg_in_dict_form['edges'].items():
        for edge_key, edge in edges.items():
            node_ids_used_by_edges.add(edge.source_id)
            node_ids_used_by_edges.add(edge.target_id)
    assert node_ids == node_ids_used_by_edges or len(node_ids_used_by_edges) == 0


def check_all_qg_ids_fulfilled(kg_in_dict_form, query_graph):
    for qnode in query_graph.nodes:
        assert kg_in_dict_form['nodes'].get(qnode.id)
    for qedge in query_graph.edges:
        assert kg_in_dict_form['edges'].get(qedge.id)


# Actual test cases

def test_kg1_parkinsons_demo_example():
    print("Testing KG1 parkinson's demo example")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    # Make sure only one node exists for n00 (the original curie)
    assert len(kg_in_dict_form['nodes']['n00']) == 1

    # Make sure all e00 edges map to Parkinson's curie for n00
    for edge_id, edge in kg_in_dict_form['edges']['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure all drugs returned are as expected
    for node_id, node in kg_in_dict_form['nodes']['n02'].items():
        assert "chemical_substance" in node.type

    # Make sure drugs include cilnidipine
    assert any(node.name.lower() == 'cilnidipine' for node in kg_in_dict_form['nodes']['n02'].values())

    # Make sure there are four proteins connecting to cilnidipine
    proteins_connected_to_cilnidipine = set()
    for edge_id, edge in kg_in_dict_form['edges']['e01'].items():
        if edge.source_id == "CHEMBL.COMPOUND:CHEMBL452076" or edge.target_id == "CHEMBL.COMPOUND:CHEMBL452076":
            non_cilnidipine_node = edge.source_id if edge.source_id != "CHEMBL.COMPOUND:CHEMBL452076" else edge.target_id
            proteins_connected_to_cilnidipine.add(non_cilnidipine_node)
    assert(len(proteins_connected_to_cilnidipine) >= 4)


def test_kg2_parkinsons_demo_example():
    print("Testing KG2 parkinson's demo example")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2, enforce_directionality=true, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    # Make sure only one node exists for n00 (the original curie)
    assert len(kg_in_dict_form['nodes']['n00']) == 1

    # Make sure all e00 edges map to Parkinson's curie for n00
    for edge_id, edge in kg_in_dict_form['edges']['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure all drugs returned are as expected
    for node_id, node in kg_in_dict_form['nodes']['n02'].items():
        assert "chemical_substance" in node.type

    # Make sure drugs include cilnidipine
    assert any(node.name.lower() == 'cilnidipine' for node in kg_in_dict_form['nodes']['n02'].values())

    # Make sure there are four proteins connecting to cilnidipine
    proteins_connected_to_cilnidipine = set()
    for edge_id, edge in kg_in_dict_form['edges']['e01'].items():
        if edge.source_id == "CHEMBL.COMPOUND:CHEMBL452076" or edge.target_id == "CHEMBL.COMPOUND:CHEMBL452076":
            non_cilnidipine_node = edge.source_id if edge.source_id != "CHEMBL.COMPOUND:CHEMBL452076" else edge.target_id
            proteins_connected_to_cilnidipine.add(non_cilnidipine_node)
    assert(len(proteins_connected_to_cilnidipine) >= 4)

    assert len(kg_in_dict_form['nodes']['n00']) == 1
    assert len(kg_in_dict_form['nodes']['n01']) == 18
    assert len(kg_in_dict_form['nodes']['n02']) == 1119
    assert len(kg_in_dict_form['edges']['e00']) == 18
    assert len(kg_in_dict_form['edges']['e01']) == 1871


def test_kg2_synonym_map_back_parkinsons_proteins():
    print("Testing kg2 synonym map back parkinsons proteins")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "expand(edge_id=e00, kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    # Make sure all edges have been remapped to original curie for n00
    for edge_key, edge in kg_in_dict_form['edges']['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure only one node exists for n00 (the original curie)
    assert len(kg_in_dict_form['nodes']['n00']) == 1

    # Take a look at the proteins returned, make sure they're all proteins
    for node_key, node in kg_in_dict_form['nodes']['n01'].items():
        assert "protein" in node.type


def test_kg2_synonym_map_back_parkinsons_full_example():
    print("Testing kg2 synonym map back parkinsons full example")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    # Make sure only one node exists for n00 (the original curie)
    assert len(kg_in_dict_form['nodes']['n00']) == 1

    # Make sure all e00 edges have been remapped to original curie for n00
    for edge_id, edge in kg_in_dict_form['edges']['e00'].items():
        assert edge.source_id == "DOID:14330" or edge.target_id == "DOID:14330"

    # Make sure all drugs returned are as expected
    for node_id, node in kg_in_dict_form['nodes']['n02'].items():
        assert "chemical_substance" in node.type


def test_kg2_synonym_add_all_parkinsons_full_example():
    print("Testing kg2 synonym add all parkinson's full example")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=molecularly_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    # Make sure all drugs returned are as expected
    for node_id, node in kg_in_dict_form['nodes']['n02'].items():
        assert "chemical_substance" in node.type


def test_demo_example_1_simple():
    print(f"Testing demo example 1 (Acetaminophen) without synonyms, using KG1")
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n0)",
        "add_qnode(type=protein, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n0']) >= 1
    assert len(kg_in_dict_form['nodes']['n1']) >= 32
    assert len(kg_in_dict_form['edges']['e0']) >= 64


def test_demo_example_2_simple():
    print(f"Testing demo example 2 (Parkinson's) without synonyms, using KG1")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n00']) >= 1
    assert len(kg_in_dict_form['nodes']['n01']) >= 18
    assert len(kg_in_dict_form['nodes']['n02']) >= 1119
    assert len(kg_in_dict_form['edges']['e00']) >= 18
    assert len(kg_in_dict_form['edges']['e01']) >= 1871


def test_demo_example_3_simple():
    print(f"Testing demo example 3 (hypopituitarism) without synonyms, using KG1")
    actions_list = [
        "create_message",
        "add_qnode(curie=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01], use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n00']) >= 1
    assert len(kg_in_dict_form['nodes']['n01']) >= 29
    assert len(kg_in_dict_form['nodes']['n02']) >= 240
    assert len(kg_in_dict_form['edges']['e00']) >= 29
    assert len(kg_in_dict_form['edges']['e01']) >= 1368


def test_demo_example_1_with_synonyms():
    print(f"Testing demo example 1 (Acetaminophen) WITH synonyms, using KG1")
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n0)",
        "add_qnode(type=protein, id=n1)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "expand(edge_id=e0)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n0']) >= 1
    assert len(kg_in_dict_form['nodes']['n1']) >= 32
    assert len(kg_in_dict_form['edges']['e0']) >= 64


def test_demo_example_2_with_synonyms():
    print(f"Testing demo example 2 (Parkinson's) WITH synonyms, using KG1")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n00']) >= 1
    assert len(kg_in_dict_form['nodes']['n01']) >= 18
    assert len(kg_in_dict_form['nodes']['n02']) >= 1119
    assert len(kg_in_dict_form['edges']['e00']) >= 18
    assert len(kg_in_dict_form['edges']['e01']) >= 1871


def test_demo_example_3_with_synonyms():
    print(f"Testing demo example 3 (hypopituitarism) WITH synonyms, using KG1")
    actions_list = [
        "create_message",
        "add_qnode(curie=DOID:9406, id=n00)",
        "add_qnode(type=chemical_substance, is_set=true, id=n01)",
        "add_qnode(type=protein, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01])",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n00']) >= 1
    assert len(kg_in_dict_form['nodes']['n01']) >= 29
    assert len(kg_in_dict_form['nodes']['n02']) >= 240
    assert len(kg_in_dict_form['edges']['e00']) >= 29
    assert len(kg_in_dict_form['edges']['e01']) >= 1368


def erics_first_kg1_synonym_test_without_synonyms():
    print(f"Testing Eric's first KG1 synonym test without synonyms")
    actions_list = [
        "create_message",
        "add_qnode(name=PHENYLKETONURIA, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def erics_first_kg1_synonym_test_with_synonyms():
    print(f"Testing Eric's first KG1 synonym test WITH synonyms")
    actions_list = [
        "create_message",
        "add_qnode(name=PHENYLKETONURIA, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def acetaminophen_example_enforcing_directionality():
    print(f"Testing acetaminophen example with enforced directionality")
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, use_synonyms=false, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n00']) == 1
    assert len(kg_in_dict_form['nodes']['n01']) == 32
    assert len(kg_in_dict_form['edges']['e00']) == 32

    # Make sure the source of every node is acetaminophen
    for node_id in kg_in_dict_form['nodes']['n00'].keys():
        assert node_id == "CHEMBL.COMPOUND:CHEMBL112"


def parkinsons_example_enforcing_directionality():
    print(f"Testing Parkinson's using KG1, enforcing directionality")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, enforce_directionality=true)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n00']) == 1
    assert len(kg_in_dict_form['nodes']['n01']) == 18
    assert len(kg_in_dict_form['nodes']['n02']) == 1119
    assert len(kg_in_dict_form['edges']['e00']) == 18
    assert len(kg_in_dict_form['edges']['e01']) == 1871


def ambitious_query_causing_multiple_qnode_ids_error():
    print(f"Testing ambitious query causing multiple qnode_ids error (#720)")
    actions_list = [
        "create_message",
        "add_qnode(curie=DOID:14330, id=n00)",
        "add_qnode(is_set=true, id=n01)",
        "add_qnode(type=disease, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00, e01])",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def test_kg1_property_format():
    print(f"Testing kg1 property format")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        "add_qnode(id=n01, type=protein, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    for qnode_id, nodes in kg_in_dict_form['nodes'].items():
        for node in nodes.values():
            assert type(node.name) is str
            assert type(node.id) is str
            assert ":" in node.id
            assert type(node.qnode_id) is str
            assert type(node.type) is list
            assert type(node.uri) is str

    for qedge_id, edges in kg_in_dict_form['edges'].items():
        for edge in edges.values():
            assert type(edge.id) is str
            assert type(edge.is_defined_by) is str
            assert type(edge.provided_by) is str
            assert type(edge.qedge_id) is str
            assert type(edge.type) is str
            if "chembl" in edge.provided_by.lower():
                assert edge.edge_attributes[0].name == "probability"


def simple_bte_acetaminophen_query():
    print(f"Testing simple BTE acetaminophen query")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "expand(edge_id=e00, kp=BTE)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def bte_query_using_list_of_curies():
    print(f"Testing BTE query using list of curies")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=[CHEMBL.COMPOUND:CHEMBL112, CHEMBL.COMPOUND:CHEMBL521])",
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n00']) > 1


def simple_bte_cdk2_query():
    print(f"Testing simple BTE CDK2 query")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=NCBIGene:1017)",
        "add_qnode(id=n01, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n01, target_id=n00)",
        "expand(edge_id=e00, kp=BTE)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def test_two_hop_bte_query():
    print(f"Testing two-hop BTE query")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=NCBIGene:1017)",
        "add_qnode(id=n01, type=disease, is_set=True)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "add_qedge(id=e01, source_id=n01, target_id=n02)",
        "expand(kp=BTE)",
        "return(message=true, store=false)",
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def test_simple_bidirectional_query():
    print(f"Testing simple bidirectional query (caused #727)")
    actions_list = [
        "create_message",
        "add_qnode(name=CHEMBL.COMPOUND:CHEMBL1276308, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def query_that_doesnt_return_original_curie():
    print(f"Testing query that doesn't return the original curie (only synonym curies - #731)")
    actions_list = [
        "create_message",
        "add_qnode(name=MONDO:0005737, id=n0, type=disease)",
        "add_qnode(type=protein, id=n1)",
        "add_qnode(type=disease, id=n2)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(edge_id=[e0,e1], kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)

    assert len(kg_in_dict_form['nodes']['n0']) == 1
    assert "MONDO:0005737" in kg_in_dict_form['nodes']['n0']

    for edge in kg_in_dict_form['edges']['e0'].values():
        assert edge.source_id == "MONDO:0005737" or edge.target_id == "MONDO:0005737"


def single_node_query_map_back():
    print("Testing a single node query (clopidogrel) using KG2, with map_back synonym handling")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_id=n00, kp=ARAX/KG2, synonym_handling=map_back)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n00']) == 1
    assert kg_in_dict_form['nodes']['n00'].get("CHEMBL.COMPOUND:CHEMBL1771")


def single_node_query_add_all():
    print("Testing a single node query (clopidogrel) using KG2, with add_all synonym handling")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1771)",
        "expand(node_id=n00, kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n00']) > 1
    assert "CHEMBL.COMPOUND:CHEMBL1771" in kg_in_dict_form['nodes']['n00']


def single_node_query_without_synonyms():
    print("Testing a single node query without using synonyms")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL1276308)",
        "expand(kp=ARAX/KG1, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n00']) == 1
    assert "CHEMBL.COMPOUND:CHEMBL1276308" in kg_in_dict_form['nodes']['n00']


def query_with_no_edge_or_node_ids():
    print("Testing query with no edge or node IDs specified")
    actions_list = [
        "create_message",
        "add_qnode(name=CHEMBL.COMPOUND:CHEMBL1276308, id=n00)",
        "add_qnode(type=protein, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand()",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert kg_in_dict_form['nodes']['n00'] and kg_in_dict_form['nodes']['n01'] and kg_in_dict_form['edges']['e00']


def query_that_produces_multiple_provided_bys():
    print("Testing query that produces node with multiple provided bys")
    actions_list = [
        "create_message",
        "add_qnode(name=MONDO:0005737, id=n0, type=disease)",
        "add_qnode(type=protein, id=n1)",
        "add_qnode(type=disease, id=n2)",
        "add_qedge(source_id=n0, target_id=n1, id=e0)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def babesia_query_producing_self_edges():
    print("Testing babesia query that produces self edges (causing #742)")
    actions_list = [
        "create_message",
        "add_qnode(name=babesia, id=n00)",
        "add_qnode(id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(edge_id=e00, kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def three_hop_query():
    print("Testing three-hop query")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:8454)",
        "add_qnode(id=n01, type=phenotypic_feature)",
        "add_qnode(id=n02, type=protein)",
        "add_qnode(id=n03, type=anatomical_entity)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "add_qedge(source_id=n02, target_id=n03, id=e02)",
        "expand()",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def branched_query():
    print("Testing branched query")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=DOID:14330)",
        "add_qnode(id=n01, type=protein)",
        "add_qnode(id=n02, type=chemical_substance)",
        "add_qedge(source_id=n00, target_id=n02, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand()",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)


def add_all_query_with_multiple_synonyms_in_results():
    print("Testing query with many synonyms, using add_all")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, name=warfarin)",
        "add_qnode(id=n01, type=disease)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n00']) > 1


def query_that_expands_same_edge_twice():
    print("Testing query that expands the same edge twice, using different KPs")
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521)",  # ibuprofen
        "add_qnode(id=n01, type=protein)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        "expand(kp=ARAX/KG1, continue_if_no_results=true)",
        "expand(kp=ARAX/KG2, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert any(edge for edge in kg_in_dict_form['edges']['e00'].values() if edge.is_defined_by == "ARAX/KG1")
    assert any(edge for edge in kg_in_dict_form['edges']['e00'].values() if edge.is_defined_by == "ARAX/KG2")


def angioedema_bte_query_causing_759():
    print("Testing angioedema BTE query causing #759")
    actions_list = [
        "create_message",
        # "add_qnode(name=Angioedema, id=n1)",  # Original query
        # "add_qnode(name=vasodilation, id=n2)",
        # "add_qedge(source_id=n1, target_id=n2, id=e1)",
        # "expand(edge_id=[e1], kp=BTE)",
        "add_qnode(name=vasodilation, id=n1)",  # Revised
        "add_qnode(type=disease, id=n2)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(edge_id=[e1], kp=BTE)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    # for node in kg_in_dict_form['nodes']['n2'].values():
    #     if node.id == "MESH:D000799" or "angioedema" in node.id.lower():
    #         print(node)


def query_using_continue_if_no_results():
    print("Testing query with no results using continue_if_no_results #771")
    actions_list = [
        "create_message",
        "add_qnode(curie=UniProtKB:P14136, id=n00)",
        "add_qnode(curie=UniProtKB:P35579, id=n01)",
        "add_qnode(type=biological_process, id=n02)",
        "add_qedge(source_id=n00, target_id=n02, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=[e00,e01], kp=ARAX/KG1, continue_if_no_results=true)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list, do_standard_testing=False)


def query_using_list_of_curies_map_back_handling():
    print("Testing query using list of curies with map_back synonym handling")
    actions_list = [
        "create_message",
        "add_qnode(curie=[CUI:C0024530, CUI:C0024535, CUI:C0024534, CUI:C0747820], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert 1 < len(kg_in_dict_form['nodes']['n00']) <= 4
    n00_node_ids = set(kg_in_dict_form['nodes']['n00'].keys())
    assert n00_node_ids.issubset({"CUI:C0024530", "CUI:C0024535", "CUI:C0024534", "CUI:C0747820"})


def query_using_list_of_curies_add_all_handling():
    print("Testing query using list of curies with add_all synonym handling")
    actions_list = [
        "create_message",
        "add_qnode(curie=[CUI:C0024530, CUI:C0024535, CUI:C0024534, CUI:C0747820], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2, synonym_handling=add_all)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n00']) > 4


def query_using_list_of_curies_without_synonyms():
    print("Testing query using list of curies without using any synonyms")
    actions_list = [
        "create_message",
        "add_qnode(curie=[CUI:C0024530, CUI:C0024535, CUI:C0024534, CUI:C0747820], id=n00)",
        "add_qnode(type=phenotypic_feature, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2, use_synonyms=false)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert 1 < len(kg_in_dict_form['nodes']['n00']) <= 4
    n00_node_ids = set(kg_in_dict_form['nodes']['n00'].keys())
    assert n00_node_ids.issubset({"CUI:C0024530", "CUI:C0024535", "CUI:C0024534", "CUI:C0747820"})


def query_with_curies_on_both_ends():
    print("Testing query with curies on both ends")
    actions_list = [
        "create_message",
        "add_qnode(name=diabetes, id=n00)",
        "add_qnode(name=ketoacidosis, id=n01)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n00']) == 1 and len(kg_in_dict_form['nodes']['n01']) == 1


def query_with_intermediate_curie_node():
    print("Testing query with intermediate curie node")
    actions_list = [
        "create_message",
        "add_qnode(type=protein, id=n00)",
        "add_qnode(name=atrial fibrillation, id=n01)",
        "add_qnode(type=chemical_substance, id=n02)",
        "add_qedge(source_id=n00, target_id=n01, id=e00)",
        "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(kp=ARAX/KG2)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list)
    assert len(kg_in_dict_form['nodes']['n01']) == 1


def continue_if_no_results_query_causing_774():
    print("Testing continue if no results query causing #774")
    actions_list = [
        "create_message",
        "add_qnode(name=acetaminophen, id=n1)",
        "add_qnode(name=scabies, id=n2)",
        "add_qedge(source_id=n1, target_id=n2, id=e1)",
        "expand(edge_id=e1, kp=ARAX/KG2, continue_if_no_results=True)",
        "return(message=true, store=false)"
    ]
    kg_in_dict_form = run_query_and_conduct_standard_testing(actions_list, do_standard_testing=False)
    assert not kg_in_dict_form['nodes'] and not kg_in_dict_form['edges']


def main():
    # Regular tests
    test_kg1_parkinsons_demo_example()
    test_kg2_parkinsons_demo_example()
    test_kg2_synonym_map_back_parkinsons_proteins()
    test_kg2_synonym_map_back_parkinsons_full_example()
    test_kg2_synonym_add_all_parkinsons_full_example()
    test_demo_example_1_simple()
    test_demo_example_2_simple()
    test_demo_example_3_simple()
    test_demo_example_1_with_synonyms()
    test_demo_example_2_with_synonyms()
    test_demo_example_3_with_synonyms()
    erics_first_kg1_synonym_test_without_synonyms()
    erics_first_kg1_synonym_test_with_synonyms()
    acetaminophen_example_enforcing_directionality()
    parkinsons_example_enforcing_directionality()
    test_kg1_property_format()
    simple_bte_acetaminophen_query()
    bte_query_using_list_of_curies()
    simple_bte_cdk2_query()
    test_simple_bidirectional_query()
    query_that_doesnt_return_original_curie()
    single_node_query_map_back()
    single_node_query_add_all()
    single_node_query_without_synonyms()
    query_with_no_edge_or_node_ids()
    query_that_produces_multiple_provided_bys()
    babesia_query_producing_self_edges()
    three_hop_query()
    branched_query()
    add_all_query_with_multiple_synonyms_in_results()
    query_that_expands_same_edge_twice()
    query_using_continue_if_no_results()
    query_with_curies_on_both_ends()
    query_using_list_of_curies_map_back_handling()
    query_using_list_of_curies_add_all_handling()
    query_using_list_of_curies_without_synonyms()
    query_with_intermediate_curie_node()
    continue_if_no_results_query_causing_774()

    # Non-standard tests/bug tests
    # ambitious_query_causing_multiple_qnode_ids_error()
    # test_two_hop_bte_query()
    # angioedema_bte_query_causing_759()


if __name__ == "__main__":
    main()
