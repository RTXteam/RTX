#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import yaml
from datetime import datetime

from ARAX_response import ARAXResponse
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo
from ARAX_messenger import ARAXMessenger

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.message import Message
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge


class ARAXQueryGraphInterpreter:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None

        self.query_graph_templates = None
        self.query_graph_tree = None

        self.read_query_graph_templates()


    # #### Create a fresh Message object and fill with defaults
    def translate_to_araxi(self, response, describe=False):
        """
        Translate an input query_graph into ARAXi
        :return: ARAXResponse object with execution information and the DSL command set
        :rtype: ARAXResponse
        """

        #### Extract the message from the response
        message = response.envelope.message
        debug = False

        #### Ensure that query_graph_templates is ready
        if self.query_graph_templates is None:
            response.error("QueryGraph templates cannot be read from reference file", error_code="QueryGraphInterpreterMissingTemplates")
            return response

        query_graph_info = QueryGraphInfo()

        result = query_graph_info.assess(message)
        response.merge(result)
        if result.status != 'OK':
            #print(response.show(level=ARAXResponse.DEBUG))
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
                if component['has_ids'] and component['has_categories'] and component['categories_value']:
                    possible_next_steps.append( { 'content': f"ids,categories={component['categories_value']}", 'score': 10000 } )
                    possible_next_steps.append( { 'content': 'ids', 'score': 1000 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_ids']:
                    possible_next_steps.append( { 'content': 'ids', 'score': 1000 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_categories'] and component['categories_value']:
                    possible_next_steps.append( { 'content': f"categories={component['categories_value']}", 'score': 100 } )
                    possible_next_steps.append( { 'content': 'categories', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_categories']:
                    possible_next_steps.append( { 'content': 'categories', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                else:
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

            # Else it's an edge. Don't do anything with those currently
            else:
                # Go through the list of possible things it could be and those or lesser possible next steps
                if component['has_predicates'] and component['predicates_value']:
                    possible_next_steps.append( { 'content': f"predicates={component['predicates_value']}", 'score': 90 } )
                    possible_next_steps.append( { 'content': 'predicates', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                elif component['has_predicates']:
                    possible_next_steps.append( { 'content': 'predicates', 'score': 10 } )
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

                else:
                    possible_next_steps.append( { 'content': '', 'score': 0 } )

            # For each of the current tree pointers
            new_tree_pointers = []
            for tree_pointer in tree_pointers:
                if debug:
                    #print(f"    - pointer={tree_pointer}")
                    #print(f"    - pointer...")
                    #for tp_key,tp_pointer in tree_pointer['pointer'].items():
                    #    print(f"        - {tp_key} = {tp_pointer}")
                    pass

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
            # Do it in two passes in case there are overlaps in the names. Issue #1457
            new_araxi_commands = []
            tmp_araxi_commands = []
            for command in araxi_commands:
                node_index = 0
                new_command = command
                for node in query_graph_info.node_order:
                    template_id = f"n{node_index:02}"
                    temp_template_id = f"zzxxyqn{node_index:02}"
                    new_command = re.sub(template_id,temp_template_id,new_command)
                    node_index += 1

                edge_index = 0
                for edge in query_graph_info.edge_order:
                    template_id = f"e{edge_index:02}"
                    temp_template_id = f"zzxxyqe{node_index:02}"
                    new_command = re.sub(template_id,temp_template_id,new_command)
                    edge_index += 1

                tmp_araxi_commands.append(new_command)

            #### Second pass remapping the temporary names
            for command in tmp_araxi_commands:
                node_index = 0
                new_command = command
                for node in query_graph_info.node_order:
                    template_id = f"zzxxyqn{node_index:02}"
                    new_command = re.sub(template_id,node['key'],new_command)
                    node_index += 1

                edge_index = 0
                for edge in query_graph_info.edge_order:
                    template_id = f"zzxxyqe{edge_index:02}"
                    new_command = re.sub(template_id,edge['key'],new_command)
                    edge_index += 1

                new_araxi_commands.append(new_command)

            # TODO: Create the restated_question from the template
            response.data['araxi_commands'] = new_araxi_commands
            return response

        # response.error("QueryGraphInterpreter cannot interpret this QueryGraph", error_code="QueryGraphInterpreterUnsupportedGraph")

        # If we got here, then no templates matches, so try to assign a bland program and hope for the best
        response.warning("QueryGraphInterpreter cannot match this QueryGraph to a known template, just running a default template")
        response.data['araxi_commands'] = [
            'expand()',
            'resultify()',
            'filter_results(action=limit_number_of_results, max_results=500)'
        ]

        return response


    # #### Read the YAML file containing the current QueryGraph templates
    def read_query_graph_templates(self):
        """
        Read the YAML file containing the current QueryGraph templates
        :rcategory: None
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
        if self.query_graph_templates['ARAX_QG_DSL_mapping'] != 0.2:
            self.response.error(f"Incorrect version number in QueryGraphInterpreter templates file {template_file}", error_code="BadQueryGraphInterpreterTemplateFileVersion")
            self.query_graph_templates = None
            return self.response

        # We will create dict lookup table of all the template string [e.g. 'n00(ids)-e00()-n01(categories)' -> template_name]
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

def QGI_test1():

    #### Some qnode examples
    test_query_graphs = [
        [ { 'id': 'n10', 'curie': 'DOID:9281', 'category': 'disease'}, { 'id': 'n11', 'category': 'chemical_substance'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11', 'category': 'treats'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'category': 'protein'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'category': 'protein'}, { 'id': 'n12', 'category': 'chemical_substance'},
            { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'}, { 'id': 'e11', 'source_id': 'n11', 'target_id': 'n12'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281'}, { 'id': 'n11', 'category': 'chemical_substance'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'} ],
        [ { 'id': 'n10', 'curie': 'DOID:9281', 'category': 'disease'}, { 'id': 'n11', 'category': 'chemical_substance'}, { 'id': 'e10', 'source_id': 'n10', 'target_id': 'n11'} ],
    ]

    #interpreter = ARAXQueryGraphInterpreter()
    #print(json.dumps(interpreter.query_graph_tree,sort_keys=True,indent=2))
    #return

    for test_query_graph in test_query_graphs:

        #### Create a response object for each test
        response = ARAXResponse()

        #### Create a template Message
        messenger = ARAXMessenger()
        messenger.create_envelope(response)
        message = response.envelope.message

        for parameters in test_query_graph:
            if 'n' in parameters['id']:
                messenger.add_qnode(response, parameters)
                if response.status != 'OK':
                    print(response.show(level=ARAXResponse.DEBUG))
                    return response
            elif 'e' in parameters['id']:
                #print(f"++ Adding qedge with {parameters}")
                messenger.add_qedge(response, parameters)
                if response.status != 'OK':
                    print(response.show(level=ARAXResponse.DEBUG))
                    return response
            else:
                response.error(f"Unrecognized component {parameters['id']}")
                return response

        interpreter = ARAXQueryGraphInterpreter()
        interpreter.translate_to_araxi(response)
        if response.status != 'OK':
            print(response.show(level=ARAXResponse.DEBUG))
            return response

        araxi_commands = response.data['araxi_commands']
        for cmd in araxi_commands:
            print(f"  - {cmd}")

        #### Show the final result
        #print('-------------------------')
        #print(response.show(level=ARAXResponse.DEBUG))
        #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
        #sys.exit(1)


##########################################################################################

def QGI_test2():

    #### Set example query_graph
    # TRAPI 0.9.2
    input_query_graph = { "message": { "query_graph": { "nodes": [ { "id": "n1", "category": "chemical_substance" }, { "id": "n2", "curie": "UMLS:C0002395" } ], "edges": [ { "id": "e1", "predicate": "clinically_tested_approved_unknown_phase", "source_id": "n1", "target_id": "n2" } ] } } }
    # TRAPI 1.0.0
    input_query_graph = { "message": { "query_graph": { 
        "nodes": { "n1": { "category": "biolink:ChemicalEntity" }, "n2": { "id": "UMLS:C0002395" } },
        "edges": { "e1": { "predicate": "clinically_tested_approved_unknown_phase", "subject": "n1", "object": "n2" } }
        } } }
    # TRAPI 1.1.0
    input_query_graph = { "message": { "query_graph": { 
        "nodes": { "n1": { "categories": [ "biolink:ChemicalEntity" ] }, "n2": { "ids": [ "UMLS:C0002395" ] } },
        "edges": { "e1": { "predicates": [ "biolink:clinically_tested_approved_unknown_phase" ], "subject": "n1", "object": "n2" } }
        } } }

    #### Create a template Message
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    message = ARAXMessenger().from_dict(input_query_graph['message'])
    response.envelope.message.query_graph = message.query_graph

    interpreter = ARAXQueryGraphInterpreter()
    interpreter.translate_to_araxi(response)
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    araxi_commands = response.data['araxi_commands']
    for cmd in araxi_commands:
        print(f"  - {cmd}")

    #### Show the final result
    print('-------------------------')
    print(response.show(level=ARAXResponse.DEBUG))
    print(json.dumps(message.to_dict(),sort_keys=True,indent=2))


##########################################################################################

def QGI_test3():

    input_query_graph = { "message": { "query_graph": 
        {
        "nodes": {
            "n00": {
            "ids": [ "MONDO:0002715" ]
            },
            "n01": {
            "categories": [ "biolink:ChemicalEntity" ]
            },
            "n02": {
            "categories": [ "biolink:Gene" ]
            }
        },
        "edges": {
            "e00": {
            "predicates": [ "biolink:correlated_with" ],
            "subject": "n00",
            "object": "n01"
            },
            "e01": {
            "predicates": [ "biolink:related_to" ],
            "subject": "n01",
            "object": "n02"
            }
        }
        }
    } }

    #### Create a template Message
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    message = ARAXMessenger().from_dict(input_query_graph['message'])
    response.envelope.message.query_graph = message.query_graph

    interpreter = ARAXQueryGraphInterpreter()
    interpreter.translate_to_araxi(response)
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    araxi_commands = response.data['araxi_commands']
    for cmd in araxi_commands:
        print(f"  - {cmd}")

    #### Show the final result
    print('-------------------------')
    print(response.show(level=ARAXResponse.DEBUG))
    print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
    #sys.exit(1)



##########################################################################################

def QGI_test4():

    input_query_graph = { "message": { "query_graph": 
            {
            "nodes": {
                "n00": {
                "categories": [
                    "biolink:Gene"
                ],
                "is_set": False
                },
                "n01": {
                "ids": [
                    "MONDO:0018177"
                ],
                "categories": [
                    "biolink:Disease"
                ],
                "is_set": False
                }
            },
            "edges": {
                "e00": {
                "subject": "n00",
                "object": "n01",
                "exclude": False
                }
            }
            }
    } }

    #### Create a template Message
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    message = ARAXMessenger().from_dict(input_query_graph['message'])
    response.envelope.message.query_graph = message.query_graph

    interpreter = ARAXQueryGraphInterpreter()
    interpreter.translate_to_araxi(response)
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    araxi_commands = response.data['araxi_commands']
    for cmd in araxi_commands:
        print(f"  - {cmd}")

    #### Show the final result
    #print('-------------------------')
    #print(response.show(level=ARAXResponse.DEBUG))
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
    #sys.exit(1)


def QGI_test5():
    # This is to test forked/non-linear queries (currently not working properly)
    input_query_graph = {
    "message": {
        "query_graph": {
            "nodes": {
                "n0": {
                    "categories": ["biolink:Gene"]
                },
                "n1": {
                    "ids": ["CHEBI:45783"],
                    "categories": ["biolink:ChemicalEntity"]
                },
                "n2": {
                    "ids": ["MONDO:0005301"],
                    "categories": ["biolink:Disease"]
                },
                "n3": {
                    "categories": ["biolink:ChemicalEntity"]
                }
            },
            "edges": {
                "e01": {
                    "subject": "n0",
                    "object": "n1",
                    "predicates": ["biolink:related_to"]
                },
                "e02": {
                    "subject": "n0",
                    "object": "n2",
                    "predicates": ["biolink:related_to"]
                },
                "e03": {
                    "subject": "n0",
                    "object": "n3",
                    "predicates": ["biolink:related_to"]
                }
            }
        }
    }
    }


    #### Create a template Message
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    message = ARAXMessenger().from_dict(input_query_graph['message'])
    response.envelope.message.query_graph = message.query_graph

    interpreter = ARAXQueryGraphInterpreter()
    interpreter.translate_to_araxi(response)
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    araxi_commands = response.data['araxi_commands']
    for cmd in araxi_commands:
        print(f"  - {cmd}")

    #### Show the final result
    #print('-------------------------')
    #print(response.show(level=ARAXResponse.DEBUG))
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
    #sys.exit(1)

def QGI_test6():
    # This is to test a three hop query with ends pinned (should result in FET ARAXi commands), and actually run the query
    input_query_graph = {
            "message": {
                "query_graph": {
          "edges": {
            "e00": {
              "object": "n01",
              "subject": "n00"
            },
            "e01": {
              "object": "n02",
              "subject": "n01"
            },
            "e02": {
              "object": "n03",
              "subject": "n02"
            }
          },
          "nodes": {
            "n00": {
              "categories": [
                "biolink:ChemicalEntity"
              ],
              "ids": [
                "DRUGBANK:DB00150"
              ]
            },
            "n01": {
              "categories": [
                "biolink:Protein"
              ]
            },
            "n02": {
              "categories": [
                "biolink:MolecularActivity"
              ]
            },
            "n03": {
              "categories": [
                "biolink:ChemicalEntity"
              ],
              "ids": [
                "KEGG.COMPOUND:C02700"
              ]
            }
          }
        }

    }
    }


    #### Create a template Message
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    message = ARAXMessenger().from_dict(input_query_graph['message'])
    response.envelope.message.query_graph = message.query_graph

    interpreter = ARAXQueryGraphInterpreter()
    interpreter.translate_to_araxi(response)
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    araxi_commands = response.data['araxi_commands']
    for cmd in araxi_commands:
        print(f"  - {cmd}")

    #### Show the final result
    #print('-------------------------')
    #print(response.show(level=ARAXResponse.DEBUG))
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))

    #### Actually run the query
    from ARAX_query import ARAXQuery
    import ast
    araxq = ARAXQuery()
    # Run the query
    araxq.query({**input_query_graph, "operations": {"actions":araxi_commands}})
    # unpack the response
    response = araxq.response
    envelope = response.envelope
    message = envelope.message  # overrides the current message
    envelope.status = response.error_code
    envelope.description = response.message
    # return the message ID
    print(f"Returned response id: {envelope.id}")
    print('-------------------------')
    # print the whole message
    #print(json.dumps(ast.literal_eval(repr(envelope)), sort_keys=True, indent=2))
    # save message to file (since I can't get the UI working locally for some reason)
    with open('QGI_test6.json', 'w', encoding='utf-8') as f:
        json.dump(ast.literal_eval(repr(envelope)), f, ensure_ascii=False, indent=4)

def QGI_test7():
    # This is to test a three hop query with one end pinned (should result in FET ARAXi commands), and actually run the query
    input_query_graph = {
        "message": {
            "query_graph": {
                "edges": {
                    "e00": {
                        "object": "n01",
                        "subject": "n00"
                    },
                    "e01": {
                        "object": "n02",
                        "subject": "n01"
                    },
                    "e02": {
                        "object": "n03",
                        "subject": "n02"
                    }
                },
                "nodes": {
                    "n00": {
                        "categories": [
                            "biolink:ChemicalEntity"
                        ],
                        "ids": [
                            "DRUGBANK:DB00150"
                        ]
                    },
                    "n01": {
                        "categories": [
                            "biolink:Protein"
                        ]
                    },
                    "n02": {
                        "categories": [
                            "biolink:MolecularActivity"
                        ]
                    },
                    "n03": {
                        "categories": [
                            "biolink:ChemicalEntity"
                        ]
                    }
                }
            }

        }
    }

    #### Create a template Message
    response = ARAXResponse()
    messenger = ARAXMessenger()
    messenger.create_envelope(response)
    message = ARAXMessenger().from_dict(input_query_graph['message'])
    response.envelope.message.query_graph = message.query_graph

    interpreter = ARAXQueryGraphInterpreter()
    interpreter.translate_to_araxi(response)
    if response.status != 'OK':
        print(response.show(level=ARAXResponse.DEBUG))
        return response

    araxi_commands = response.data['araxi_commands']
    for cmd in araxi_commands:
        print(f"  - {cmd}")

    #### Show the final result
    # print('-------------------------')
    # print(response.show(level=ARAXResponse.DEBUG))
    # print(json.dumps(message.to_dict(),sort_keys=True,indent=2))

    #### Actually run the query
    from ARAX_query import ARAXQuery
    import ast
    araxq = ARAXQuery()
    # Run the query
    araxq.query({**input_query_graph, "operations": {"actions": araxi_commands}})
    # unpack the response
    response = araxq.response
    envelope = response.envelope
    message = envelope.message  # overrides the current message
    envelope.status = response.error_code
    envelope.description = response.message
    # return the message ID
    print(f"Returned response id: {envelope.id}")
    print('-------------------------')
    # print the whole message
    # print(json.dumps(ast.literal_eval(repr(envelope)), sort_keys=True, indent=2))
    # save message to file (since I can't get the UI working locally for some reason)
    with open('QGI_test7.json', 'w', encoding='utf-8') as f:
        json.dump(ast.literal_eval(repr(envelope)), f, ensure_ascii=False, indent=4)
##########################################################################################
def main():

    import argparse

    argparser = argparse.ArgumentParser(description='Class for parsing an incoming query graph and deciding what to do')
    argparser.add_argument('test_number', type=str, nargs='*', help='Optional test to run')
    params = argparser.parse_args()

    #print(params.test_number)
    if params.test_number[0] == '2':
        QGI_test2()
    elif params.test_number[0] == '3':
        QGI_test3()
    elif params.test_number[0] == '4':
        QGI_test4()
    elif params.test_number[0] == '5':
        QGI_test5()
    elif params.test_number[0] == '6':
        QGI_test6()
    elif params.test_number[0] == '7':
        QGI_test7()
    else:
        QGI_test1()


if __name__ == "__main__": main()
