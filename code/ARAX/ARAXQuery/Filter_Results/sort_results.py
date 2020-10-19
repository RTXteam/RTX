# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import traceback
import numpy as np
import math

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
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
            for edge in self.message.knowledge_graph.edges:  # iterate over the edges
                edge_values[str(edge.id)] = {'value': None, 'relation': edge.relation}
                if hasattr(edge, 'edge_attributes'):  # check if they have attributes
                    if edge.edge_attributes:  # if there are any edge attributes
                        for attribute in edge.edge_attributes:  # for each attribute
                            if attribute.name == params['edge_attribute']:  # check if it's the desired one
                                edge_values[str(edge.id)] = {'value': attribute.value, 'relation': edge.relation}
            if params['descending']:
                value_list=[-math.inf]*len(self.message.results)
            else:
                value_list=[math.inf]*len(self.message.results)
            i = 0
            type_flag = 'edge_relation' in params
            for result in self.message.results:
                for binding in result.edge_bindings:
                    if edge_values[binding.kg_id]['value'] is not None:
                        if not type_flag or (type_flag and params['edge_relation'] == edge_values[binding.kg_id]['relation']):
                            if abs(value_list[i]) == math.inf:
                                value_list[i] = edge_values[binding.kg_id]['value']
                            else:
                                # this will take the sum off all edges with the attribute if we want to change to max edit this line
                                value_list[i] += edge_values[binding.kg_id]['value']
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
                value_list[i] = len(result.edge_bindings)
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
            for node in self.message.knowledge_graph.nodes:  # iterate over the nodes
                node_values[str(node.id)] = {'value': None, 'type': node.type}
                if hasattr(node, 'node_attributes'):  # check if they have attributes
                    if node.node_attributes:  # if there are any node attributes
                        for attribute in node.node_attributes:  # for each attribute
                            if attribute.name == params['node_attribute']:  # check if it's the desired one
                                if attribute.name == 'pubmed_ids':
                                    node_values[str(node.id)] = {'value': attribute.value.count("PMID"), 'type': node.type}
                                else:
                                    node_values[str(node.id)] = {'value': attribute.value, 'type': node.type}
            if params['descending']:
                value_list=[-math.inf]*len(self.message.results)
            else:
                value_list=[math.inf]*len(self.message.results)
            i = 0
            type_flag = 'node_type' in params
            for result in self.message.results:
                for binding in result.node_bindings:
                    if node_values[binding.kg_id]['value'] is not None:
                        if not type_flag or (type_flag and params['node_type'] == node_values[binding.kg_id]['type']):
                            if abs(value_list[i]) == math.inf:
                                value_list[i] = node_values[binding.kg_id]['value']
                            else:
                                # this will take the sum off all nodes with the attribute if we want to change to max edit this line
                                value_list[i] += node_values[binding.kg_id]['value']
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
                value_list[i] = len(result.node_bindings)
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
            node_ids = set()
            edge_ids = set()
            nodes_to_remove = set()
            edges_to_remove = set()
            for result in self.message.results:
                for node_binding in result.node_bindings:
                    node_ids.add(node_binding.kg_id)
                for edge_binding in result.edge_bindings:
                    edge_ids.add(edge_binding.kg_id)
            node_ids_to_remove = set()
            i = 0
            for node in self.message.knowledge_graph.nodes:
                if node.id not in node_ids:
                    nodes_to_remove.add(i)
                    node_ids_to_remove.add(node.id)
                i += 1
            self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            i = 0
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for edge in self.message.knowledge_graph.edges:
                if edge.id not in edge_ids or edge.source_id in node_ids_to_remove or edge.target_id in node_ids_to_remove:
                    edges_to_remove.add(i)
                i += 1
            # remove edges
            self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong prunning the KG")
        else:
            self.response.info(f"KG successfully pruned to match results")




    

    