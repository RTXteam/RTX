#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
from datetime import datetime
import numpy as np

from response import Response
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.message import Message
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction")
from KGNodeIndex import KGNodeIndex


class ARAXMessenger:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None

    def describe_me(self):
        """
        Self-documentation method for internal use that returns the available actions and what they can do
        :return: A list of allowable actions supported by this class
        :rtype: list
        """
        description_list = []
        description_list.append(self.create_message(describe=True))
        description_list.append(self.add_qnode(0,0,describe=True))
        description_list.append(self.add_qedge(0,0,describe=True))
        return description_list


    # #### Create a fresh Message object and fill with defaults
    def create_message(self, describe=False):
        """
        Creates a basic empty Message object with basic boilerplate metadata
        :return: Response object with execution information and the new message object inside the data envelope
        :rtype: Response
        """

        # Internal documentation setup
        #allowable_parameters = { 'action': { 'None' } }
        allowable_parameters = { 'dsl_command': '`create_message()`'}  # can't get this name at run-time, need to manually put it in per https://www.python.org/dev/peps/pep-3130/
        if describe:
            allowable_parameters['brief_description'] = """The `create_message` method creates a basic empty Message object with basic boilerplate metadata
            such as reasoner_id, schema_version, etc. filled in. This DSL command takes no arguments"""
            return allowable_parameters

        #### Define a default response
        response = Response()
        self.response = response

        #### Create the top-level message
        response.info("Creating an empty template ARAX Message")
        message = Message()
        self.message = message

        #### Fill it with default information
        message.id = None
        message.type = "translator_reasoner_message"
        message.reasoner_id = "ARAX"
        message.tool_version = RTXConfiguration().version
        message.schema_version = "0.9.3"
        message.message_code = "OK"
        message.code_description = "Created empty template Message"
        message.context = "https://raw.githubusercontent.com/biolink/biolink-model/master/context.jsonld"

        #### Why is this _datetime ?? FIXME
        message._datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		#### Create an empty master knowledge graph
        message.knowledge_graph = KnowledgeGraph()
        message.knowledge_graph.nodes = []
        message.knowledge_graph.edges = []

		#### Create an empty query graph
        message.query_graph = QueryGraph()
        message.query_graph.nodes = []
        message.query_graph.edges = []

        #### Create empty results
        message.results = []
        message.n_results = 0

        #### Return the response
        response.data['message'] = message
        return response


    # #### Add a new QNode
    def add_qnode(self, message, input_parameters, describe=False):
        """
        Adds a new QNode object to the QueryGraph inside the Message object
        :return: Response object with execution information
        :rtype: Response
        """

        # #### Internal documentation setup
        allowable_parameters = {
            'id': { 'Any string that is unique among all QNode id fields, with recommended format n00, n01, n02, etc.'},
            'curie': { 'Any compact URI (CURIE) (e.g. DOID:9281) (May also be a list like [UniProtKB:P12345,UniProtKB:Q54321])'},
            'name': { 'Any name of a bioentity that will be resolved into a CURIE if possible or result in an error if not (e.g. hypertension, insulin)'},
            'type': { 'Any valid Translator bioentity type (e.g. protein, chemical_substance, disease)'},
            'is_set': { 'If set to true, this QNode represents a set of nodes that are all in common between the two other linked QNodes'},
            }
        if describe:
            allowable_parameters['dsl_command'] = '`add_qnode()`'  # can't get this name at run-time, need to manually put it in per https://www.python.org/dev/peps/pep-3130/
            allowable_parameters['brief_description'] = """The `add_qnode` method adds an additional QNode to the QueryGraph in the Message object. Currently
                when a curie or name is specified, this method will only return success if a matching node is found in the KG1/KG2 KGNodeIndex."""
            return allowable_parameters

        #### Define a default response
        response = Response()
        self.response = response
        self.message = message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'id': None,
            'curie': None,
            'name': None,
            'type': None,
            'is_set': None,
        }

        #### Loop through the input_parameters and override the defaults and make sure they are allowed
        for key,value in input_parameters.items():
            if key not in parameters:
                response.error(f"Supplied parameter {key} is not permitted", error_code="UnknownParameter")
            else:
                parameters[key] = value
        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters


        #### Now apply the filters. Order of operations is probably quite important
        #### Scalar value filters probably come first like minimum_confidence, then complex logic filters
        #### based on edge or node properties, and then finally maximum_results
        response.info(f"Adding a QueryNode to Message with parameters {parameters}")

        #### Make sure there's a query_graph already here
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.nodes is None:
            message.query_graph.nodes = []

        #### Set up the KGNodeIndex
        kgNodeIndex = KGNodeIndex()

        # Create the QNode and set the id
        qnode = QNode()
        if parameters['id'] is not None:
            id = parameters['id']
        else:
            id = self.__get_next_free_node_id()
        qnode.id = id

        # Set the is_set parameter to what the user selected
        if parameters['is_set'] is not None:
            qnode.is_set = (parameters['is_set'].lower() == 'true')

        #### If the CURIE is specified, try to find that
        if parameters['curie'] is not None:

            # If the curie is a scalar then treat it here as a list of one
            if isinstance(parameters['curie'], str):
                curie_list = [ parameters['curie'] ]
                is_curie_a_list = False
                if parameters['is_set'] is not None and qnode.is_set is True:
                    response.error(f"Specified CURIE '{parameters['curie']}' is a scalar, but is_set=true, which doesn't make sense", error_code="CurieScalarButIsSetTrue")
                    return response

            # Or else set it up as a list
            elif isinstance(parameters['curie'], list):
                curie_list = parameters['curie']
                is_curie_a_list = True
                qnode.curie = []
                if parameters['is_set'] is None:
                    response.warning(f"Specified CURIE '{parameters['curie']}' is a list, but is_set was not set to true. It must be true in this context, so automatically setting to true. Avoid this warning by explictly setting to true.")
                    qnode.is_set = True
                else:
                    if qnode.is_set == False:
                        response.warning(f"Specified CURIE '{parameters['curie']}' is a list, but is_set=false, which doesn't make sense, so automatically setting to true. Avoid this warning by explictly setting to true.")
                        qnode.is_set = True

            # Or if it's neither a list or a string, then error out. This cannot be handled at present
            else:
                response.error(f"Specified CURIE '{parameters['curie']}' is neither a string nor a list. This cannot to handled", error_code="CurieNotListOrScalar")
                return response

            # Loop over the available curies and create the list
            for curie in curie_list:
                response.debug(f"Looking up CURIE {curie} in KgNodeIndex")
                nodes = kgNodeIndex.get_curies_and_types(curie, kg_name='KG2')

                # If nothing was found, log an error, but don't bail out yet. Check them all in case there are multiple problems before returning with error
                if len(nodes) == 0:
                    response.error(f"A node with CURIE {parameters['curie']} is not in our knowledge graph", error_code="UnknownCURIE")
                else:

                    # FIXME. This is just always taking the first result. This could cause problems for CURIEs with multiple types. Is that possible?
                    qnode.type = nodes[0]['type']

                    # Either append or set the found curie
                    if is_curie_a_list:
                        qnode.curie.append(nodes[0]['curie'])
                    else:
                        qnode.curie = nodes[0]['curie']

            message.query_graph.nodes.append(qnode)
            return response

        #### If the name is specified, try to find that
        if parameters['name'] is not None:
            response.debug(f"Looking up CURIE {parameters['name']} in KgNodeIndex")
            nodes = kgNodeIndex.get_curies_and_types(parameters['name'])
            if len(nodes) == 0:
                nodes = kgNodeIndex.get_curies_and_types(parameters['name'], kg_name='KG2')
                if len(nodes) == 0:
                    response.error(f"A node with name '{parameters['name']}'' is not in our knowledge graph", error_code="UnknownCURIE")
                    return response
            qnode.curie = nodes[0]['curie']
            qnode.type = nodes[0]['type']
            message.query_graph.nodes.append(qnode)
            return response

        #### If the type is specified, just add that type. There should be checking that it is legal. FIXME
        if parameters['type'] is not None:
            qnode.type = parameters['type']
            if parameters['is_set'] is not None:
                qnode.is_set = (parameters['is_set'].lower() == 'true')
            message.query_graph.nodes.append(qnode)
            return response

        #### If we get here, it means that all three main parameters are null. Just a generic node with no type or anything. This is okay.
        message.query_graph.nodes.append(qnode)
        return response


    #### Get the next free node id like nXX where XX is a zero-padded integer starting with 00
    def __get_next_free_node_id(self):

        #### Set up local references to the message and verify the query_graph nodes
        message = self.message
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.nodes is None:
            message.query_graph.nodes = []
        qnodes = message.query_graph.nodes

        #### Loop over the nodes making a dict of the ids
        ids = {}
        for qnode in qnodes:
            id = qnode.id
            ids[id] = 1

        #### Find the first unused id
        index = 0
        while 1:
            pad = '0'
            if index > 9:
                pad = ''
            potential_node_id = f"n{pad}{str(index)}"
            if potential_node_id not in ids:
                return potential_node_id
            index += 1


    #### Add a new QEdge
    def add_qedge(self, message, input_parameters, describe=False):
        """
        Adds a new QEdge object to the QueryGraph inside the Message object
        :return: Response object with execution information
        :rtype: Response
        """

        # #### Internal documentation setup
        allowable_parameters = {
            'id': { 'Any string that is unique among all QEdge id fields, with recommended format e00, e01, e02, etc.'},
            'source_id': { 'id of the source QNode already present in the QueryGraph (e.g. n01, n02)'},
            'target_id': { 'id of the target QNode already present in the QueryGraph (e.g. n01, n02)'},
            'type': { 'Any valid Translator/BioLink relationship type (e.g. physically_interacts_with, participates_in)'},
            }
        if describe:
            #allowable_parameters['action'] = { 'None' }
            #allowable_parameters = dict()
            allowable_parameters['dsl_command'] = '`add_qedge()`'  # can't get this name at run-time, need to manually put it in per https://www.python.org/dev/peps/pep-3130/
            allowable_parameters['brief_description'] = """The `add_qedge` method adds an additional QEdge to the QueryGraph in the Message object. Currently
                source_id and target_id QNodes must already be present in the QueryGraph. The specified type is not currently checked that it is a
                valid Translator/BioLink relationship type, but it should be."""
            return allowable_parameters


        #### Define a default response
        response = Response()
        self.response = response
        self.message = message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'id': None,
            'source_id': None,
            'target_id': None,
            'type': None,
        }

        #### Loop through the input_parameters and override the defaults and make sure they are allowed
        for key,value in input_parameters.items():
            if key not in parameters:
                response.error(f"Supplied parameter {key} is not permitted", error_code="UnknownParameter")
            else:
                parameters[key] = value
        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters


        #### Now apply the filters. Order of operations is probably quite important
        #### Scalar value filters probably come first like minimum_confidence, then complex logic filters
        #### based on edge or node properties, and then finally maximum_results
        response.info(f"Adding a QueryEdge to Message with parameters {parameters}")

        #### Make sure there's a query_graph already here
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.edges is None:
            message.query_graph.edges = []

        #### Create a QEdge
        qedge = QEdge()
        if parameters['id'] is not None:
            id = parameters['id']
        else:
            id = self.__get_next_free_edge_id()
        qedge.id = id

        #### Get the list of available node_ids
        qnodes = message.query_graph.nodes
        ids = {}
        for qnode in qnodes:
            id = qnode.id
            ids[id] = 1

        #### Add the source_id
        if parameters['source_id'] is not None:
            if parameters['source_id'] not in ids:
                response.error(f"While trying to add QEdge, there is no QNode with id {parameters['source_id']}", error_code="UnknownSourceId")
                return response
            qedge.source_id = parameters['source_id']
        else:
            response.error(f"While trying to add QEdge, source_id is a required parameter", error_code="MissingSourceId")
            return response

        #### Add the target_id
        if parameters['target_id'] is not None:
            if parameters['target_id'] not in ids:
                response.error(f"While trying to add QEdge, there is no QNode with id {parameters['target_id']}", error_code="UnknownTargetId")
                return response
            qedge.target_id = parameters['target_id']
        else:
            response.error(f"While trying to add QEdge, target_id is a required parameter", error_code="MissingTargetId")
            return response

        #### Add the type if any. Need to verify it's an allowed type. FIXME
        if parameters['type'] is not None:
            qedge.type = parameters['type']

        #### Add it to the query_graph edge list
        message.query_graph.edges.append(qedge)

        #### Return the response
        return response


    #### Get the next free edge id like eXX where XX is a zero-padded integer starting with 00
    def __get_next_free_edge_id(self):

        #### Set up local references to the message and verify the query_graph nodes
        message = self.message
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.edges is None:
            message.query_graph.edges = []
        qedges = message.query_graph.edges

        #### Loop over the nodes making a dict of the ids
        ids = {}
        for qedge in qedges:
            id = qedge.id
            ids[id] = 1

        #### Find the first unused id
        index = 0
        while 1:
            pad = '0'
            if index > 9:
                pad = ''
            potential_edge_id = f"e{pad}{str(index)}"
            if potential_edge_id not in ids:
                return potential_edge_id
            index += 1


    #### Reassign QNode CURIEs to KG1 space
    def reassign_curies(self, message, input_parameters, describe=False):
        """
        Reassigns CURIEs to the target Knowledge Provider
        :param message: Translator standard Message object
        :type message: Message
        :param input_parameters: Dict of input parameters to control the method
        :type input_parameters: Message
        :return: Response object with execution information
        :rtype: Response
        """

        # #### Internal documentation setup
        allowable_parameters = {
            'knowledge_provider': { 'Name of the Knowledge Provider CURIE space to map to. Default=KG1. Also currently supported KG2' },
            'mismap_result': { 'Desired action when mapping fails: ERROR or WARNING. Default is ERROR'},
            }
        if describe:
            allowable_parameters['dsl_command'] = '`reassign_curies()`'  # can't get this name at run-time, need to manually put it in per https://www.python.org/dev/peps/pep-3130/
            allowable_parameters['brief_description'] = """The `reassign_curies` method reassigns all the CURIEs in the Message QueryGraph to the specified
                knowledge provider. Allowed values are KG1 or KG2. Default is KG1 if not specified."""
            return allowable_parameters

        #### Define a default response
        response = Response()
        self.response = response
        self.message = message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = {
            'knowledge_provider': 'KG1',
            'mismap_result': 'ERROR',
        }

        #### Loop through the input_parameters and override the defaults and make sure they are allowed
        for key,value in input_parameters.items():
            if key not in parameters:
                response.error(f"Supplied parameter {key} is not permitted", error_code="UnknownParameter")
            else:
                parameters[key] = value
        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters

        # Check that the knowledge_provider is valid:
        if parameters['knowledge_provider'] != 'KG1' and parameters['knowledge_provider'] != 'KG2':
            response.error(f"Specified knowledge provider must be 'KG1' or 'KG2', not '{parameters['knowledge_provider']}'", error_code="UnknownKP")
            return response

        #### Now try to assign the CURIEs
        response.info(f"Reassigning the CURIEs in QueryGraph to {parameters['knowledge_provider']} space")

        #### Make sure there's a query_graph already here
        if message.query_graph is None:
            message.query_graph = QueryGraph()
            message.query_graph.nodes = []
            message.query_graph.edges = []
        if message.query_graph.nodes is None:
            message.query_graph.nodes = []

        #### Set up the KGNodeIndex
        kgNodeIndex = KGNodeIndex()

        # Loops through the QueryGraph nodes and adjust them
        for qnode in message.query_graph.nodes:

            # If the CURIE is None, then there's nothing to do
            curie = qnode.curie
            if curie is None:
                continue

            # Map the CURIE to the desired Knowledge Provider
            if parameters['knowledge_provider'] == 'KG1':
                if kgNodeIndex.is_curie_present(curie) is True:
                    mapped_curies = [ curie ]
                else:
                    mapped_curies = kgNodeIndex.get_KG1_curies(curie)
            elif parameters['knowledge_provider'] == 'KG2':
                if kgNodeIndex.is_curie_present(curie, kg_name='KG2'):
                    mapped_curies = [ curie ]
                else:
                    mapped_curies = kgNodeIndex.get_curies_and_types(curie, kg_name='KG2')
            else:
                response.error(f"Specified knowledge provider must be 'KG1' or 'KG2', not '{parameters['knowledge_provider']}'", error_code="UnknownKP")
                return response

            # Try to find a new CURIE
            new_curie = None
            if len(mapped_curies) == 0:
                if parameters['mismap_result'] == 'WARNING':
                    response.warning(f"Did not find a mapping for {curie} to KP '{parameters['knowledge_provider']}'. Leaving as is")
                else:
                    response.error(f"Did not find a mapping for {curie} to KP '{parameters['knowledge_provider']}'. This is an error")
            elif len(mapped_curies) == 1:
                new_curie = mapped_curies[0]
            else:
                original_curie_is_fine = False
                for potential_curie in mapped_curies:
                    if potential_curie == curie:
                        original_curie_is_fine = True
                if original_curie_is_fine:
                    new_curie = curie
                else:
                    new_curie = mapped_curies[0]
                    response.warning(f"There are multiple possible CURIEs in KP '{parameters['knowledge_provider']}'. Selecting the first one {new_curie}")

            # If there's no CURIE, then nothing to do
            if new_curie is None:
                pass
            # If it's the same
            elif new_curie == curie:
                response.debug(f"CURIE {curie} is fine for KP '{parameters['knowledge_provider']}'")
            else:
                response.info(f"Remapping CURIE {curie} to {new_curie} for KP '{parameters['knowledge_provider']}'")

        #### Return the response
        return response


    #### Early experimental code to re-rank results
    def rank_results(self, message, response=None):

        #### Define a default response
        if response is None:
            if self.response is None:
                response = Response()
            else:
                response = self.response
        else:
            self.response = response
        self.message = message

        #### Determine the query_graph info
        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(message)
        #response.merge(result)
        #if result.status != 'OK':
        #    print(response.show(level=Response.DEBUG))
        #    return response

        #### Create an index of edges in the knowledge_graph and collect some min,max stats
        kg_edges = {}
        score_stats = {}
        for edge in message.knowledge_graph.edges:
            kg_edges[edge.id] = edge
            if edge.edge_attributes is not None:
                for edge_attribute in edge.edge_attributes:
                    for attribute_name in [ 'probability', 'ngd', 'jaccard_index', 'probability_drug_treats' ]:
                        if edge_attribute.name == attribute_name:
                            if attribute_name not in score_stats:
                                score_stats[attribute_name] = { 'minimum': -9999, 'maximum': -9999 }
                            value = float(edge_attribute.value)
                            if np.isinf(value): value = 9999
                            if score_stats[attribute_name]['minimum'] == -9999 or value < score_stats[attribute_name]['minimum']:
                                score_stats[attribute_name]['minimum'] = value
                            if score_stats[attribute_name]['maximum'] == -9999 or value > score_stats[attribute_name]['maximum']:
                                score_stats[attribute_name]['maximum'] = value
        response.info(f"Summary of available edge metrics: {score_stats}")

        # Iterate through the results
        i_result = 0
        for result in message.results:
            #response.debug(f"Metrics for result {i_result}  {result.essence}: ")
            score = 1.0
            best_probability = 0.0
            for edge in result.edge_bindings:
                kg_edge_id = edge.kg_id
                buf = ''
                if kg_edges[kg_edge_id].confidence is not None:
                    buf += f" confidence={kg_edges[kg_edge_id].confidence}"
                    score *= float(kg_edges[kg_edge_id].confidence)
                if kg_edges[kg_edge_id].edge_attributes is not None:
                    for edge_attribute in kg_edges[kg_edge_id].edge_attributes:
                        if edge_attribute.name == 'probability':
                            value = float(edge_attribute.value)
                            buf += f" probability={edge_attribute.value}"
                            if value > best_probability:
                                best_probability = value
                        #if edge_attribute.name == 'probability_drug_treats':               # this is already put in confidence
                        #    buf += f" probability_drug_treats={edge_attribute.value}"
                        #    score *= value
                        if edge_attribute.name == 'ngd':
                            ngd = float(edge_attribute.value)
                            if np.isinf(ngd): ngd = 10.0
                            buf += f" ngd={ngd}"
                            factor = 1 - ( ngd - 0.3) * 0.6
                            if factor < 0.01: factor = 0.01
                            if factor > 1: factor = 1.0
                            buf += f" ngd_factor={factor}"
                            score *= factor
                        if edge_attribute.name == 'jaccard_index':
                            jaccard = float(edge_attribute.value)
                            if np.isinf(jaccard): jaccard = 0.01
                            factor = jaccard / score_stats['jaccard_index']['maximum'] * 0.9
                            buf += f" jaccard={jaccard}, factor={factor}"
                            score *= factor
                #response.debug(f"  - {kg_edge_id}  {buf}")

            # #### If there was a best_probability recorded, then multiply times the running score
            if best_probability > 0.0:
                score *= best_probability

            # #### Make all scores at least 0.01. This is all way low anyway, but let's not have anything that rounds to zero
            if score < 0.01:
                score += 0.01

            #### Keep only 3 digits after the decimal 
            score = int(score * 1000 + 0.5) / 1000.0

            #response.debug(f"  ---> final score={score}")
            result.confidence = score
            result.row_data = [ score, result.essence, result.essence_type ]
            i_result += 1

        #### Add table columns name
        message.table_column_names = [ 'confidence', 'essence', 'essence_type' ]

        #### Re-sort the final results
        message.results.sort(key=lambda result: result.confidence, reverse=True)



    #### Convert a Message as a dict to a Message as objects
    def from_dict(self, message):

        if str(message.__class__) != "<class 'swagger_server.models.message.Message'>":
            message = Message().from_dict(message)
        message.query_graph = QueryGraph().from_dict(message.query_graph)
        message.knowledge_graph = KnowledgeGraph().from_dict(message.knowledge_graph)
        #new_nodes = []
        #for qnode in message.query_graph.nodes:
        #    print(type(qnode))
        #    new_nodes.append(QNode().from_dict(qnode))
        #message.query_graph.nodes = new_nodes
        #for qedge in message.query_graph.edges:
        #    new_edges.append(QEdge().from_dict(qedge))
        #message.query_graph.edges = new_edges

        if message.results is not None:
            for result in message.results:
                if result.result_graph is not None:
                    #eprint(str(result.result_graph.__class__))
                    if str(result.result_graph.__class__) != "<class 'swagger_server.models.knowledge_graph.KnowledgeGraph'>":
                        result.result_graph = KnowledgeGraph().from_dict(result.result_graph)

        return message



