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
        nodes = query_graph.nodes
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
        #if self.n_nodes == 2 and self.n_edges > 1:
        #    response.error("QueryGraph may not have more than 1 edge if there are only 2 nodes", error_code="QueryGraphTooManyEdges")
        #    return response

        #### Loop through nodes computing some stats
        node_info = {}
        self.node_category_map = {}
        for key,qnode in nodes.items():
            node_info[key] = { 'key': key, 'node_object': qnode, 'has_id': False, 'category': qnode.category, 'has_category': False, 'is_set': False, 'n_edges': 0, 'n_links': 0, 'is_connected': False, 'edges': [], 'edge_dict': {} }
            if qnode.id is not None:
                node_info[key]['has_id'] = True

                #### If the user did not specify a category, but there is a curie, try to figure out the category
                if node_info[key]['category'] is None:
                    synonymizer = NodeSynonymizer()
                    curie = qnode.id
                    curies_list = qnode.id
                    if isinstance(qnode.id,list):
                        curie = qnode.id[0]
                    else:
                        curies_list = [ qnode.id ]

                    canonical_curies = synonymizer.get_canonical_curies(curies=curies_list, return_all_categories=True)
                    if curie in canonical_curies and 'preferred_type' in canonical_curies[curie]:
                        node_info[key]['has_category'] = True
                        node_info[key]['category'] = canonical_curies[curie]['preferred_type']

            if qnode.category is not None:
                node_info[key]['has_category'] = True

            #if qnode.is_set is not None: node_info[key]['is_set'] = True
            if key is None:
                response.error("QueryGraph has a node with null key. This is not permitted", error_code="QueryGraphNodeWithNoId")
                return response

            #### Remap the node categorys from unsupported to supported
            if qnode.category is not None:
                qnode.category = self.remap_node_category(qnode.category)

            #### Store lookup of categorys
            warning_counter = 0
            if qnode.category is None or ( isinstance(qnode.category,list) and len(qnode.category) == 0 ):
                if warning_counter == 0:
                    #response.debug("QueryGraph has nodes with no category. This may cause problems with results inference later")
                    pass
                warning_counter += 1
                self.node_category_map['unknown'] = key
            else:
                category = qnode.category
                if isinstance(qnode.category,list):
                    category = qnode.category[0]                # FIXME this is a hack prior to proper list handling
                self.node_category_map[category] = key

        #### Loop through edges computing some stats
        edge_info = {}
        self.edge_predicate_map = {}
        unique_links = {}

        #### Ignore special informationational edges for now.
        virtual_edge_predicates = {'has_normalized_google_distance_with': 1, 'has_fisher_exact_test_p-value_with': 1,
                                'has_jaccard_index_with': 1, 'probably_treats': 1,
                                'has_paired_concept_frequency_with': 1,
                                'has_observed_expected_ratio_with': 1, 'has_chi_square_with': 1}

        for key,qedge in edges.items():

            predicate = qedge.predicate
            if isinstance(predicate,list):
                if len(predicate) == 0:
                    predicate = None
                else:
                    predicate = predicate[0]                       # FIXME Hack before dealing with predicates as lists!

            if predicate is not None and predicate in virtual_edge_predicates:
                continue

            edge_info[key] = { 'key': key, 'has_predicate': False, 'subject': qedge.subject, 'object': qedge.object, 'predicate': None }
            if predicate is not None:
                edge_info[key]['has_predicate'] = True
                edge_info[key]['predicate'] = predicate

            if key is None:
                response.error("QueryGraph has a edge with null key. This is not permitted", error_code="QueryGraphEdgeWithNoKey")
                return response

            #### Create a unique node link string
            link_string = ','.join(sorted([qedge.subject,qedge.object]))
            if link_string not in unique_links:
                node_info[qedge.subject]['n_links'] += 1
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
                if node_data['has_id']:
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
            if singletons[0]['has_id'] is True and singletons[1]['has_id'] is False:
                start_node = singletons[0]
            elif singletons[0]['has_id'] is False and singletons[1]['has_id'] is True:
                start_node = singletons[1]
            else:
                start_node = singletons[0]
        #### Hmm, that's not very robust against odd graphs. This needs work. FIXME

        self.node_info = node_info
        self.edge_info = edge_info
        self.start_node = start_node


        current_node = start_node
        node_order = [ start_node ]
        edge_order = [ ]
        edges = current_node['edges']
        debug = False

        while 1:
            if debug:
                tmp = { 'astate': '1', 'current_node': current_node, 'node_order': node_order, 'edge_order': edge_order, 'edges': edges }
                print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))
                print('==================================================================================')
                tmp = input()

            if len(edges) == 0:
                break
            #if len(edges) > 1:
            if current_node['n_links'] > 1:
                response.error(f"Help, two edges at A583. Don't know what to do: {current_node['n_links']}", error_code="InteralErrorA583")
                return response
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

        # Create a text rendering of the QueryGraph geometry for matching against a template
        self.query_graph_templates = { 'simple': '', 'detailed': { 'n_nodes': len(node_order), 'components': [] } }
        node_index = 0
        edge_index = 0
        #print(json.dumps(ast.literal_eval(repr(node_order)),sort_keys=True,indent=2))
        for node in node_order:
            component_id = f"n{node_index:02}"
            content = ''
            component = { 'component_type': 'node', 'component_id': component_id, 'has_id': node['has_id'], 'has_category': node['has_category'], 'category_value': None }
            self.query_graph_templates['detailed']['components'].append(component)
            if node['has_id']:
                content = 'id'
            elif node['has_category'] and node['node_object'].category is not None:
                content = f"category={node['node_object'].category}"
                component['category_value'] = node['node_object'].category
            elif node['has_category']:
                content = 'category'
            template_part = f"{component_id}({content})"
            self.query_graph_templates['simple'] += template_part

            # Since queries with intermediate nodes that are not is_set=true tend to blow up, for now, make them is_set=true unless explicitly set to false
            if node_index > 0 and node_index < (self.n_nodes - 1 ):
                if 'is_set' not in node or node['is_set'] is None:
                    node['node_object'].is_set = True
                    response.warning(f"Setting unspecified is_set to true for {node['key']} because this will probably lead to a happier result")
                elif node['is_set'] is True:
                    response.debug(f"Value for is_set is already true for {node['key']} so that's good")
                elif node['is_set'] is False:
                    #response.info(f"Value for is_set is set to false for intermediate node {node['key']}. This could lead to weird results. Consider setting it to true")
                    response.info(f"Value for is_set is false for intermediate node {node['key']}. Setting to true because this will probably lead to a happier result")
                    node['node_object'].is_set = True
                #else:
                #    response.error(f"Unrecognized value is_set='{node['is_set']}' for {node['key']}. This should be true or false")

            node_index += 1
            if node_index < self.n_nodes:
                #print(json.dumps(ast.literal_eval(repr(node)),sort_keys=True,indent=2))

                #### Extract the has_predicate and predicate_value from the edges of the node
                #### This could fail if there are two edges coming out of the node FIXME
                has_predicate = False
                predicate_value = None
                if 'edges' in node:
                    for related_edge in node['edges']:
                        if related_edge['subject'] == node['key']:
                            has_predicate = related_edge['has_predicate']
                            if has_predicate is True and 'predicate' in related_edge:
                                predicate_value = related_edge['predicate']

                component_id = f"e{edge_index:02}"
                template_part = f"-{component_id}()-"
                self.query_graph_templates['simple'] += template_part
                component = { 'component_type': 'edge', 'component_id': component_id, 'has_id': False, 'has_predicate': has_predicate, 'predicate_value': predicate_value }
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
    #### Remap node categorys from the new TRAPI 1.0 style to the older TRAPI 0.9.x style
    #### No longer needed. FIXME
    def remap_node_category(self, node_category):
        #match = re.match(r'biolink:(.+)', node_category)
        #if match:
        #    node_category = match.group(1)
        #    node_category = re.sub(r'(?<!^)(?=[A-Z])', '_', node_category).lower()
        return node_category


##########################################################################################
def test_example1():
    query_graph = {
          "edges":{
            "e00":{
            "subject":"n00",
            "object":"n01"
            },
            "e01":{
            "subject":"n00",
            "object":"n01",
            "predicate":"biolink:contraindicated_for",
            "exclude": True
            }
        },
          "nodes":{
            "n00":{
            "id":"MONDO:0001627",
            "category":"biolink:Disease"
            },
            "n01":{
            "category":"biolink:ChemicalSubstance"
            }
          }
        }

    from ARAX_messenger import ARAXMessenger
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)

    response.envelope.message.query_graph = QueryGraph().from_dict(query_graph)

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
        'start_node': query_graph_info.start_node,
        'node_info': query_graph_info.node_info,
        'edge_info': query_graph_info.edge_info,
        'node_order': query_graph_info.node_order,
        'edge_order': query_graph_info.edge_order,
        'node_category_map': query_graph_info.node_category_map,
        'edge_predicate_map': query_graph_info.edge_predicate_map,
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
