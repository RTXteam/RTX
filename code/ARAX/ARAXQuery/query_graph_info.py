#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response


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
        self.node_type_map = None
        self.edge_type_map = None

        self.query_graph_template = None


    #### Top level decision maker for applying filters
    def assess(self, message):

        #### Define a default response
        response = Response()
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
        if self.n_nodes == 2 and self.n_edges > 1:
            response.error("QueryGraph may not have more than 1 edge if there are only 2 nodes", error_code="QueryGraphTooManyEdges")
            return response

        #### Loop through nodes computing some stats
        node_info = {}
        self.node_type_map = {}
        for qnode in nodes:
            id = qnode.id
            node_info[id] = { 'id': id, 'node_object': qnode, 'has_curie': False, 'type': qnode.type, 'has_type': False, 'is_set': False, 'n_edges': 0, 'is_connected': False, 'edges': [], 'edge_dict': {} }
            if qnode.curie is not None: node_info[id]['has_curie'] = True
            if qnode.type is not None: node_info[id]['has_type'] = True
            #if qnode.is_set is not None: node_info[id]['is_set'] = True
            if qnode.id is None:
                response.error("QueryGraph has a node with no id. This is not permitted", error_code="QueryGraphNodeWithNoId")
                return response

            #### Store lookup of types
            warning_counter = 0
            if qnode.type is None:
                if warning_counter == 0:
                    response.debug("QueryGraph has nodes with no type. This may cause problems with results inference later")
                warning_counter += 1
                self.node_type_map['unknown'] = id
            else:
                self.node_type_map[qnode.type] = id

        #### Loop through edges computing some stats
        edge_info = {}
        self.edge_type_map = {}
        for qedge in edges:
            id = qedge.id
            edge_info[id] = { 'id': id, 'has_type': False, 'source_id': qedge.source_id, 'target_id': qedge.target_id, 'type': None }
            if qnode.type is not None:
                edge_info[id]['has_type'] = True
                edge_info[id]['type'] = qnode.type
            if qedge.id is None:
                response.error("QueryGraph has a edge with no id. This is not permitted", error_code="QueryGraphEdgeWithNoId")
                return response
            node_info[qedge.source_id]['n_edges'] += 1
            node_info[qedge.target_id]['n_edges'] += 1
            node_info[qedge.source_id]['is_connected'] = True
            node_info[qedge.target_id]['is_connected'] = True
            #node_info[qedge.source_id]['edges'].append(edge_info[id])
            #node_info[qedge.target_id]['edges'].append(edge_info[id])
            node_info[qedge.source_id]['edges'].append(edge_info[id])
            node_info[qedge.target_id]['edges'].append(edge_info[id])
            node_info[qedge.source_id]['edge_dict'][id] = edge_info[id]
            node_info[qedge.target_id]['edge_dict'][id] = edge_info[id]

            #### Store lookup of types
            warning_counter = 0
            edge_type = 'any'
            if qedge.type is None:
                if warning_counter == 0:
                    response.debug("QueryGraph has edges with no type. This may cause problems with results inference later")
                warning_counter += 1
            else:
                edge_type = qedge.type

            #### It's not clear yet whether we need to store the whole sentence or just the type
            #type_encoding = f"{node_info[qedge.source_id]['type']}---{edge_type}---{node_info[qedge.target_id]['type']}"
            type_encoding = edge_type
            self.edge_type_map[type_encoding] = id

        #### Loop through the nodes again, trying to identify the start_node and the end_node
        singletons = []
        for node_id,node_data in node_info.items():
            if node_data['n_edges'] < 2:
                singletons.append(node_data)
            elif node_data['n_edges'] > 2:
                self.is_bifurcated_graph = True
                response.warning("QueryGraph appears to have a fork in it. This might cause trouble")

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
            if singletons[0]['has_curie'] is True and singletons[1]['has_curie'] is False:
                start_node = singletons[0]
            elif singletons[0]['has_curie'] is False and singletons[1]['has_curie'] is True:
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
        while 1:
            #tmp = { 'astate': '1', 'current_node': current_node, 'node_order': node_order, 'edge_order': edge_order, 'edges': edges }
            #print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))
            #print('==================================================================================')
            #tmp = input()

            if len(edges) == 0:
                break
            if len(edges) > 1:
                response.error("Help, two edges at A583. Don't know what to do", error_code="InteralErrorA583")
                return response
            edge_order.append(edges[0])
            previous_node = current_node
            if edges[0]['source_id'] == current_node['id']:
                current_node = node_info[edges[0]['target_id']]
            elif edges[0]['target_id'] == current_node['id']:
                current_node = node_info[edges[0]['source_id']]
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
                if edge['id'] not in previous_node['edge_dict']:
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
        self.query_graph_template = ''
        node_index = 0
        edge_index = 0
        for node in node_order:
            template_id = f"n{node_index:02}"
            content = ''
            if node['has_curie']:
                content = 'curie'
            elif node['has_type']:
                content = 'type'
            template_part = f"{template_id}({content})"
            self.query_graph_template += template_part

            # Since queries with intermediate nodes that are not is_set=true tend to blow up, for now, make them is_set=true unless explicitly set to false
            if node_index > 0 and node_index < (self.n_nodes - 1 ):
                if 'is_set' not in node or node['is_set'] is None:
                    node['node_object'].is_set = True
                    response.warning(f"Setting unspecified is_set to true for {node['id']} because this will probably lead to a happier result")
                elif node['is_set'] is True:
                    response.debug(f"Value for is_set is already true for {node['id']} so that's good")
                elif node['is_set'] is False:
                    #response.info(f"Value for is_set is set to false for intermediate node {node['id']}. This could lead to weird results. Consider setting it to true")
                    response.info(f"Value for is_set is false for intermediate node {node['id']}. Setting to true because this will probably lead to a happier result")
                    node['node_object'].is_set = True
                #else:
                #    response.error(f"Unrecognized value is_set='{node['is_set']}' for {node['id']}. This should be true or false")

            node_index += 1
            if node_index < self.n_nodes:
                self.query_graph_template += f"-e{edge_index:02}()-"
                edge_index += 1

        response.debug(f"The QueryGraph reference template is: {self.query_graph_template}")

        #tmp = { 'node_info': node_info, 'edge_info': edge_info, 'start_node': start_node, 'n_nodes': self.n_nodes, 'n_edges': self.n_edges,
        #    'is_bifurcated_graph': self.is_bifurcated_graph, 'node_order': node_order, 'edge_order': edge_order }
        #print(json.dumps(ast.literal_eval(repr(tmp)),sort_keys=True,indent=2))
        #sys.exit(0)

        #### Return the response
        return response



##########################################################################################
def main():

    #### Create a response object
    response = Response()

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
        print(response.show(level=Response.DEBUG))
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
    #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))

    #### Create a filter object and use it to apply action[0] from the list
    query_graph_info = QueryGraphInfo()
    result = query_graph_info.assess(message)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
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
        'node_type_map': query_graph_info.node_type_map,
        'edge_type_map': query_graph_info.edge_type_map,
    }
    print(json.dumps(ast.literal_eval(repr(query_graph_info_dict)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
