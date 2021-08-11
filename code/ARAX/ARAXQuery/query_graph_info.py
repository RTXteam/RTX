#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer")
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph


class QueryGraphInfo:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None

        self.n_nodes = None
        self.n_edges = None
        self.is_bifurcated_graph = False
        self.start_node = None
        self.node_info = None
        self.edge_info = None
        self.node_order = None
        self.edge_order = None
        self.node_category_map = None
        self.edge_predicate_map = None

        self.query_graph_templates = None


    #### Top level decision maker for applying filters
    def assess(self, message):

        #### Define a default response
        response = ARAXResponse()
        self.response = response
        self.message = message
        response.debug(f"Assessing the QueryGraph for basic information")

        #### Get shorter handles
        query_graph = message.query_graph
        nodes = {}
        if query_graph.nodes is not None:
            nodes = query_graph.nodes
        edges = {}
        if query_graph.edges is not None:
            edges = query_graph.edges

        #### Store number of nodes and edges
        self.n_nodes = len(nodes)
        self.n_edges = len(edges)
        response.debug(f"Found {self.n_nodes} nodes and {self.n_edges} edges")

        #### Handle impossible cases
        if self.n_nodes == 0:
            response.error("QueryGraph has 0 nodes. At least 1 node is required", error_code="QueryGraphZeroNodes")
            return response
        if self.n_nodes == 1 and self.n_edges > 0:
            response.error("QueryGraph may not have edges if there is only one node", error_code="QueryGraphTooManyEdges")
            return response


        #### Loop through nodes computing some stats
        have_at_least_one_id = False
        node_info = {}
        self.node_category_map = {}
        for key,qnode in nodes.items():

            if key is None:
                response.error("QueryGraph has a node with null key. This is not permitted", error_code="QueryGraphNodeWithNullKey")
                return response

            node_info[key] = { 'key': key, 'node_object': qnode, 'has_ids': False, 'categories': qnode.categories, 'has_categories': False, 'is_set': False, 'n_edges': 0, 'n_links': 0, 'is_connected': False, 'edges': [], 'edge_dict': {} }
            if qnode.ids is not None:
                node_info[key]['has_ids'] = True
                have_at_least_one_id = True

                #### If the user did not specify a category, but there is a curie, try to figure out the category
                if node_info[key]['categories'] is None:
                    synonymizer = NodeSynonymizer()
                    curie = qnode.ids
                    curies_list = qnode.ids
                    if isinstance(qnode.ids,list):
                        curie = qnode.ids[0]
                    else:
                        curies_list = [ qnode.ids ]

                    canonical_curies = synonymizer.get_canonical_curies(curies=curies_list, return_all_categories=True)
                    response.debug(f"canonical_curies={canonical_curies}, curie={curie}")
                    if curie in canonical_curies and canonical_curies[curie] is not None and 'preferred_type' in canonical_curies[curie]:
                        node_info[key]['has_categories'] = True
                        node_info[key]['categories'] = canonical_curies[curie]['preferred_type']

            if qnode.categories is not None:
                node_info[key]['has_categories'] = True

            #if qnode.is_set is not None: node_info[key]['is_set'] = True

            #### Store lookup of categories
            warning_counter = 0
            if qnode.categories is None or ( isinstance(qnode.categories,list) and len(qnode.categories) == 0 ):
                if warning_counter == 0:
                    #response.debug("QueryGraph has nodes with no categories. This may cause problems with results inference later")
                    pass
                warning_counter += 1
                self.node_category_map['unknown'] = key
            else:
                category = qnode.categories
                if isinstance(qnode.categories,list):
                    category = qnode.categories[0]                # FIXME this is a hack prior to proper list handling
                self.node_category_map[category] = key


        #### If we don't even have one id, then we don't support this
        if not have_at_least_one_id:
            response.error("QueryGraph has no nodes with ids. At least one node must have a specified 'ids'", error_code="QueryGraphNoIds")
            return response


        #### Ignore special informationational edges for now.
        virtual_edge_predicates = {
            'biolink:has_normalized_google_distance_with': 1,
            'biolink:has_fisher_exact_test_p-value_with': 1,
            'biolink:has_jaccard_index_with': 1,
            'biolink:probably_treats': 1,
            'biolink:has_paired_concept_frequency_with': 1,
            'biolink:has_observed_expected_ratio_with': 1,
            'biolink:has_chi_square_with': 1
            }


        #### Loop through edges computing some stats
        edge_info = {}
        self.edge_predicate_map = {}
        unique_links = {}

        for key,qedge in edges.items():

            predicate = qedge.predicates
            if isinstance(predicate,list):
                if len(predicate) == 0:
                    predicate = None
                else:
                    predicate = predicate[0]                       # FIXME Hack before dealing with predicates as lists!

            if predicate is not None and predicate in virtual_edge_predicates:
                continue

            edge_info[key] = { 'key': key, 'has_predicates': False, 'subject': qedge.subject, 'object': qedge.object, 'predicates': None, 'exclude': False }

            if qedge.exclude is not None:
                edge_info[key]['exclude'] = qedge.exclude

            if predicate is not None:
                edge_info[key]['has_predicates'] = True
                edge_info[key]['predicates'] = predicate

            if key is None:
                response.error("QueryGraph has a edge with null key. This is not permitted", error_code="QueryGraphEdgeWithNoKey")
                return response

            #### Create a unique node link string
            link_string = ','.join(sorted([qedge.subject,qedge.object]))
            if link_string not in unique_links:
                if qedge.subject not in node_info:
                    response.error(f"QEdge subject={qedge.subject} is not found among the nodes", error_code="QEdgeInvalidSubject")
                    return response
                node_info[qedge.subject]['n_links'] += 1
                if qedge.object not in node_info:
                    response.error(f"QEdge object={qedge.object} is not found among the nodes", error_code="QEdgeInvalidObject")
                    return response
                node_info[qedge.object]['n_links'] += 1
                unique_links[link_string] = 1
                #print(link_string)

            node_info[qedge.subject]['n_edges'] += 1
            node_info[qedge.object]['n_edges'] += 1
            node_info[qedge.subject]['is_connected'] = True
            node_info[qedge.object]['is_connected'] = True
            #node_info[qedge.subject]['edges'].append(edge_info[key])
            #node_info[qedge.object]['edges'].append(edge_info[key])
            node_info[qedge.subject]['edges'].append(edge_info[key])
            node_info[qedge.object]['edges'].append(edge_info[key])
            node_info[qedge.subject]['edge_dict'][key] = edge_info[key]
            node_info[qedge.object]['edge_dict'][key] = edge_info[key]

            #### Store lookup of predicates
            warning_counter = 0
            edge_predicate = 'any'
            if predicate is None:
                if warning_counter == 0:
                    response.debug("QueryGraph has edges with no predicate. This may cause problems with results inference later")
                warning_counter += 1
            else:
                edge_predicate = predicate

            #### It's not clear yet whether we need to store the whole sentence or just the predicate
            #predicate_encoding = f"{node_info[qedge.subject]['predicate']}---{edge_predicate}---{node_info[qedge.object]['predicate']}"
            predicate_encoding = edge_predicate
            self.edge_predicate_map[predicate_encoding] = key


        #### Loop through the nodes again, trying to identify the start_node and the end_node
        singletons = []
        for node_id,node_data in node_info.items():
            if node_data['n_links'] < 2:
                singletons.append(node_data)
            elif node_data['n_links'] > 2:
                self.is_bifurcated_graph = True
                response.warning("QueryGraph appears to have a fork in it. This might cause trouble")

        #### If this doesn't produce any singletons, then try curie based selection
        if len(singletons) == 0:
            for node_id,node_data in node_info.items():
                if node_data['has_ids']:
                    singletons.append(node_data)

        #### If this doesn't produce any singletons, then we don't know how to continue
        if len(singletons) == 0:
            response.error("Unable to understand the query graph", error_code="QueryGraphCircular")
            return response

        #### Try to identify the start_node and the end_node
        start_node = singletons[0]
        if len(nodes) == 1:
            # Just a single node, fine
            pass
        elif len(singletons) < 2:
            response.warning("QueryGraph appears to be circular or has a strange geometry. This might cause trouble")
        elif len(singletons) > 2:
            response.warning("QueryGraph appears to have a fork in it. This might cause trouble")
        else:
            if singletons[0]['has_ids'] is True and singletons[1]['has_ids'] is False:
                start_node = singletons[0]
            elif singletons[0]['has_ids'] is False and singletons[1]['has_ids'] is True:
                start_node = singletons[1]
            else:
                start_node = singletons[0]
        #### Hmm, that's not very robust against odd graphs. This needs work. FIXME

        #### Store results into the object
        self.node_info = node_info
        self.edge_info = edge_info
        self.start_node = start_node


        #### Set up state for computing the node order
        current_node = start_node
        node_order = [ start_node ]
        edge_order = [ ]
        edges = current_node['edges']
        debug = False
        loop_counter = 0

        #### Starting with the start node, loop until we run out of nodes to create node_order
        while 1:

            if debug:
                tmp = { 'astate': '1', 'current_node': current_node, 'node_order': node_order, 'edge_order': edge_order, 'edges': edges }
                print('==================================================================================')
                print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))
                #tmp = input()

            #### Ensure that we don't get stuck in an infinite loop
            loop_counter += 1
            if loop_counter > 20:
                response.error(f"Reached loop max: {loop_counter}", error_code="InteralError_F260")
                return response

            #### If we arrive at a node that has no more edges going out, then we're done
            if len(edges) == 0:
                break

            #### If there are multiple edges here, then we just take the first one. FIXME ignore the rest
            edge_order.append(edges[0])
            previous_node = current_node
            if edges[0]['subject'] == current_node['key']:
                current_node = node_info[edges[0]['object']]
            elif edges[0]['object'] == current_node['key']:
                current_node = node_info[edges[0]['subject']]
            else:
                response.error("Help, edge error A584. Don't know what to do", error_code="InteralErrorA584")
                return response
            node_order.append(current_node)

            #tmp = { 'astate': '2', 'current_node': current_node, 'node_order': node_order, 'edge_order': edge_order, 'edges': edges }
            #print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))
            #print('==================================================================================')
            #tmp = input()

            edges = current_node['edges']
            new_edges = []
            for edge in edges:
                key = edge['key']
                if key not in previous_node['edge_dict']:
                    new_edges.append(edge)
            edges = new_edges
            if len(edges) == 0:
                break
            #tmp = { 'astate': '3', 'current_node': current_node, 'node_order': node_order, 'edge_order': edge_order, 'edges': edges }
            #print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))
            #print('==================================================================================')
            #tmp = input()


        self.node_order = node_order
        self.edge_order = edge_order


        #### Loop over the ordered list of nodes,
        #### creating a text rendering of the QueryGraph geometry for matching against a template
        self.query_graph_templates = { 'simple': '', 'detailed': { 'n_nodes': len(node_order), 'components': [] } }
        node_index = 0
        edge_index = 0

        for node in node_order:
            component_id = f"n{node_index:02}"
            content = ''
            component = { 'component_type': 'node', 'component_id': component_id, 'has_ids': node['has_ids'], 'has_categories': node['has_categories'], 'categories_value': None }
            self.query_graph_templates['detailed']['components'].append(component)
            if node['has_ids']:
                content = 'ids'
            elif node['has_categories'] and node['node_object'].categories is not None:
                category = node['node_object'].categories
                if isinstance(category,list):
                    category = category[0]                                      # FIXME: Can we be smarter than just taking the first?
                content = f"categories={category}"
                component['categories_value'] = node['node_object'].categories
            elif node['has_categories']:
                content = 'categories'
            template_part = f"{component_id}({content})"
            self.query_graph_templates['simple'] += template_part

            # Since queries with intermediate nodes that are not is_set=true tend to blow up,
            # we thought it would be a good idea to set them to true, but then around 2021-07
            # this seemed to hurt more than it helps, so disable it for now and see how that goes.
            # Intermediate nodes that have ids (curies) are an exception to this treatment
            if node_index > 0 and node_index < (self.n_nodes - 1 ) and node['has_ids'] == False:
                if 'is_set' not in node or node['is_set'] is None:
                    #node['node_object'].is_set = True
                    #response.warning(f"Setting unspecified is_set to true for {node['key']} because this will probably lead to a happier result")
                    response.info(f"Property is_set is not true for {node['key']} although maybe it should be to keep the query from blowing up. Consider setting is_set to true here.")
                elif node['is_set'] is True:
                    response.debug(f"Value for is_set is already true for {node['key']} so that's good")
                elif node['is_set'] is False:
                    #node['node_object'].is_set = True
                    #response.info(f"Value for is_set is false for intermediate node {node['key']}. Setting to true because this will probably lead to a happier result")
                    response.info(f"Property is_set is not true for {node['key']} although maybe it should be to keep the query from blowing up. Consider setting is_set to true here.")

            node_index += 1
            if node_index < self.n_nodes:
                #print(json.dumps(ast.literal_eval(repr(node)),sort_keys=True,indent=2))

                #### Extract the has_predicate and predicate_value from the edges of the node
                #### This could fail if there are two edges coming out of the node FIXME
                has_predicates = False
                predicates_value = None
                if 'edges' in node:
                    for related_edge in node['edges']:
                        if related_edge['subject'] == node['key']:
                            has_predicates = related_edge['has_predicates']
                            if has_predicates is True and 'predicates' in related_edge:
                                predicates_value = related_edge['predicates']

                component_id = f"e{edge_index:02}"
                template_part = f"-{component_id}()-"
                self.query_graph_templates['simple'] += template_part
                component = { 'component_type': 'edge', 'component_id': component_id, 'has_ids': False, 'has_predicates': has_predicates, 'predicates_value': predicates_value }
                self.query_graph_templates['detailed']['components'].append(component)
                edge_index += 1

        response.debug(f"The QueryGraph reference template is: {self.query_graph_templates['simple']}")

        #tmp = { 'node_info': node_info, 'edge_info': edge_info, 'start_node': start_node, 'n_nodes': self.n_nodes, 'n_edges': self.n_edges,
        #    'is_bifurcated_graph': self.is_bifurcated_graph, 'node_order': node_order, 'edge_order': edge_order }
        #print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))
        #sys.exit(0)

        #### Return the response
        return response


