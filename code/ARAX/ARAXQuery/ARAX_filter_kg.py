import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import numpy as np
from ARAX_response import ARAXResponse
import traceback
from collections import Counter

class ARAXFilterKG:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'remove_edges_by_predicate',
            'remove_edges_by_attribute',
            'remove_edges_by_stats',
            'remove_edges_by_property',
            'remove_nodes_by_category',
            'remove_nodes_by_property',
            'remove_orphaned_nodes',
        }
        self.report_stats = True  # Set this to False when ready to go to production, this is only for debugging purposes

        #parameter descriptions
        self.edge_type_info = {
            "is_required": True,
            "examples": ["contraindicated_for", "affects", "expressed_in"],
            "type": "ARAXedge",
            "description": "The name of the edge predicate to filter by."
        }
        self.remove_connected_nodes_info = {
            "is_required": False,
            "enum": ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'],
            "type": "boolean",
            "description": "Indicates whether or not to remove the nodes connected to the edge.",
            "default": 'false'
        }
        self.qnode_id_info = {
            "is_required": False,
            "examples": ['n01', 'n02'],
            "type": "string",
            "description": "If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed." +\
            "If not provided the qnode_id will not be considered when filtering."
        }
        self.edge_property_info = {
            "is_required": True,
            "examples": ['subject', 'provided_by', 'is_defined_by'],
            "type": "string",
            "description": "The name of the edge property to filter on."
        }
        self.edge_property_value_info = {
            "is_required": True,
            "examples": ['DOID:8398', 'Pharos', 'ARAX/RTX'],
            "type": "string",
            "description": "The edge property value to indicate which edges to remove."
        }
        self.edge_attribute_info = {
            "is_required": True,
            "examples": ["jaccard_index", "observed_expected_ratio", "normalized_google_distance"],
            "type": "string",
            "description": "The name of the edge attribute to filter on."
        }
        self.direction_info = {
            "is_required": True,
            "enum": ['above', 'below'],
            "type": "string",
            "description": "Indictes whether to remove above or below the given threshold."
        }
        self.threshold_info = {
            "is_required": True,
            "examples": [5,0.45],
            "min": '-inf',
            "max":'inf',
            "type": "float",
            "description": "The threshold to filter with."
        }
        self.type_info = {
            "is_required": False,
            "enum": ['n', 'std', 'std_dev', 'percentile', 'p'],
            "type": "string",
            "description": "The statistic to use for filtering.",
            "default": 'n'
        }
        self.threshold_stats_info = {
            "is_required": False,
            "examples": [5,0.45],
            "min": 0,
            "max": 'inf (or 100 if type=percentile or p)',
            "type": "float",
            "description": "The threshold to filter with.",
            "default": "a value dictated by the `type` parameter. " +\
            "If `type` is 'n' then `threshold` will default to 50. " +\
            "If `type` is 'std_dev' or 'std' then `threshold` will default to 1." +\
            "If `type` is 'percentile' or 'p' then `threshold` will default to 95 unless "+\
            "`edge_attribute` is also 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' "+\
            "then `threshold` will default to 5.",
            "UI_display": "false"
        }
        self.direction_stats_info = {
            "is_required": False,
            "enum": ['above', 'below'],
            "type": "string",
            "description": "Indictes whether to remove above or below the given threshold.",
            "default": "a value dictated by the `edge_attribute` parameter. " +\
            "If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `direction` defaults to above. " +\
            "If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `direction` defaults to below.",
            "UI_display": "false"
        }
        self.top_info = {
            "is_required": False,
            "enum": ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'],
            "type": "string",
            "description": "Indicate whether or not the threshold should be placed in top of the list. E.g. top set as True with type set as std_dev will set the cutoff for filtering as the mean + threshold * std_dev while setting top to False will set the cutoff as the mean - std_dev * threshold.",
            "default": "a value dictated by the `edge_attribute` parameter. " +\
            "If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `top` defaults to False. " +\
            "If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `top` defaults to True.",
            "UI_display": "false"
        }
        self.node_type_required_info = {
            "is_required": True,
            "examples": ["chemical_substance", "disease"],
            "type": "ARAXnode",
            "description": "The name of the node category to filter by."
        }
        self.node_type_info = {
            "is_required": False,
            "examples": ["chemical_substance", "disease"],
            "type": "ARAXnode",
            "description": "The name of the node category to filter by. If no value provided node category will not be considered."
        }
        self.node_property_info = {
            "is_required": True,
            "examples": ['provided_by', 'is_defined_by'],
            "type": "string",
            "description": "The name of the node property to filter on."
        }
        self.node_property_value_info = {
            "is_required": True,
            "examples": ['Pharos', 'ARAX/RTX'],
            "type": "string",
            "description": "The node property vaue to indicate which nodes to remove."
        }

        

        #command descriptions
        self.command_definitions = {
            "remove_edges_by_predicate": {
                "dsl_command": "filter_kg(action=remove_edges_by_predicate)",
                "description": """
`remove_edges_by_predicate` removes edges from the knowledge graph (KG) based on a given edge predicate.
Use cases include:
             
* removing all edges that have `edge_predicate=contraindicated_for`. 
* if virtual edges have been introduced with `overlay()` DSL commands, this action can remove all of them.
* etc.
            
You have the option to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`
            
This can be applied to an arbitrary knowledge graph as possible edge predicates are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
remove_edges_by_predicate removes edges from the knowledge graph (KG) based on a given edge predicate.
                    """,
                "parameters": {
                    "edge_predicate": self.edge_type_info,
                    "remove_connected_nodes": self.remove_connected_nodes_info,
                    "qnode_id": self.qnode_id_info
                }
            },
            "remove_edges_by_attribute": {
                "dsl_command": "filter_kg(action=remove_edges_by_attribute)",
                "description": """
`remove_edges_by_attribute` removes edges from the knowledge graph (KG) based on a a certain edge attribute.
Edge attributes are a list of additional attributes for an edge.
This action interacts particularly well with `overlay()` as `overlay()` frequently adds additional edge attributes.
Use cases include:

* removing all edges that have a normalized google distance above/below a certain value `edge_attribute=ngd, direction=above, threshold=0.85` (i.e. remove edges that aren't represented well in the literature)
* removing all edges that Jaccard index above/below a certain value `edge_attribute=jaccard_index, direction=below, threshold=0.2` (i.e. all edges that have less than 20% of intermediate nodes in common)
* removing all edges with clinical information satisfying some condition `edge_attribute=chi_square, direction=above, threshold=.005` (i.e. all edges that have a chi square p-value above .005)
* etc. etc.
                
You have the option to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`
                
This can be applied to an arbitrary knowledge graph as possible edge attributes are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
remove_edges_by_attribute removes edges from the knowledge graph (KG) based on a a certain edge attribute.
Edge attributes are a list of additional attributes for an edge.
This action interacts particularly well with overlay() as overlay() frequently adds additional edge attributes.
                    """,
                "parameters": {
                    "edge_attribute": self.edge_attribute_info,
                    "direction": self.direction_info,
                    "threshold": self.threshold_info,
                    "remove_connected_nodes": self.remove_connected_nodes_info,
                    "qnode_id": self.qnode_id_info
                }
            },
            "remove_edges_by_property": {
                "dsl_command": "filter_kg(action=remove_edges_by_property)",
                "description": """
`remove_edges_by_property` removes edges from the knowledge graph (KG) based on a given edge property.
Use cases include:
                
* removing all edges that were provided by a certain knowledge provider (KP) via `edge_property=provided, property_value=Pharos` to remove all edges provided by the KP Pharos.
* removing all edges that connect to a certain node via `edge_property=subject, property_value=DOID:8398`
* removing all edges with a certain relation via `edge_property=relation, property_value=upregulates`
* removing all edges provided by another ARA via `edge_property=is_defined_by, property_value=ARAX/RTX`
* etc. etc.
                
You have the option to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`
                
This can be applied to an arbitrary knowledge graph as possible edge properties are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
remove_edges_by_property removes edges from the knowledge graph (KG) based on a given edge property.
                    """,
                "parameters": {
                    "edge_property": self.edge_property_info,
                    "property_value": self.edge_property_value_info,
                    "remove_connected_nodes": self.remove_connected_nodes_info,
                    "qnode_id": self.qnode_id_info
                }
            },
            "remove_edges_by_stats": {
                "dsl_command": "filter_kg(action=remove_edges_by_stats)",
                "description": """
`remove_edges_by_stats` removes edges from the knowledge graph (KG) based on a certain edge attribute using default heuristics.
Edge attributes are a list of additional attributes for an edge.
This action interacts particularly well with `overlay()` as `overlay()` frequently adds additional edge attributes.
there are two heuristic options: `n` for removing all but the 50 best results, `std`/`std_dev` for removing all but 
the best results more than 1 standard deviation from the mean, or `percentile` to remove all but the best 
5% of results. (if not supplied this defaults to `n`)
Use cases include:

* removing all edges with normalized google distance scores but the top 50 `edge_attribute=ngd, type=n` (i.e. remove edges that aren't represented well in the literature)
* removing all edges that Jaccard index less than 1 standard deviation above the mean. `edge_attribute=jaccard_index, type=std` (i.e. all edges that have less than 20% of intermediate nodes in common)
* etc. etc.
                
You have the option (this defaults to false) to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`

You also have the option of specifying the direction to remove and location of the split by using the options 
* `direction` with options `above`,`below`
* `threshold` specified by a floating point number
* `top` which is boolean specified by `t`, `true`, `T`, `True` and `f`, `false`, `F`, `False`
e.g. to remove all the edges with jaccard_index values greater than 0.25 standard deviations below the mean you can run the following:
`filter_kg(action=remove_edges_by_stats, edge_attribute=jaccard_index, type=std, remove_connected_nodes=f, threshold=0.25, top=f, direction=above)`
                    """,
                'brief_description': """
remove_edges_by_stats removes edges from the knowledge graph (KG) based on a certain edge attribute using default heuristics.
Edge attributes are a list of additional attributes for an edge.
This action interacts particularly well with overlay() as overlay() frequently adds additional edge attributes.
                    """,
                "parameters": {
                    "edge_attribute": self.edge_attribute_info,
                    "type": self.type_info,
                    "direction": self.direction_stats_info,
                    "threshold": self.threshold_stats_info,
                    "top": self.top_info,
                    "remove_connected_nodes": self.remove_connected_nodes_info,
                    "qnode_id": self.qnode_id_info
                }
            },
            "remove_nodes_by_category": {
                "dsl_command": "filter_kg(action=remove_nodes_by_category)",
                "description": """
`remove_node_by_category` removes nodes from the knowledge graph (KG) based on a given node category.
Use cases include:
* removing all nodes that have `node_category=protein`.
* removing all nodes that have `node_category=chemical_substance`.
* etc.
This can be applied to an arbitrary knowledge graph as possible node categories are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
remove_node_by_category removes nodes from the knowledge graph (KG) based on a given node category.
                    """,
                "parameters": {
                    "node_category": self.node_type_required_info
                }
            },
            "remove_nodes_by_property": {
                "dsl_command": "filter_kg(action=remove_nodes_by_property)",
                "description": """
`remove_nodes_by_property` removes nodes from the knowledge graph (KG) based on a given node property.
Use cases include:
                
* removing all nodes that were provided by a certain knowledge provider (KP) via `node_property=provided, property_value=Pharos` to remove all nodes provided by the KP Pharos.
* removing all nodes provided by another ARA via `node_property=is_defined_by, property_value=ARAX/RTX`
* etc. etc.
                
This can be applied to an arbitrary knowledge graph as possible node properties are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
remove_nodes_by_property removes nodes from the knowledge graph (KG) based on a given node property.
                    """,
                "parameters": {
                    "node_property": self.node_property_info,
                    "property_value": self.node_property_value_info
                }
            },
            "remove_orphaned_nodes": {
                "dsl_command": "filter_kg(action=remove_orphaned_nodes)",
                "description": """
`remove_orphaned_nodes` removes nodes from the knowledge graph (KG) that are not connected via any edges.
Specifying a `node_category` will restrict this to only remove orphaned nodes of a certain category.
This can be applied to an arbitrary knowledge graph as possible node categories are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                'brief_description': """
remove_orphaned_nodes removes nodes from the knowledge graph (KG) that are not connected via any edges.
Specifying a 'node_category' will restrict this to only remove orphaned nodes of a certain category.
This can be applied to an arbitrary knowledge graph as possible node categories are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    """,
                "parameters": {
                    "node_category": self.node_type_info
                }
            }
        }


    def report_response_stats(self, response):
        """
        Little helper function that will report the KG, QG, and results stats to the debug in the process of executing actions. Basically to help diagnose problems
        """
        message = self.message
        if self.report_stats:
            # report number of nodes and edges, and their type in the QG
            if hasattr(message, 'query_graph') and message.query_graph:
                response.debug(f"Query graph is {message.query_graph}")
            if hasattr(message, 'knowledge_graph') and message.knowledge_graph and hasattr(message.knowledge_graph, 'nodes') and message.knowledge_graph.nodes and hasattr(message.knowledge_graph, 'edges') and message.knowledge_graph.edges:
                response.debug(f"Number of nodes in KG is {len(message.knowledge_graph.nodes)}")
                response.debug(f"Number of nodes in KG by type is {Counter([x.category[0] for x in message.knowledge_graph.nodes])}")  # type is a list, just get the first one
                #response.debug(f"Number of nodes in KG by with attributes are {Counter([x.category for x in message.knowledge_graph.nodes])}")  # don't really need to worry about this now
                response.debug(f"Number of edges in KG is {len(message.knowledge_graph.edges)}")
                response.debug(f"Number of edges in KG by type is {Counter([x.predicate for x in message.knowledge_graph.edges])}")
                response.debug(f"Number of edges in KG with attributes is {len([x for x in message.knowledge_graph.edges if x.edge_attributes])}")
                # Collect attribute names, could do this with list comprehension, but this is so much more readable
                attribute_names = []
                for x in message.knowledge_graph.edges:
                    if x.edge_attributes:
                        for attr in x.edge_attributes:
                            attribute_names.append(attr.name)
                response.debug(f"Number of edges in KG by attribute {Counter(attribute_names)}")
        return response

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        #description_list = []
        #for action in self.allowable_actions:
        #    description_list.append(getattr(self, '_' + self.__class__.__name__ + '__' + action)(describe=True))
        #return description_list
        return list(self.command_definitions.values())

    # Write a little helper function to test parameters
    def check_params(self, allowable_parameters):
        """
        Checks to see if the input parameters are allowed
        :param input_parameters: input parameters supplied to ARAXOverlay.apply()
        :param allowable_parameters: the allowable parameters
        :return: None
        """
        for key, item in self.parameters.items():
            if key not in allowable_parameters:
                self.response.error(
                    f"Supplied parameter {key} is not permitted. Allowable parameters are: {list(allowable_parameters.keys())}",
                    error_code="UnknownParameter")
            elif item not in allowable_parameters[key]:
                if any([type(x) == float for x in allowable_parameters[key]]):  # if it's a float, just accept it as it is
                    return
                else:  # otherwise, it's really not an allowable parameter
                    self.response.warning(
                        f"Supplied value {item} is not permitted. In action {allowable_parameters['action']}, allowable values to {key} are: {list(allowable_parameters[key])}")
                    return -1

    #### Top level decision maker for applying filters
    def apply(self, input_message, input_parameters):

        #### Define a default response
        response = ARAXResponse()
        self.response = response
        self.message = input_message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        # list of actions that have so far been created for ARAX_overlay
        allowable_actions = self.allowable_actions

        # check to see if an action is actually provided
        if 'action' not in input_parameters:
            response.error(f"Must supply an action. Allowable actions are: action={allowable_actions}", error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            response.error(f"Supplied action {input_parameters['action']} is not permitted. Allowable actions are: {allowable_actions}", error_code="UnknownAction")

        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        # populate the parameters dict
        parameters = dict()
        for key, value in input_parameters.items():
            parameters[key] = value

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters

        # convert the action string to a function call (so I don't need a ton of if statements
        getattr(self, '_' + self.__class__.__name__ + '__' + parameters['action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

        response.debug(f"Applying Overlay to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action

        #### Return the response and done
        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            response = self.report_response_stats(response)
        return response

    def __remove_edges_by_predicate(self, describe=False):
        """
        Removes edges from the KG.
        Allowable parameters: {'edge_predicate': str, 
                                'edge_property': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'edges'):
            allowable_parameters = {'action': {'remove_edges_by_predicate'},
                                    'edge_predicate': set([x.predicate for x in self.message.knowledge_graph.edges]),
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id': set([t for x in self.message.knowledge_graph.nodes if x.qnode_ids is not None for t in x.qnode_ids])
                                }
        else:
            allowable_parameters = {'action': {'remove_edges_by_predicate'},
                                    'edge_predicate': {'an edge predicate'},
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id':{'a specific query node id to remove'}
                                }

        # A little function to describe what this thing does
        if describe:
            allowable_parameters['brief_description'] = self.command_definitions['remove_edges_by_predicate']
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        edge_params = self.parameters
        if 'remove_connected_nodes' in edge_params:
            value = edge_params['remove_connected_nodes']
            if value in {'true', 'True', 't', 'T'}:
                edge_params['remove_connected_nodes'] = True
            elif value in {'false', 'False', 'f', 'F'}:
                edge_params['remove_connected_nodes'] = False
            else:
                self.response.error(f"Supplied value {value} is not permitted. In parameter remove_connected_nodes, allowable values are: {list(allowable_parameters['remove_connected_nodes'])}",
                    error_code="UnknownValue")
        else:
            edge_params['remove_connected_nodes'] = False

        # now do the call out to NGD
        from Filter_KG.remove_edges import RemoveEdges
        RE = RemoveEdges(self.response, self.message, edge_params)
        response = RE.remove_edges_by_predicate()
        return response

    def __remove_edges_by_property(self, describe=False):
        """
        Removes edges from the KG.
        Allowable parameters: {'edge_predicate': str, 
                                'edge_property': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters

        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'edges'):
            # check if all required parameters are provided
            if 'edge_property' not in parameters.keys():
                self.response.error(f"The parameter edge_property must be provided to remove edges by propery, allowable parameters include: {set([key for x in self.message.knowledge_graph.edges for key, val in x.to_dict().items() if type(val) == str])}")
            if self.response.status != 'OK':
                return self.response
            known_values = set()
            if 'edge_property' in parameters:
                for edge in message.knowledge_graph.edges:
                    if hasattr(edge, parameters['edge_property']):
                        value = edge.to_dict()[parameters['edge_property']]
                        if type(value) == str:
                            known_values.add(value)
                        elif type(value) == list:
                            for x in value:
                                if type(x) == str:
                                    known_values.add(x)
            allowable_parameters = {'action': {'remove_edges_by_property'},
                                    'edge_property': set([key for x in self.message.knowledge_graph.edges for key, val in x.to_dict().items() if type(val) == str or type(val) == list]),
                                    'property_value': known_values,
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id':set([t for x in self.message.knowledge_graph.nodes if x.qnode_ids is not None for t in x.qnode_ids])
                                }
        else:
            allowable_parameters = {'action': {'remove_edges_by_property'},
                                    'edge_property': {'an edge property'},
                                    'property_value':{'a value for the edge property'},
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id':{'a specific query node id to remove'}
                                }

        # A little function to describe what this thing does
        if describe:
            brief_description = self.command_definitions['remove_edges_by_property']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        edge_params = self.parameters
        if 'remove_connected_nodes' in edge_params:
            value = edge_params['remove_connected_nodes']
            if value in {'true', 'True', 't', 'T'}:
                edge_params['remove_connected_nodes'] = True
            elif value in {'false', 'False', 'f', 'F'}:
                edge_params['remove_connected_nodes'] = False
            else:
                self.response.error(f"Supplied value {value} is not permitted. In parameter remove_connected_nodes, allowable values are: {list(allowable_parameters['remove_connected_nodes'])}",
                    error_code="UnknownValue")
        else:
            edge_params['remove_connected_nodes'] = False

        if 'edge_property' not in edge_params:
            self.response.error(
                f"Edge property must be provided, allowable properties are: {list(allowable_parameters['edge_property'])}",
                error_code="UnknownValue")
        if 'property_value' not in edge_params:
            self.response.error(
                f"Property value must be provided, allowable values are: {list(allowable_parameters['property_value'])}",
                error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_KG.remove_edges import RemoveEdges
        RE = RemoveEdges(self.response, self.message, edge_params)
        response = RE.remove_edges_by_property()
        return response

    def __remove_edges_by_attribute(self, describe=False):
        """
        Removes edges from the KG.
        Allowable parameters: {'edge_predicate': str, 
                                'edge_attribute': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'knowledge_graph') and hasattr(message.knowledge_graph, 'edges'):
            known_attributes = set()
            for edge in message.knowledge_graph.edges:
                if hasattr(edge, 'edge_attributes'):
                    if edge.edge_attributes:
                        for attribute in edge.edge_attributes:
                            known_attributes.add(attribute.name)
            # print(known_attributes)
            allowable_parameters = {'action': {'remove_edges_by_attribute'},
                                    'edge_attribute': known_attributes,
                                    'direction': {'above', 'below'},
                                    'threshold': {float()},
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id':set([t for x in self.message.knowledge_graph.nodes if x.qnode_ids is not None for t in x.qnode_ids])
                                    }
        else:
            allowable_parameters = {'action': {'remove_edges_by_attribute'},
                                    'edge_attribute': {'an edge attribute name'},
                                    'direction': {'above', 'below'},
                                    'threshold': {'a floating point number'},
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id':{'a specific query node id to remove'}
                                    }

        # A little function to describe what this thing does
        if describe:
            brief_description = self.command_definitions['remove_edges_by_attribute']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        edge_params = self.parameters

        # try to convert the threshold to a float
        try:
            edge_params['threshold'] = float(edge_params['threshold'])
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"parameter 'threshold' must be a float")
        if self.response.status != 'OK':
            return self.response

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        if 'remove_connected_nodes' in edge_params:
            value = edge_params['remove_connected_nodes']
            if value in {'true', 'True', 't', 'T'}:
                edge_params['remove_connected_nodes'] = True
            elif value in {'false', 'False', 'f', 'F'}:
                edge_params['remove_connected_nodes'] = False
            else:
                self.response.error(
                    f"Supplied value {value} is not permitted. In parameter remove_connected_nodes, allowable values are: {list(allowable_parameters['remove_connected_nodes'])}",
                    error_code="UnknownValue")
        else:
            edge_params['remove_connected_nodes'] = False

        if 'direction' not in edge_params:
            self.response.error(
                f"Direction must be provided, allowable directions are: {list(allowable_parameters['direction'])}",
                error_code="UnknownValue")
        if 'edge_attribute' not in edge_params:
            self.response.error(
                f"Edge attribute must be provided, allowable attributes are: {list(allowable_parameters['edge_attribute'])}",
                error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_KG.remove_edges import RemoveEdges
        RE = RemoveEdges(self.response, self.message, edge_params)
        response = RE.remove_edges_by_attribute()
        return response

    def __remove_edges_by_stats(self, describe=False):
        """
        Removes edges from the KG.
        Allowable parameters: {'edge_predicate': str, 
                                'edge_attribute': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'knowledge_graph') and hasattr(message.knowledge_graph, 'edges'):
            known_attributes = set()
            for edge in message.knowledge_graph.edges:
                if hasattr(edge, 'edge_attributes'):
                    if edge.edge_attributes:
                        for attribute in edge.edge_attributes:
                            known_attributes.add(attribute.name)
            # print(known_attributes)
            allowable_parameters = {'action': {'remove_edges_by_stats'},
                                    'edge_attribute': known_attributes,
                                    'type': {'n', 'std', 'std_dev', 'percentile', 'p'},
                                    'direction': {'above', 'below'},
                                    'threshold': {float()},
                                    'top': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id':set([t for x in self.message.knowledge_graph.nodes if x.qnode_ids is not None for t in x.qnode_ids])
                                    }
        else:
            allowable_parameters = {'action': {'remove_edges_by_stats'},
                                    'edge_attribute': {'an edge attribute name'},
                                    'type': {'n', 'top_n', 'std', 'top_std'},
                                    'direction': {'above', 'below'},
                                    'threshold': {'a floating point number'},
                                    'top': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'remove_connected_nodes': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'},
                                    'qnode_id':{'a specific query node id to remove'}
                                    }

        # A little function to describe what this thing does
        if describe:
            brief_description = self.command_definitions['remove_edges_by_stats']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        edge_params = self.parameters

        # try to convert the threshold to a float
        if self.response.status != 'OK':
            return self.response

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        supplied_threshhold = None
        supplied_direction = None
        supplied_top = None

        if 'threshold' in edge_params:
            try:
                edge_params['threshold'] = float(edge_params['threshold'])
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"parameter 'threshold' must be a float")
            if self.response.status != 'OK':
                return self.response
            supplied_threshhold = edge_params['threshold']
        if 'direction' in edge_params:
            supplied_direction = edge_params['direction']
        if 'top' in edge_params:
            if edge_params['top'] in {'true', 'True', 't', 'T'}:
                supplied_top = True
            elif edge_params['top'] in {'false', 'False', 'f', 'F'}:
                supplied_top = False

        if 'remove_connected_nodes' in edge_params:
            value = edge_params['remove_connected_nodes']
            if value in {'true', 'True', 't', 'T'}:
                edge_params['remove_connected_nodes'] = True
            elif value in {'false', 'False', 'f', 'F'}:
                edge_params['remove_connected_nodes'] = False
            else:
                self.response.error(
                    f"Supplied value {value} is not permitted. In parameter remove_connected_nodes, allowable values are: {list(allowable_parameters['remove_connected_nodes'])}",
                    error_code="UnknownValue")
        else:
            edge_params['remove_connected_nodes'] = False

        if 'type' in edge_params:
            if edge_params['type'] in {'n'}:
                edge_params['stat'] = 'n'
                edge_params['threshold']= 50
            elif edge_params['type'] in {'std', 'std_dev'}:
                edge_params['stat'] = 'std'
                edge_params['threshold'] = 1
            elif edge_params['type'] in {'percentile', 'p'}:
                edge_params['stat'] = 'percentile'
                edge_params['threshold'] = 95
                if supplied_threshhold is not None:
                    if supplied_threshhold > 100 or supplied_threshhold < 0:
                        self.response.error(
                            f"Supplied value {supplied_threshhold} is not permitted. In parameter threshold, when using the percentile type allowable values are real numbers between 0 and 100.",
                            error_code="UnknownValue")
        else:
            edge_params['stat'] = 'n'
            edge_params['threshold']= 50
        if 'edge_attribute' not in edge_params:
            self.response.error(
                f"Edge attribute must be provided, allowable attributes are: {list(allowable_parameters['edge_attribute'])}",
                error_code="UnknownValue")
        else:
            if edge_params['edge_attribute'] in {'ngd', 'chi_square', 'fisher_exact', 'normalized_google_distance'}:
                edge_params['direction'] = 'above'
                edge_params['top'] = False
                if edge_params['stat'] == 'percentile':
                    edge_params['threshold'] = 1-edge_params['threshold']
            elif edge_params['edge_attribute'] in {'jaccard_index', 'observed_expected_ratio', 'probability_treats'}:
                edge_params['direction'] = 'below'
                edge_params['top'] = True
            else:
                edge_params['direction'] = 'below'
                edge_params['top'] = True
        
        if supplied_threshhold is not None:
            edge_params['threshold'] = supplied_threshhold
        if supplied_direction is not None:
            edge_params['direction'] = supplied_direction
        if supplied_top is not None:
            edge_params['top'] = supplied_top

        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_KG.remove_edges import RemoveEdges
        RE = RemoveEdges(self.response, self.message, edge_params)
        response = RE.remove_edges_by_stats()
        return response

    def __remove_nodes_by_category(self, describe=False):
        """
        Removes nodes from the KG.
        Allowable parameters: {'node_category': str, 
                                'node_property': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'remove_nodes_by_category'},
                                    'node_category': set([t for x in self.message.knowledge_graph.nodes for t in x.category])
                                   }
        else:
            allowable_parameters = {'action': {'remove_nodes_by_category'}, 
                                'node_category': {'a node category'}}

        # A little function to describe what this thing does
        if describe:
            brief_description = self.command_definitions['remove_nodes_by_category']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        node_params = self.parameters

        # now do the call out to NGD
        from Filter_KG.remove_nodes import RemoveNodes
        RN = RemoveNodes(self.response, self.message, node_params)
        response = RN.remove_nodes_by_category()
        return response

    def __remove_nodes_by_property(self, describe=False):
        """
        Removes nodes from the KG.
        Allowable parameters: {'node_category': str, 
                                'node_property': str,
                                'direction': {'above', 'below'}}
        :return:
        """
        message = self.message
        parameters = self.parameters

        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            # check if all required parameters are provided
            if 'node_property' not in parameters.keys():
                self.response.error(f"The parameter node_property must be provided to remove nodes by propery, allowable parameters include: {set([key for x in self.message.knowledge_graph.nodes for key, val in x.to_dict().items() if type(val) == str])}")
            if self.response.status != 'OK':
                return self.response
            known_values = set()
            if 'node_property' in parameters:
                for node in message.knowledge_graph.nodes:
                    if hasattr(node, parameters['node_property']):
                        value = node.to_dict()[parameters['node_property']]
                        if type(value) == str:
                            known_values.add(value)
            allowable_parameters = {'action': {'remove_nodes_by_property'},
                                    'node_property': set([key for x in self.message.knowledge_graph.nodes for key, val in x.to_dict().items() if type(val) == str]),
                                    'property_value': known_values
                                }
        else:
            allowable_parameters = {'action': {'remove_nodes_by_property'},
                                    'node_property': {'an node property'},
                                    'property_value':{'a value for the node property'}
                                }

        # A little function to describe what this thing does
        if describe:
            brief_description = self.command_definitions['remove_nodes_by_property']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        node_params = self.parameters

        if 'node_property' not in node_params:
            self.response.error(
                f"node property must be provided, allowable properties are: {list(allowable_parameters['node_property'])}",
                error_code="UnknownValue")
        if 'property_value' not in node_params:
            self.response.error(
                f"Property value must be provided, allowable values are: {list(allowable_parameters['property_value'])}",
                error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_KG.remove_nodes import RemoveNodes
        RN = RemoveNodes(self.response, self.message, node_params)
        response = RN.remove_nodes_by_property()
        return response

    def __remove_orphaned_nodes(self, describe=False):
        """
        Removes orphaned nodes from the KG nodes from the KG.
        Allowable parameters: {'node_category': str,
                                'node_property': str,}
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'query_graph') and hasattr(message.query_graph, 'nodes'):
            allowable_parameters = {'action': {'remove_orphaned_nodes'},
                                    'node_category': set(
                                        [t for x in self.message.knowledge_graph.nodes for t in x.category])
                                    }
        else:
            allowable_parameters = {'action': {'remove_orphaned_nodes'},
                                    'node_category': {'a node category (optional)'}}

        # A little function to describe what this thing does
        if describe:
            brief_description = self.command_definitions['remove_orphaned_nodes']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        node_params = self.parameters

        # now do the call out to NGD
        from Filter_KG.remove_nodes import RemoveNodes
        RN = RemoveNodes(self.response, self.message, node_params)
        response = RN.remove_orphaned_nodes()
        return response

##########################################################################################
def main():
    ### Note that most of this is just manually doing what ARAXQuery() would normally do for you

    #### Create a response object
    response = ARAXResponse()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()

    #### Set a simple list of actions
    # actions_list = [
    #    "overlay(compute_confidence_scores=true)",
    #    "return(message=true,store=false)"
    # ]

    actions_list = [
        #"filter_kg(action=remove_edges_by_predicate, edge_predicate=physically_interacts_with, remove_connected_nodes=false)",
        #"filter_kg(action=remove_edges_by_predicate, edge_predicate=physically_interacts_with, remove_connected_nodes=something)",
        #"filter(action=remove_nodes_by_category, node_category=protein)",
        #"overlay(action=compute_ngd)",
        #"filter(action=remove_edges_by_attribute, edge_attribute=ngd, threshold=.63, direction=below, remove_connected_nodes=t)",
        #"filter(action=remove_edges_by_attribute, edge_attribute=ngd, threshold=.6, remove_connected_nodes=False)",
        "filter(action=remove_orphaned_nodes)",
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
    sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/Feedback")
    from RTXFeedback import RTXFeedback
    araxdb = RTXFeedback()

    #message_dict = araxdb.getMessage(2)  # acetaminophen2proteins graph
    # message_dict = araxdb.getMessage(13)  # ibuprofen -> proteins -> disease # work computer
    # message_dict = araxdb.getMessage(14)  # pleuropneumonia -> phenotypic_feature # work computer
    # message_dict = araxdb.getMessage(16)  # atherosclerosis -> phenotypic_feature  # work computer
    # message_dict = araxdb.getMessage(5)  # atherosclerosis -> phenotypic_feature  # home computer
    # message_dict = araxdb.getMessage(10)
    message_dict = araxdb.getMessage(40)

    #### The stored message comes back as a dict. Transform it to objects
    from ARAX_messenger import ARAXMessenger
    message = ARAXMessenger().from_dict(message_dict)
    # print(json.dumps(message.to_dict(),sort_keys=True,indent=2))

    #### Create an overlay object and use it to apply action[0] from the list
    #filterkg = ARAXFilterKG()
    #result = filterkg.apply(message, actions[0]['parameters'])
    #response.merge(result)

    # Apply overlay so you get an edge attribute to work with, then apply the filter
    #from ARAX_overlay import ARAXOverlay
    #overlay = ARAXOverlay()
    #result = overlay.apply(message, actions[0]['parameters'])
    #response.merge(result)
    # then apply the filter
    filterkg = ARAXFilterKG()
    result = filterkg.apply(message, actions[0]['parameters'])
    response.merge(result)

    # if result.status != 'OK':
    #    print(response.show(level=ARAXResponse.DEBUG))
    #    return response
    # response.data = result.data

    #### If successful, show the result
    # print(response.show(level=ARAXResponse.DEBUG))
    # response.data['message_stats'] = { 'n_results': message.n_results, 'id': message.id,
    #    'reasoner_id': message.reasoner_id, 'tool_version': message.tool_version }
    # response.data['message_stats']['confidence_scores'] = []
    # for result in message.results:
    #    response.data['message_stats']['confidence_scores'].append(result.confidence)

    # print(json.dumps(ast.literal_eval(repr(response.data['parameters'])),sort_keys=True,indent=2))
    # print(json.dumps(ast.literal_eval(repr(response.data['message_stats'])),sort_keys=True,indent=2))
    # a comment on the end so you can better see the network on github

    # look at the response
    # print(response.show(level=ARAXResponse.DEBUG))
    # print(response.show())
    # print("Still executed")

    # look at the edges
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)),sort_keys=True,indent=2))
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.nodes)), sort_keys=True, indent=2))
    # print(json.dumps(message.to_dict(), sort_keys=True, indent=2))
    # print(response.show(level=ARAXResponse.DEBUG))

    # just print off the values
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2))
    # for edge in message.knowledge_graph.edges:
    #    if hasattr(edge, 'edge_attributes') and edge.edge_attributes and len(edge.edge_attributes) >= 1:
    #        print(edge.edge_attributes.pop().value)
    print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2))
    print(response.show(level=ARAXResponse.DEBUG))
    vals = []
    for node in message.knowledge_graph.nodes:
        print(node.id)
    print(len(message.knowledge_graph.nodes))
    for edge in message.knowledge_graph.edges:
        if hasattr(edge, 'edge_attributes') and edge.edge_attributes and len(edge.edge_attributes) >= 1:
            vals.append(edge.edge_attributes.pop().value)
    print(sorted(vals))


if __name__ == "__main__": main()