##########################################################################################
def main():

    #### Create a response object
    response = Response()

    #### Create a default ARAX Message
    messenger = ARAXMessenger()
    result = messenger.create_message()
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    message = messenger.message

    #### Some qnode examples
    parameters_sets = [
#        { 'curie': 'DOID:9281'},
        { 'curie': 'Orphanet:673'},
        { 'name': 'acetaminophen'},
        { 'curie': 'NCIT:C198'},
        { 'curie': 'CUI:C4710278'},
        { 'type': 'protein', 'id': 'n10'},
        { 'curie': ['UniProtKB:P14136','UniProtKB:P35579'] },
        { 'curie': ['UniProtKB:P14136','UniProtKB:P35579'], 'is_set': 'false' },
    ]

    for parameter in parameters_sets:
        #### Add a QNode
        result = messenger.add_qnode(message, parameter)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    #### Some qedge examples
    parameters_sets = [
        { 'source_id': 'n00', 'target_id': 'n01' },
        { 'source_id': 'n01', 'target_id': 'n10', 'type': 'treats' },
   ]

    for parameter in parameters_sets:
        #### Add a QEdge
        result = messenger.add_qedge(message, parameter)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    if 0:
        result = messenger.reassign_curies(message, { 'knowledge_provider': 'KG1', 'mismap_result': 'WARNING'} )
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    #### Show the final result
    print(response.show(level=Response.DEBUG))
    print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