##########################################################################################
def test_example1():

    test_query_graphs = [
        { "description": "Two nodes, one edge linking them, 1 CURIE",
          "nodes": {
            "n00": { "ids": [ "MONDO:0001627" ] },
            "n01": { "categories": [ "biolink:ChemicalEntity" ] } },
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": [ "biolink:physically_interacts_with" ] } } },

        { "description": "Two nodes, two edges linking them, 1 CURIE, one of which is excluded",
          "nodes": {
            "n00": { "ids": [ "MONDO:0001627" ] },
            "n01": { "categories": [ "biolink:ChemicalEntity" ] } },
          "edges": {
            "e00": { "subject": "n00", "object": "n01" },
            "e01": { "subject": "n00", "object":"n01", "predicates": [ "biolink:contraindicated_for" ], "exclude": True } } },

        { "description": "Two nodes, one edge linking them, both nodes are CURIEs",
          "nodes": {
            "n00": { "ids": [ "MONDO:0001627" ] },
            "n01": { "ids": [ "CHEMBL.COMPOUND:CHEMBL112" ] } },
          "edges": {
            "e00": { "subject": "n00", "object": "n01" } } },

        { "description": "Three nodes, 2 edges, 1 CURIE, simple linear chain",
          "nodes": {
            "n00": { "ids": [ "MONDO:0001627" ] },
            "n01": { "categories": [ "biolink:ChemicalEntity" ] },
            "n02": { "categories": [ "biolink:Protein" ] } },
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": [ "biolink:physically_interacts_with" ] },
            "e01": { "subject": "n01", "object": "n02" } } },

        { "description": "Three nodes, 2 edges, but the CURIE is in the middle. What does that even mean?",
          "nodes": {
            "n00": { "categories": [ "biolink:ChemicalEntity" ] },
            "n01": { "ids": [ "MONDO:0001627" ] },
            "n02": { "categories": [ "biolink:Protein" ] } },
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": [ "biolink:physically_interacts_with" ] },
            "e01": { "subject": "n01", "object": "n02" } } },

        { "description": "Four nodes, 3 edges, 1 CURIE, simple linear chain",
          "nodes": {
            "n00": { "ids": [ "MONDO:0001627" ] },
            "n01": { "categories": [ "biolink:ChemicalEntity" ] },
            "n02": { "categories": [ "biolink:Protein" ] },
            "n03": { "categories": [ "biolink:Disease" ] } },
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": [ "biolink:physically_interacts_with" ] },
            "e01": { "subject": "n01", "object": "n02" },
            "e02": { "subject": "n02", "object": "n03" } } },

        { "description": "Two nodes, one edge linking them, 0 CURIEs",
          "nodes": {
            "n00": { "categories": [ "biolink:Drug" ] },
            "n01": { "categories": [ "biolink:ChemicalEntity" ] } },
          "edges": {
            "e00": { "subject": "n00", "object": "n01", "predicates": [ "biolink:physically_interacts_with" ] } } },

        { "description": "One node only",
          "nodes": {
            "n00": { "ids": [ "MONDO:0001627" ] } },
          "edges": {} },

        ]

    from ARAX_messenger import ARAXMessenger

    for test_query_graph in test_query_graphs:
        response = ARAXResponse()
        messenger = ARAXMessenger()
        messenger.create_envelope(response)

        print('==================================================================')
        description = test_query_graph['description']
        del test_query_graph['description']
        print(f"Query Graph '{description}'")

        response.envelope.message.query_graph = QueryGraph().from_dict(test_query_graph)

        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(response.envelope.message)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=ARAXResponse.DEBUG))
            return response

        query_graph_info_dict = {
            'n_nodes': query_graph_info.n_nodes,
            'n_edges': query_graph_info.n_edges,
            'is_bifurcated_graph': query_graph_info.is_bifurcated_graph,
            'start_node': query_graph_info.start_node['key'],
            'simple_query_graph_template': query_graph_info.query_graph_templates['simple'],
            #'start_node': query_graph_info.start_node,
            #'node_info': query_graph_info.node_info,
            #'edge_info': query_graph_info.edge_info,
            #'node_order': query_graph_info.node_order,
            #'edge_order': query_graph_info.edge_order,
            #'node_category_map': query_graph_info.node_category_map,
            #'edge_predicate_map': query_graph_info.edge_predicate_map,
        }
        print(json.dumps(ast.literal_eval(repr(query_graph_info_dict)),sort_keys=True,indent=2))



