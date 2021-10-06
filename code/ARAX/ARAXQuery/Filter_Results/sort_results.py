# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import traceback
import numpy as np
import math

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/kg-construction/")
from NormGoogleDistance import NormGoogleDistance as NGD


def sort_index(lst, desc):
    #modified from http://stackoverflow.com/questions/3382352/equivalent-of-numpy-argsort-in-basic-python/, answer by the user unutbu
    indexes = sorted(range(len(lst)), key=lst.__getitem__, reverse = desc)
    return indexes

class SortResults:

    #### Constructor
    def __init__(self, response, message, params):
        self.response = response
        self.message = message
        self.parameters = params

    def limit_number_of_results(self):
        """
        limit number of results
        :return: response
        """
        self.response.debug(f"Limiting Number of Results")
        self.response.info(f"Filtering excess results above max result limit")
        params = self.parameters
        try:
            n = params['max_results']
            self.message.results = self.message.results[:n]
            if params['prune_kg']:
                self.prune_kg()
            self.message.n_results = n
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code = error_type.__name__)
            self.response.error(f"Something went wrong when limiting results")
        else:
            self.response.info(f"Successfully limited the number of results")

        return self.response

    def sort_by_edge_attribute(self):
        """
        Iterate over all the results and sort by the edge attribute provided.
        :return: response
        """
        self.response.debug(f"Sorting Results")
        self.response.info(f"Sorting the results by edge attribute")
        params = self.parameters
        try:
            edge_values = {}
            # iterate over the edges find the attribute values
            for key, edge in self.message.knowledge_graph.edges.items():  # iterate over the edges
                edge_relation = None
                edge_values[key] = {'value': None, 'relation': None}
                if 'qedge_keys' in params and params['qedge_keys'] is not None and len(params['qedge_keys']) > 0:
                    if key not in params['qedge_keys']:
                        continue
                if hasattr(edge, 'attributes'):  # check if they have attributes
                    if edge.attributes:  # if there are any edge attributes
                        for attribute in edge.attributes:  # for each attribute
                            if attribute.original_attribute_name == params['edge_attribute'] or attribute.attribute_type_id == params['edge_attribute']:  # check if it's the desired one
                                try:
                                    edge_values[key] = {'value': float(attribute.value), 'relation': None}
                                except ValueError:
                                    edge_values[key] = {'value': attribute.value, 'relation': None}
                            if attribute.original_attribute_name == "virtual_relation_label":
                                edge_relation = attribute.value
                        edge_values[key]['relation'] = edge_relation
            if params['descending']:
                value_list=[-math.inf]*len(self.message.results)
            else:
                value_list=[math.inf]*len(self.message.results)
            i = 0
            type_flag = 'edge_relation' in params
            for result in self.message.results:
                for binding_list in result.edge_bindings.values():
                    for binding in binding_list:
                        # need to test this for TRAPI 1.0 after expand (and resultify?)is updated to see if binding.id matches edge_key
                        if edge_values[binding.id]['value'] is not None:
                            if not type_flag or (type_flag and params['edge_relation'] == edge_values[binding.id]['relation']):
                                if abs(value_list[i]) == math.inf:
                                    value_list[i] = edge_values[binding.id]['value']
                                else:
                                    # this will take the sum off all edges with the attribute if we want to change to max edit this line
                                    value_list[i] += edge_values[binding.id]['value']
                i+=1
            idx = sort_index(value_list, params['descending'])
            self.message.results = [self.message.results[i] for i in idx]
            if 'max_results' in params:
                prune_val = self.parameters['prune_kg']
                self.parameters['prune_kg'] = False
                self.limit_number_of_results()
                self.parameters['prune_kg'] = prune_val
            if params['prune_kg']:
                self.prune_kg()
            self.message.n_results = len(self.message.results)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong sorting results")
        else:
            self.response.info(f"Results successfully sorted")

        return self.response

    def sort_by_edge_count(self):
        """
        sort results by edge count
        :return: response
        """
        self.response.debug(f"Sorting Results")
        self.response.info(f"Sorting the results by edge count")
        params = self.parameters
        try:
            value_list=[0]*len(self.message.results)
            i = 0
            for result in self.message.results:
                value_list[i] = len([binding for binding_list in result.edge_bindings.values() for binding in binding_list])
                i+=1
            idx = sort_index(value_list, params['descending'])
            self.message.results = [self.message.results[i] for i in idx]
            if 'max_results' in params:
                prune_val = self.parameters['prune_kg']
                self.parameters['prune_kg'] = False
                self.limit_number_of_results()
                self.parameters['prune_kg'] = prune_val
            if params['prune_kg']:
                self.prune_kg()
            self.message.n_results = len(self.message.results)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong sorting results")
        else:
            self.response.info(f"Results successfully sorted")

        return self.response

    def sort_by_score(self):
        """
        sort results by edge count
        :return: response
        """
        self.response.debug(f"Sorting Results")
        self.response.info(f"Sorting the results by result score")
        params = self.parameters
        try:
            value_list=[0]*len(self.message.results)
            i = 0
            for result in self.message.results:
                value_list[i] = result.score
                i+=1
            idx = sort_index(value_list, params['descending'])
            self.message.results = [self.message.results[i] for i in idx]
            if 'max_results' in params:
                prune_val = self.parameters['prune_kg']
                self.parameters['prune_kg'] = False
                self.limit_number_of_results()
                self.parameters['prune_kg'] = prune_val
            if params['prune_kg']:
                self.prune_kg()
            self.message.n_results = len(self.message.results)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong sorting results")
        else:
            self.response.info(f"Results successfully sorted")

        return self.response

    def sort_by_node_attribute(self):
        """
        Iterate over all the results and sort by the edge attribute provided.
        :return: response
        """
        self.response.debug(f"Sorting Results")
        self.response.info(f"Sorting the results by node attribute")
        params = self.parameters
        try:
            node_values = {}
            # iterate over the nodes find the attribute values
            for key, node in self.message.knowledge_graph.nodes.items():  # iterate over the nodes
                node_values[key] = {'value': None, 'category': node.categories}
                if 'qnode_keys' in params and params['qnode_keys'] is not None and len(params['qnode_keys']) > 0:
                    if key not in params['qnode_keys']:
                        continue
                if hasattr(node, 'attributes'):  # check if they have attributes
                    if node.attributes:  # if there are any node attributes
                        for attribute in node.attributes:  # for each attribute
                            if attribute.original_attribute_name == params['node_attribute'] or attribute.attribute_type_id == params['node_attribute']:  # check if it's the desired one
                                if attribute.original_attribute_name == 'pubmed_ids':
                                    node_values[key] = {'value': attribute.value.count("PMID"), 'category': node.categories}
                                else:
                                    try:
                                        node_values[key] = {'value': float(attribute.value), 'category': node.categories}
                                    except ValueError:
                                        node_values[key] = {'value': attribute.value, 'category': node.categories}
            if params['descending']:
                value_list=[-math.inf]*len(self.message.results)
            else:
                value_list=[math.inf]*len(self.message.results)
            i = 0
            type_flag = 'node_category' in params
            for result in self.message.results:
                for binding_list in result.node_bindings.values():
                    for binding in binding_list:
                        if node_values[binding.id]['value'] is not None:
                            if not type_flag or (type_flag and params['node_category'] == node_values[binding.id]['category']):
                                if abs(value_list[i]) == math.inf:
                                    value_list[i] = node_values[binding.id]['value']
                                else:
                                    # this will take the sum off all nodes with the attribute if we want to change to max edit this line
                                    value_list[i] += node_values[binding.id]['value']
                i+=1
            idx = sort_index(value_list, params['descending'])
            self.message.results = [self.message.results[i] for i in idx]
            if 'max_results' in params:
                prune_val = self.parameters['prune_kg']
                self.parameters['prune_kg'] = False
                self.limit_number_of_results()
                self.parameters['prune_kg'] = prune_val
            if params['prune_kg']:
                self.prune_kg()
            self.message.n_results = len(self.message.results)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong sorting results")
        else:
            self.response.info(f"Results successfully sorted")

        return self.response

    def sort_by_node_count(self):
        """
        sort the results by node count
        :return: response
        """
        self.response.debug(f"Sorting Results")
        self.response.info(f"Sorting the results by node count")
        params = self.parameters
        try:
            value_list=[0]*len(self.message.results)
            i = 0
            for result in self.message.results:
                value_list[i] = len([binding for binding_list in result.node_bindings.values() for binding in binding_list])
                i+=1
            idx = sort_index(value_list, params['descending'])
            self.message.results = [self.message.results[i] for i in idx]
            if 'max_results' in params:
                prune_val = self.parameters['prune_kg']
                self.parameters['prune_kg'] = False
                self.limit_number_of_results()
                self.parameters['prune_kg'] = prune_val
            if params['prune_kg']:
                self.prune_kg()
            self.message.n_results = len(self.message.results)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong sorting results")
        else:
            self.response.info(f"Results successfully sorted")


        return self.response

    def prune_kg(self):
        """
        prune the kg to match the results
        :return: response
        """
        try:
            node_keys = set()
            edge_keys = set()
            nodes_to_remove = set()
            edges_to_remove = set()
            for result in self.message.results:
                for node_binding_list in result.node_bindings.values():
                    for node_binding in node_binding_list:
                        node_keys.add(node_binding.id)
                for edge_binding_list in result.edge_bindings.values():
                    for edge_binding in edge_binding_list:
                        edge_keys.add(edge_binding.id)
            #node_keys_to_remove = set()
            for key, node in self.message.knowledge_graph.nodes.items():
                if key not in node_keys:
                    nodes_to_remove.add(key)
                    #node_keys_to_remove.add(node.id)
            #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for key, edge in self.message.knowledge_graph.edges.items():
                if key not in edge_keys or edge.subject in nodes_to_remove or edge.object in nodes_to_remove:
                    edges_to_remove.add(key)
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong prunning the KG")
        else:
            self.response.info(f"KG successfully pruned to match results")




    

    
