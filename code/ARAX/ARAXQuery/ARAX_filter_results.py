#!/bin/env python3
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

class ARAXFilterResults:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        self.allowable_actions = {
            'sort_by_edge_attribute',
            'sort_by_node_attribute',
            'limit_number_of_results',
            'sort_by_edge_count',
            'sort_by_node_count'
        }
        self.report_stats = True  # Set this to False when ready to go to production, this is only for debugging purposes

        #parameter descriptions
        self.edge_attribute_info = {
            "is_required": True,
            "examples": ["jaccard_index", "observed_expected_ratio", "normalized_google_distance"],
            "type": "string",
            "description": "The name of the attribute to filter by."
        }
        self.direction_info = {
            "is_required": True,
            "enum": ['descending', 'd', 'ascending', 'a'],
            "type": "string",
            "description": "The direction in which to order results. (ascending or descending)"
        }
        self.max_results_info = {
            "is_required": False,
            "examples": [5,10,50],
            "min":0,
            "max":'inf',
            "type": "int",
            "description": "The maximum number of results to return. If not provided all results will be returned."
        }
        self.max_results_required_info = {
            "is_required": True,
            "examples": [5,10,50],
            "min":0,
            "max":'inf',
            "type": "int",
            "description": "The maximum number of results to return. If not provided all results will be returned."
        }
        self.edge_relation_info = {
            "is_required": False,
            "examples": ['N1', 'C1'],
            "type": "string",
            "description": "The name of unique identifier to only filter on edges with matching relation field. (stored in the relation neo4j edge property) "+\
            "If not provided the edge relation will not be considered when filtering."
        }
        self.node_attribute_info = {
            "is_required": True,
            "examples": ["pubmed_ids"],
            "type": "string",
            "description": "The name of the attribute to filter by."
        }
        self.node_type_info = {
            "is_required": False,
            "examples": ["chemical_substance", "disease"],
            "type": "ARAXnode",
            "description": "The name of the node category to only filter on nodes of the matching category. " +\
            "If not provided the node category will not be considered when filtering."
        }
        self.prune_kg_info = {
            "is_required": False,
            "enum": ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'],
            "type": "boolean",
            "description": "This indicates if the Knowledge Graph (KG) should be pruned so that any nodes or edges not appearing in the results are removed from the KG.",
            "default": "true"
        }

        #command descriptions
        self.command_definitions = {
            "sort_by_edge_attribute": {
                "dsl_command": "filter_results(action=sort_by_edge_attribute)",
                "description": """
`sort_by_edge_attribute` sorts the results by the edges based on a a certain edge attribute.
Edge attributes are a list of additional attributes for an edge.
Use cases include:

* sorting the results by the value of the jaccard index and take the top ten `filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=d, max_results=10)`
* etc. etc.
                
You have the option to specify the edge relation (e.g. via `edge_relation=<an edge relation>`)
Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`
                    """,
                'brief_description': """
sort_by_edge_attribute sorts the results by the edges based on a a certain edge attribute.
Edge attributes are a list of additional attributes for an edge.
                    """,
                "parameters": {
                    "edge_attribute": self.edge_attribute_info,
                    "edge_relation": self.edge_relation_info,
                    "direction": self.direction_info,
                    "max_results": self.max_results_info,
                    "prune_kg": self.prune_kg_info
                }
            },
            "sort_by_node_attribute": {
                "dsl_command": "filter_results(action=sort_by_node_attribute)",
                "description": """
`sort_by_node_attribute` sorts the results by the nodes based on a a certain node attribute.
Node attributes are a list of additional attributes for an node.
Use cases include:

* Sorting the results by the number of pubmed ids and returning the top 20. `"filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=d, max_results=20)"`
* etc. etc.
                
You have the option to specify the node category. (e.g. via `node_category=<a node category>`)
Also, you have the option of limiting the number of results returned. (e.g. via `max_results=<a non-negative integer>`
                    """,
                'brief_description': """
sort_by_node_attribute sorts the results by the nodes based on a a certain node attribute.
Node attributes are a list of additional attributes for an node.
                    """,
                "parameters": {
                    "node_attribute": self.node_attribute_info,
                    "node_category": self.node_type_info,
                    "direction": self.direction_info,
                    "max_results": self.max_results_info,
                    "prune_kg": self.prune_kg_info
                }
            },
            "limit_number_of_results": {
                "dsl_command": "filter_results(action=limit_number_of_results)",
                "description": """
`limit_number_of_results` removes excess results over the specified maximum.

Use cases include:

* limiting the number of results to 100 `filter_results(action=limit_number_of_results, max_results=100)`
* etc. etc.
                    """,
                'brief_description': """
limit_number_of_results removes excess results over the specified maximum.
                    """,
                "parameters": {
                    "max_results": self.max_results_required_info,
                    "prune_kg": self.prune_kg_info
                }
            },
            "sort_by_edge_count": {
                "dsl_command": "filter_results(action=sort_by_edge_count)",
                "description": """
`sort_by_edge_count` sorts the results by the number of edges in the results.
Use cases include:

* return the results with the 10 fewest edges. `filter_results(action=sort_by_edge_count, direction=ascending, max_results=10)`
* etc. etc.
                
You have the option to specify the direction. (e.g. `direction=descending`)
Also, you have the option of limiting the number of results returned. (e.g. via `max_results=<a non-negative integer>`
                    """,
                'brief_description': """
sort_by_edge_count sorts the results by the number of edges in the results.
                    """,
                "parameters": {
                    "direction": self.direction_info,
                    "max_results": self.max_results_info,
                    "prune_kg": self.prune_kg_info
                }
            },
            "sort_by_node_count": {
                "dsl_command": "filter_results(action=sort_by_node_count)",
                "description": """
`sort_by_node_count` sorts the results by the number of nodes in the results.
Use cases include:

* return the results with the 10 most nodes. `filter_results(action=sort_by_node_count, direction=descending, max_results=10)`
* etc. etc.
                
You have the option to specify the direction. (e.g. `direction=descending`)
Also, you have the option of limiting the number of results returned. (e.g. via `max_results=<a non-negative integer>`
                    """,
                'brief_description': """
sort_by_node_count sorts the results by the number of nodes in the results.
                    """,
                "parameters": {
                    "direction": self.direction_info,
                    "max_results": self.max_results_info,
                    "prune_kg": self.prune_kg_info
                }
            }
        }

    def check_results(self, message):
        if not hasattr(message, 'results') or len(message.results) == 0:
            self.response.warning(
                        f"filter_results called with no results.")
            return True
        return False

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
                response.debug(f"Number of nodes in KG by type is {Counter([x.category[0] for x in message.knowledge_graph.nodes.values()])}")  # type is a list, just get the first one
                #response.debug(f"Number of nodes in KG by with attributes are {Counter([x.category for x in message.knowledge_graph.nodes.values()])}")  # don't really need to worry about this now
                response.debug(f"Number of edges in KG is {len(message.knowledge_graph.edges)}")
                response.debug(f"Number of edges in KG by type is {Counter([x.predicate for x in message.knowledge_graph.edges.values()])}")
                response.debug(f"Number of edges in KG with attributes is {len([x for x in message.knowledge_graph.edges.values() if x.attributes])}")
                # Collect attribute names, could do this with list comprehension, but this is so much more readable
                attribute_names = []
                for x in message.knowledge_graph.edges.values():
                    if x.attributes:
                        for attr in x.attributes:
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
    def apply(self, input_response, input_parameters):

        #### Define a default response
        #response = ARAXResponse()
        self.response = input_response
        self.message = input_response.envelope.message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            self.response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return self.response

        # list of actions that have so far been created for ARAX_overlay
        allowable_actions = self.allowable_actions

        # check to see if an action is actually provided
        if 'action' not in input_parameters:
            self.response.error(f"Must supply an action. Allowable actions are: action={allowable_actions}", error_code="MissingAction")
        elif input_parameters['action'] not in allowable_actions:
            self.response.error(f"Supplied action {input_parameters['action']} is not permitted. Allowable actions are: {allowable_actions}", error_code="UnknownAction")

        #### Return if any of the parameters generated an error (showing not just the first one)
        if self.response.status != 'OK':
            return self.response

        # populate the parameters dict
        parameters = dict()
        for key, value in input_parameters.items():
            parameters[key] = value

        #### Store these final parameters for convenience
        self.response.data['parameters'] = parameters
        self.parameters = parameters

        # convert the action string to a function call (so I don't need a ton of if statements
        getattr(self, '_' + self.__class__.__name__ + '__' + parameters['action'])()  # thank you https://stackoverflow.com/questions/11649848/call-methods-by-string

        self.response.debug(f"Applying Overlay to Message with parameters {parameters}")  # TODO: re-write this to be more specific about the actual action

        #### Return the response and done
        if self.report_stats:  # helper to report information in debug if class self.report_stats = True
            self.response = self.report_response_stats(self.response)
        return self.response

    def __sort_by_edge_attribute(self, describe=False):
        """
        sorts by results edge attribute
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'results') and hasattr(message, 'knowledge_graph') and hasattr(message.knowledge_graph, 'edges'):
            known_attributes = set()
            for edge in message.knowledge_graph.edges.values():
                if hasattr(edge, 'attributes'):
                    if edge.attributes:
                        for attribute in edge.attributes:
                            known_attributes.add(attribute.name)
            # print(known_attributes)
            allowable_parameters = {'action': {'sort_by_edge_attribute'},
                                    'edge_attribute': known_attributes,
                                    'edge_relation': set([x.relation for x in self.message.knowledge_graph.edges.values()]),
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {float()},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }
        else:
            allowable_parameters = {'action': {'sort_by_edge_attribute'},
                                    'edge_attribute': {'an edge attribute'},
                                    'edge_relation': {'an edge relation'},
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {'the maximum number of results to return'},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }

        # A little function to describe what this thing does
        if describe:
            brief_description = self.command_definitions['sort_by_edge_attribute']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        edge_params = self.parameters

        if self.check_results(message):
            return self.response

        # try to convert the max results to an int
        if 'max_results' in edge_params:
            try:
                edge_params['max_results'] = int(edge_params['max_results'])
                assert edge_params['max_results'] >= 0
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"parameter 'max_results' must be a non-negative integer")
            if self.response.status != 'OK':
                return self.response

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        if 'direction' not in edge_params:
            self.response.error(
                f"Direction must be provided, allowable directions are: {list(allowable_parameters['direction'])}",
                error_code="UnknownValue")
        else:
            value = edge_params['direction']
            if value in {'descending', 'd'}:
                edge_params['descending'] = True
            elif value in {'ascending', 'a'}:
                edge_params['descending'] = False
            else:
                self.response.error(
                    f"Supplied value {value} is not permitted. In parameter direction, allowable values are: {list(allowable_parameters['direction'])}",
                    error_code="UnknownValue")
        if 'edge_attribute' not in edge_params:
            self.response.error(
                f"Edge attribute must be provided, allowable attributes are: {list(allowable_parameters['edge_attribute'])}",
                error_code="UnknownValue")
        if 'prune_kg' not in edge_params:
            edge_params['prune_kg'] = True
        elif edge_params['prune_kg'] in {'true', 'True', 't', 'T'}:
            edge_params['prune_kg'] = True
        elif edge_params['prune_kg'] in {'false', 'False', 'f', 'F'}:
            edge_params['prune_kg'] = False
        else:
            value = edge_params['prune_kg']
            self.response.error(
                    f"Supplied value {value} is not permitted. In parameter prune_kg, allowable values are: {list(allowable_parameters['prune_kg'])}",
                    error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_Results.sort_results import SortResults
        SR = SortResults(self.response, self.message, edge_params)
        response = SR.sort_by_edge_attribute()
        return response

    def __sort_by_node_attribute(self, describe=False):
        """
        sorts results by node attribute
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'results') and hasattr(message, 'knowledge_graph') and hasattr(message.knowledge_graph, 'nodes'):
            known_attributes = set()
            for node in message.knowledge_graph.nodes.values():
                if hasattr(node, 'attributes'):
                    if node.attributes:
                        for attribute in node.attributes:
                            known_attributes.add(attribute.name)
            # print(known_attributes)
            allowable_parameters = {'action': {'sort_by_node_attribute'},
                                    'node_attribute': known_attributes,
                                    'node_category': set([t for x in self.message.knowledge_graph.nodes.values() for t in x.category]),
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {float()},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }
        else:
            allowable_parameters = {'action': {'sort_by_node_attribute'},
                                    'node_attribute': {'a node attribute'},
                                    'node_category': {'a node category'},
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {'the maximum number of results to return'},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }

        # A little function to describe what this thing does
        if describe:
            # TODO: add more use cases
            brief_description = self.command_definitions['sort_by_node_attribute']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        node_params = self.parameters

        if self.check_results(message):
            return self.response

        # try to convert the max results to an int
        if 'max_results' in node_params:
            try:
                node_params['max_results'] = int(node_params['max_results'])
                assert node_params['max_results'] >= 0
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"parameter 'max_results' must be a non-negative integer")
            if self.response.status != 'OK':
                return self.response

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        if 'direction' not in node_params:
            self.response.error(
                f"Direction must be provided, allowable directions are: {list(allowable_parameters['direction'])}",
                error_code="UnknownValue")
        else:
            value = node_params['direction']
            if value in {'descending', 'd'}:
                node_params['descending'] = True
            elif value in {'ascending', 'a'}:
                node_params['descending'] = False
            else:
                self.response.error(
                    f"Supplied value {value} is not permitted. In parameter direction, allowable values are: {list(allowable_parameters['direction'])}",
                    error_code="UnknownValue")
        if 'node_attribute' not in node_params:
            self.response.error(
                f"node attribute must be provided, allowable attributes are: {list(allowable_parameters['node_attribute'])}",
                error_code="UnknownValue")
        if 'prune_kg' not in node_params:
            node_params['prune_kg'] = True
        elif node_params['prune_kg'] in {'true', 'True', 't', 'T'}:
            node_params['prune_kg'] = True
        elif node_params['prune_kg'] in {'false', 'False', 'f', 'F'}:
            node_params['prune_kg'] = False
        else:
            value = node_params['prune_kg']
            self.response.error(
                    f"Supplied value {value} is not permitted. In parameter prune_kg, allowable values are: {list(allowable_parameters['prune_kg'])}",
                    error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_Results.sort_results import SortResults
        SR = SortResults(self.response, self.message, node_params)
        response = SR.sort_by_node_attribute()
        return response


    def __limit_number_of_results(self, describe=False):
        """
        limits the number of results
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'results'):
            allowable_parameters = {'action': {'limit_number_of_results'},
                                    'max_results': {float()},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }
        else:
            allowable_parameters = {'action': {'limit_number_of_results'},
                                    'max_results': {'a non-negative integer'},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }

        # A little function to describe what this thing does
        if describe:
            # TODO: add more use cases
            brief_description = self.command_definitions['limit_number_of_results']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        params = self.parameters

        if self.check_results(message):
            return self.response


        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        # try to convert the max results to an int
        if 'max_results' in params:
            try:
                params['max_results'] = int(params['max_results'])
                assert params['max_results'] >= 0
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"parameter 'max_results' must be a non-negative integer")
            if self.response.status != 'OK':
                return self.response
        else:
            self.response.error(
                f"Max results must be provided, allowable attributes are: {list(allowable_parameters['max_results'])}",
                error_code="UnknownValue")

        if 'prune_kg' not in params:
            params['prune_kg'] = True
        elif params['prune_kg'] in {'true', 'True', 't', 'T'}:
            params['prune_kg'] = True
        elif params['prune_kg'] in {'false', 'False', 'f', 'F'}:
            params['prune_kg'] = False
        else:
            value = params['prune_kg']
            self.response.error(
                    f"Supplied value {value} is not permitted. In parameter prune_kg, allowable values are: {list(allowable_parameters['prune_kg'])}",
                    error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_Results.sort_results import SortResults
        SR = SortResults(self.response, self.message, params)
        response = SR.limit_number_of_results()
        return response

        

    def __sort_by_edge_count(self, describe=False):
        """
        sorts by results edge attribute
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'results') and hasattr(message, 'knowledge_graph') and hasattr(message.knowledge_graph, 'edges'):
            allowable_parameters = {'action': {'sort_by_edge_count'},
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {float()},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }
        else:
            allowable_parameters = {'action': {'sort_by_edge_count'},
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {'the maximum number of results to return'},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }

        # A little function to describe what this thing does
        if describe:
            # TODO: add more use cases
            brief_description = self.command_definitions['sort_by_edge_count']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        edge_params = self.parameters

        if self.check_results(message):
            return self.response

        # try to convert the max results to an int
        if 'max_results' in edge_params:
            try:
                edge_params['max_results'] = int(edge_params['max_results'])
                assert edge_params['max_results'] >= 0
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"parameter 'max_results' must be a non-negative integer")
            if self.response.status != 'OK':
                return self.response

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        if 'direction' not in edge_params:
            self.response.error(
                f"Direction must be provided, allowable directions are: {list(allowable_parameters['direction'])}",
                error_code="UnknownValue")
        else:
            value = edge_params['direction']
            if value in {'descending', 'd'}:
                edge_params['descending'] = True
            elif value in {'ascending', 'a'}:
                edge_params['descending'] = False
            else:
                self.response.error(
                    f"Supplied value {value} is not permitted. In parameter direction, allowable values are: {list(allowable_parameters['direction'])}",
                    error_code="UnknownValue")
        if 'prune_kg' not in edge_params:
            edge_params['prune_kg'] = True
        elif edge_params['prune_kg'] in {'true', 'True', 't', 'T'}:
            edge_params['prune_kg'] = True
        elif edge_params['prune_kg'] in {'false', 'False', 'f', 'F'}:
            edge_params['prune_kg'] = False
        else:
            value = edge_params['prune_kg']
            self.response.error(
                    f"Supplied value {value} is not permitted. In parameter prune_kg, allowable values are: {list(allowable_parameters['prune_kg'])}",
                    error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_Results.sort_results import SortResults
        SR = SortResults(self.response, self.message, edge_params)
        response = SR.sort_by_edge_count()
        return response

    def __sort_by_node_count(self, describe=False):
        """
        sorts by number of nodes in result
        :return:
        """
        message = self.message
        parameters = self.parameters
        # make a list of the allowable parameters (keys), and their possible values (values). Note that the action and corresponding name will always be in the allowable parameters
        if message and parameters and hasattr(message, 'results') and hasattr(message, 'knowledge_graph') and hasattr(message.knowledge_graph, 'nodes'):
            allowable_parameters = {'action': {'sort_by_node_count'},
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {float()},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }
        else:
            allowable_parameters = {'action': {'sort_by_node_count'},
                                    'direction': {'descending', 'd', 'ascending', 'a'},
                                    'max_results': {'the maximum number of results to return'},
                                    'prune_kg': {'true', 'false', 'True', 'False', 't', 'f', 'T', 'F'}
                                    }

        # A little function to describe what this thing does
        if describe:
            # TODO: add more use cases
            brief_description = self.command_definitions['sort_by_node_count']
            allowable_parameters['brief_description'] = brief_description
            return allowable_parameters

        node_params = self.parameters

        if self.check_results(message):
            return self.response

        # try to convert the max results to an int
        if 'max_results' in node_params:
            try:
                node_params['max_results'] = int(node_params['max_results'])
                assert node_params['max_results'] >= 0
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"parameter 'max_results' must be a non-negative integer")
            if self.response.status != 'OK':
                return self.response

        # Make sure only allowable parameters and values have been passed
        resp = self.check_params(allowable_parameters)
        # return if bad parameters have been passed
        if self.response.status != 'OK' or resp == -1:
            return self.response

        if 'direction' not in node_params:
            self.response.error(
                f"Direction must be provided, allowable directions are: {list(allowable_parameters['direction'])}",
                error_code="UnknownValue")
        else:
            value = node_params['direction']
            if value in {'descending', 'd'}:
                node_params['descending'] = True
            elif value in {'ascending', 'a'}:
                node_params['descending'] = False
            else:
                self.response.error(
                    f"Supplied value {value} is not permitted. In parameter direction, allowable values are: {list(allowable_parameters['direction'])}",
                    error_code="UnknownValue")
        if 'prune_kg' not in node_params:
            node_params['prune_kg'] = True
        elif node_params['prune_kg'] in {'true', 'True', 't', 'T'}:
            node_params['prune_kg'] = True
        elif node_params['prune_kg'] in {'false', 'False', 'f', 'F'}:
            node_params['prune_kg'] = False
        else:
            value = node_params['prune_kg']
            self.response.error(
                    f"Supplied value {value} is not permitted. In parameter prune_kg, allowable values are: {list(allowable_parameters['prune_kg'])}",
                    error_code="UnknownValue")
        if self.response.status != 'OK':
            return self.response

        # now do the call out to NGD
        from Filter_Results.sort_results import SortResults
        SR = SortResults(self.response, self.message, node_params)
        response = SR.sort_by_node_count()
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
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges.values())),sort_keys=True,indent=2))
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.nodes.values())), sort_keys=True, indent=2))
    # print(json.dumps(message.to_dict(), sort_keys=True, indent=2))
    # print(response.show(level=ARAXResponse.DEBUG))

    # just print off the values
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges.values())), sort_keys=True, indent=2))
    # for edge in message.knowledge_graph.edges.values():
    #    if hasattr(edge, 'attributes') and edge.attributes and len(edge.attributes) >= 1:
    #        print(edge.attributes.pop().value)
    print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges.values())), sort_keys=True, indent=2))
    print(response.show(level=ARAXResponse.DEBUG))
    vals = []
    for key, node in message.knowledge_graph.nodes.items():
        print(key)
    print(len(message.knowledge_graph.nodes))
    for edge in message.knowledge_graph.edges.values():
        if hasattr(edge, 'attributes') and edge.attributes and len(edge.attributes) >= 1:
            vals.append(edge.attributes.pop().value)
    print(sorted(vals))


if __name__ == "__main__": main()