##########################################################################################
def main():

    test_example1()
    return

    #### Create a response object
    response = ARAXResponse()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
 
    #### Set a simple list of actions
    actions_list = [
        "filter(start_node=1, maximum_results=10, minimum_confidence=0.5)",
        "return(message=true,store=false)"
    ]

    #### Parse the action_list and print the result
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response
    actions = result.data['actions']

    #### Read message #2 from the database. This should be the acetaminophen proteins query result message
    sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()
    message_dict = araxdb.getMessage(2)

    #### The stored message comes back as a dict. Transform it to objects
    from ARAX_messenger import ARAXMessenger
    message = ARAXMessenger().from_dict(message_dict)
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))

    #### Create a filter object and use it to apply action[0] from the list
    query_graph_info = QueryGraphInfo()
    result = query_graph_info.assess(message)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response
    
    query_graph_info_dict = {
        'n_nodes': query_graph_info.n_nodes,
        'n_edges': query_graph_info.n_edges,
        'is_bifurcated_graph': query_graph_info.is_bifurcated_graph,
        'start_node': query_graph_info.start_node,
        'node_info': query_graph_info.node_info,
        'edge_info': query_graph_info.edge_info,
        'node_order': query_graph_info.node_order,
        'edge_order': query_graph_info.edge_order,
        'node_category_map': query_graph_info.node_category_map,
        'edge_predicate_map': query_graph_info.edge_predicate_map,
    }
    print(json.dumps(ast.literal_eval(repr(query_graph_info_dict)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
