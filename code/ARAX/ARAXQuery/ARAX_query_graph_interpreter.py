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
        self.response = Response()
        self.message = None
        self.parameters = None

        self.query_graph_templates = None
        self.query_graph_tree = None

        self.read_query_graph_templates()


    # #### Create a fresh Message object and fill with defaults
    def translate_to_araxi(self, message, describe=False):
        """
        Translate an input query_graph into ARAXi
        :return: Response object with execution information and the DSL command set
        :rtype: Response
        """

        #### Get a default response
        response = self.response
        debug = False

        #### Ensure that query_graph_templates is ready
        if self.query_graph_templates is None:
            response.error("QueryGraph templates cannot be read from reference file", error_code="QueryGraphInterpreterMissingTemplates")
            return response

        query_graph_info = QueryGraphInfo()

        result = query_graph_info.assess(message)
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

        query_graph_template = query_graph_info.query_graph_templates['detailed']
        #print(json.dumps(query_graph_template,sort_keys=True,indent=2))

        # Check the number of nodes since the tree is based on the number of nodes
        n_nodes = query_graph_template['n_nodes']
        if n_nodes not in self.query_graph_tree['n_nodes']:
            response.error("QueryGraphInterpreter finds more nodes than supported in this QueryGraph", error_code="QueryGraphInterpreterUnsupportedGraph")
            return response

        # Set up a list of tree pointers with both a pointer to the next dict as well as the running score total
        # There are potentially multiple matches to track especially since we permit less specific matches
        tree_pointers = [ { 'pointer': self.query_graph_tree['n_nodes'][n_nodes], 'score': 0 } ]

        # Now look over each component looking for matches
        possible_next_steps = []
        for component in query_graph_template['components']:
            if debug: print(f"- Component is {component}")
            possible_next_steps = []

            #### If the component is a node, then score it
            if component['component_type'] == 'node':

                # Go through the list of possible things it could be and those or lesser possible next steps
                if component['has_curie'] and component['has_type'] and component['type_value']:
                    possible_next_steps.append( { 'content': f"curie,type={component['type_value']}", 'score': 10000 } )
                    possible_next_steps.append( { 'content': 'curie', 'score': 1000 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_curie']:
                    possible_next_steps.append( { 'content': 'curie', 'score': 1000 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_type'] and component['type_value']:
                    possible_next_steps.append( { 'content': f"type={component['type_value']}", 'score': 100 } )
                    possible_next_steps.append( { 'content': 'type', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_type']:
                    possible_next_steps.append( { 'content': 'type', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                else:
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

            # Else it's an edge. Don't do anything with those currently
            else:
                # Go through the list of possible things it could be and those or lesser possible next steps
                if component['has_type'] and component['type_value']:
                    possible_next_steps.append( { 'content': f"type={component['type_value']}", 'score': 90 } )
                    possible_next_steps.append( { 'content': 'type', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_type']:
                    possible_next_steps.append( { 'content': 'type', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                else:
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

            # For each of the current tree pointers
            new_tree_pointers = []
            for tree_pointer in tree_pointers:
                if debug: print(f"    - pointer={tree_pointer}")

                # Consider each of the new possibilities
                for possible_next_step in possible_next_steps:
                    component_string = f"{component['component_id']}({possible_next_step['content']})"
                    if debug: print(f"    - component_string={component_string}")

                    # If this component is a possible next step in the tree, then add the next step to new_tree_pointers
                    if component_string in tree_pointer['pointer']:
                        if debug: print(f"      - Found this component with score {possible_next_step['score']}")
                        new_tree_pointers.append( { 'pointer': tree_pointer['pointer'][component_string], 'score': tree_pointer['score'] + possible_next_step['score'] })
                        #tree_pointer = tree_pointer[component_string]

            # When we're done, reset the surviving tree pointers
            tree_pointers = new_tree_pointers

        # Now determine the best scoring match and assign that one
        query_graph_template_name = '??'
        best_score = -1
        for tree_pointer in tree_pointers:
            if 'name' in tree_pointer['pointer']:
                if debug: print(f"==> Found template is {tree_pointer['pointer']['name']} with score {tree_pointer['score']}")
                if tree_pointer['score'] > best_score:
                    query_graph_template_name = tree_pointer['pointer']['name']
                    best_score = tree_pointer['score']


        # If the final best template name is a real one in templates, then get the ARAXI for it
        if query_graph_template_name in self.query_graph_templates['templates']:
            araxi_commands = self.query_graph_templates['templates'][query_graph_template_name]['DSL']

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
            return response

        response.error("QueryGraphInterpreter cannot interpret this QueryGraph", error_code="QueryGraphInterpreterUnsupportedGraph")
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
            self.query_graph_templates = None
            return self.response
        if self.query_graph_templates['ARAX_QG_DSL_mapping'] != 0.1:
            self.response.error(f"Incorrect version number in QueryGraphInterpreter templates file {template_file}", error_code="BadQueryGraphInterpreterTemplateFileVersion")
            self.query_graph_templates = None
            return self.response

        # We will create dict lookup table of all the template string [e.g. 'n00(curie)-e00()-n01(type)' -> template_name]
        self.query_graph_templates['template_strings'] = {}

        # We will also create dict tree of all templates organized by the number of nodes and then by each component
        self.query_graph_tree = { 'n_nodes': {} }

        # Loop over all the templates in the YAML file
        for template_name,template in self.query_graph_templates['templates'].items():

            # Initialize an empty string to build the template in 
            template_string = ''
            i = 0

            # Determine the number of components and nodes in this template and start building a tree
            n_components = len(template['template'])
            n_nodes = int( ( n_components + 1 ) / 2 )
            if n_nodes not in self.query_graph_tree['n_nodes']:
                self.query_graph_tree['n_nodes'][n_nodes] = {}

            # previous_dict will contain the last place we left off in the tree
            previous_dict = self.query_graph_tree['n_nodes'][n_nodes]

            # Loop over each component building the tree
            for component in template['template']:

                # If this branch of the tree doesn't exist yet, add it
                if component not in previous_dict:
                    previous_dict[component] = {}

                # This location will be the next starting point
                previous_dict = previous_dict[component]

                # Append to the end of the template string
                if i > 0:
                    template_string += '-'
                template_string += component

                # If this is the last component, then attach the name of this template at the end
                i += 1
                if i == n_components:
                    previous_dict['name'] = template_name

            # Store the created template string and name
            self.query_graph_templates['template_strings'][template_string] = template_name

            # Cruft
                #match = re.match(r'([a-z]\d\d)\((.*)\)',component)
#                    parameters = match.group(2)
#                    if match.group(1).startswith('n'):
#                        print(f"  This is a node with parameters '{parameters}'")
#                        if parameters > '':
#                            parts = parameters.split(',')
#                            for part in parts:



##########################################################################################
def main():

    #### Some qnode examples
    test_query_graphs = [
        [ { 'id': 'n10', 'curie': 'DOID:9281', 'type': 'disease'}, { 'id': 'n11', 'type': 'chemical_substance'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11', 'type': 'treats'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'type': 'protein'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'type': 'protein'}, { 'id': 'n12', 'type': 'chemical_substance'},
            { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'}, { 'id': 'e11', 'source_id': 'n11', 'target_id': 'n12'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'type': 'chemical_substance'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281', 'type': 'disease'}, { 'id': 'n11', 'type': 'chemical_substance'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'} ],
    ]

    #interpreter = ARAXQueryGraphInterpreter()
    #print(json.dumps(interpreter.query_graph_tree,sort_keys=True,indent=2))
    #return

    for test_query_graph in test_query_graphs:

        #### Create a response object for each test
        response = Response()

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
                #print(f"++ Adding qedge with {parameters}")
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
        #print('-------------------------')
        #print(response.show(level=Response.DEBUG))
        #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
        #sys.exit(1)


if __name__ == "__main__": main()
