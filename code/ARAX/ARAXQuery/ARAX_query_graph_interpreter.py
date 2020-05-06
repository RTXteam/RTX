#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import yaml
from datetime import datetime

from response import Response
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo
from ARAX_messenger import ARAXMessenger

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.message import Message
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge


class ARAXQueryGraphInterpreter:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None

        self.query_graph_templates = None
        self.read_query_graph_templates()


    # #### Create a fresh Message object and fill with defaults
    def translate_to_araxi(self, message, describe=False):
        """
        Translate an input query_graph into ARAXi
        :return: Response object with execution information and the DSL command set
        :rtype: Response
        """

        #### Define a default response
        response = Response()
        self.response = response

        query_graph_info = QueryGraphInfo()

        result = query_graph_info.assess(message)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

        query_graph_template = query_graph_info.query_graph_template
        if query_graph_template in self.query_graph_templates['template_strings']:
            template = self.query_graph_templates['template_strings'][query_graph_template]
            araxi_commands = self.query_graph_templates['templates'][template]['DSL']

            # Need to remap the theoretical node and edge ids into the actual ones
            new_araxi_commands = []
            for command in araxi_commands:
                node_index = 0
                new_command = command
                for node in query_graph_info.node_order:
                    template_id = f"n{node_index:02}"
                    new_command = re.sub(template_id,node['id'],new_command)
                    node_index += 1

                edge_index = 0
                for edge in query_graph_info.edge_order:
                    template_id = f"e{edge_index:02}"
                    new_command = re.sub(template_id,edge['id'],new_command)
                    edge_index += 1

                new_araxi_commands.append(new_command)

            # TODO: Create the restated_question from the template
            response.data['araxi_commands'] = new_araxi_commands

        else:
            self.response.error("QueryGraphInterpreter cannot interpret this QueryGraph", error_code="QueryGraphInterpreterUnsupportedGraph")
            return response

        return response


    # #### Read the YAML file containing the current QueryGraph templates
    def read_query_graph_templates(self):
        """
        Read the YAML file containing the current QueryGraph templates
        :rtype: None
        """

        # The template file is stored right next to this code
        template_file = os.path.dirname(os.path.abspath(__file__))+"/ARAX_query_graph_interpreter_templates.yaml"

        # If the template file is not found, record an error and return
        if not os.path.exists(template_file):
            self.response.error("QueryGraphInterpreter templates file is missing", error_code="QueryGraphInterpreterTemplateMissing")
            return self.response

        # Open the file and try to load it
        with open(template_file, 'r') as stream:
            try:
                self.query_graph_templates = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.response.error(f"Error parsing YAML file template_file: {exc}", error_code="CannotParseQueryGraphInterpreterTemplate")
                return self.response

        # Make sure the version is as expected
        if 'ARAX_QG_DSL_mapping' not in self.query_graph_templates:
            self.response.error(f"Missing version number in QueryGraphInterpreter templates file {template_file}", error_code="MissingQueryGraphInterpreterTemplateFileVersion")
            return self.response
        if self.query_graph_templates['ARAX_QG_DSL_mapping'] != 0.1:
            self.response.error(f"Incorrect version number in QueryGraphInterpreter templates file {template_file}", error_code="BadQueryGraphInterpreterTemplateFileVersion")
            return self.response

        # Create dict lookup table of all the template string [e.g. 'n00(curie)-e00()-n01(type)' -> template_name]
        self.query_graph_templates['template_strings'] = {}
        for template_name,template in self.query_graph_templates['templates'].items():
            i = 0
            template_string = ''
            for component in template['template']:
                if i > 0:
                    template_string += '-'
                template_string += component
                i += 1
            self.query_graph_templates['template_strings'][template_string] = template_name


##########################################################################################
def main():

    #### Create a response object
    response = Response()

    #### Some qnode examples
    test_query_graphs = [
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'type': 'protein'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'type': 'protein'}, { 'id': 'n12', 'type': 'drug'},
            { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'}, { 'id': 'e11', 'source_id': 'n11', 'target_id': 'n12'} ],
    ]

    for test_query_graph in test_query_graphs:

        #### Create a template Message
        messenger = ARAXMessenger()
        result = messenger.create_message()
        response.merge(result)
        message = messenger.message

        for parameters in test_query_graph:
            if 'n' in parameters['id']:
                result = messenger.add_qnode(message, parameters)
                response.merge(result)
                if result.status != 'OK':
                    print(response.show(level=Response.DEBUG))
                    return response
            elif 'e' in parameters['id']:
                result = messenger.add_qedge(message, parameters)
                response.merge(result)
                if result.status != 'OK':
                    print(response.show(level=Response.DEBUG))
                    return response
            else:
                response.error(f"Unrecognized type {parameters['id']}")
                return response

        interpreter = ARAXQueryGraphInterpreter()
        result = interpreter.translate_to_araxi(message)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

        araxi_commands = result.data['araxi_commands']
        print(araxi_commands)

        #### Show the final result
        print('-------------------------')
        print(response.show(level=Response.DEBUG))
        #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))


if __name__ == "__main__": main()
