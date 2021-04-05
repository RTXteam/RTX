#!/bin/env python3
# This class will perform fisher's exact test to evalutate the significance of connection between
# a list of source nodes with certain qnode_id in KG and each of the target nodes with specified type.

# relative imports
import scipy.stats as stats
import traceback
import sys
import os
import multiprocessing
import pandas as pd
from datetime import datetime
from neo4j import GraphDatabase, basic_auth
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../")
from ARAX_query import ARAXQuery
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import overlay_utilities as ou
import collections


class ComputeFTEST:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters

    def fisher_exact_test(self):
        """
        Peform the fisher's exact test to expand or decorate the knowledge graph
        :return: response
        """

        self.response.info(f"Performing Fisher's Exact Test to add p-value to edge attribute of virtual edge")

        # check the input parameters
        if 'subject_qnode_key' not in self.parameters:
            self.response.error(f"The argument 'subject_qnode_key' is required for fisher_exact_test function")
            return self.response
        else:
            subject_qnode_key = self.parameters['subject_qnode_key']
        if 'virtual_relation_label' not in self.parameters:
            self.response.error(f"The argument 'virtual_relation_label' is required for fisher_exact_test function")
            return self.response
        else:
            virtual_relation_label = str(self.parameters['virtual_relation_label'])
        if 'object_qnode_key' not in self.parameters:
            self.response.error(f"The argument 'object_qnode_key' is required for fisher_exact_test function")
            return self.response
        else:
            object_qnode_key = self.parameters['object_qnode_key']
        rel_edge_key = self.parameters['rel_edge_key'] if 'rel_edge_key' in self.parameters else None
        top_n = int(self.parameters['top_n']) if 'top_n' in self.parameters else None
        cutoff = float(self.parameters['cutoff']) if 'cutoff' in self.parameters else None

        # initialize some variables
        nodes_info = {}
        edge_expand_kp = []
        subject_node_list = []
        object_node_dict = {}
        size_of_object = {}
        subject_node_exist = False
        object_node_exist = False
        query_edge_key = set()
        rel_edge_type = set()
        subject_node_category = None
        object_node_category= None

        ## Check if subject_qnode_key and object_qnode_key are in the Query Graph
        try:
            if len(self.message.query_graph.nodes) != 0:
                for node_key in self.message.query_graph.nodes:
                    if node_key == subject_qnode_key:
                        subject_node_exist = True
                        subject_node_category = self.message.query_graph.nodes[node_key].category
                    elif node_key == object_qnode_key:
                        object_node_exist = True
                        object_node_category = self.message.query_graph.nodes[node_key].category
                    else:
                        pass
            else:
                self.response.error(f"There is no query node in QG")
                return self.response
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving nodes in message QG")
            return self.response

        if subject_node_exist:
            if object_node_exist:
                pass
            else:
                self.response.error(f"No query node with object qnode key {object_qnode_key} detected in QG for Fisher's Exact Test")
                return self.response
        else:
            self.response.error(f"No query node with subject qnode key {subject_qnode_key} detected in QG for Fisher's Exact Test")
            return self.response

        ## Check if there is a query edge connected to both subject_qnode_key and object_qnode_key in the Query Graph
        try:
            if len(self.message.query_graph.edges) != 0:
                for edge_key in self.message.query_graph.edges:
                    if self.message.query_graph.edges[edge_key].subject == subject_qnode_key and self.message.query_graph.edges[edge_key].object == object_qnode_key and self.message.query_graph.edges[edge_key].relation == None:
                        query_edge_key.update([edge_key])  # only actual query edge is added
                    elif self.message.query_graph.edges[edge_key].subject == object_qnode_key and self.message.query_graph.edges[edge_key].object == subject_qnode_key and self.message.query_graph.edges[edge_key].relation == None:
                        query_edge_key.update([edge_key])  # only actual query edge is added
                    else:
                        continue
            else:
                self.response.error(f"There is no query edge in Query Graph")
                return self.response
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving edges in message QG")
            return self.response

        if len(query_edge_key)!=0:
            if rel_edge_key:
                if rel_edge_key in query_edge_key:
                    pass
                else:
                    self.response.error(f"No query edge with qedge key {rel_edge_key} connected to both subject node with qnode key {subject_qnode_key} and object node with qnode key {object_qnode_key} detected in QG for Fisher's Exact Test")
                    return self.response
            else:
                pass
        else:
            self.response.error(
                f"No query edge connected to both subject node with qnode key {subject_qnode_key} and object node with qnode key {object_qnode_key} detected in QG for Fisher's Exact Test")
            return self.response

        ## loop over all nodes in KG and collect their node information
        try:
            count = 0
            for node_key, node in self.message.knowledge_graph.nodes.items():
                nodes_info[node_key] = {'count': count, 'qnode_keys': node.qnode_keys, 'category': self.message.knowledge_graph.nodes[node_key].category, 'edge_index': []}
                count = count + 1
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving nodes in message KG")
            return self.response

        ## loop over all edges in KG and create subject node list and target node dict based on subject_qnode_key, object_qnode_key as well as rel_edge_id (optional, otherwise all edges are considered)
        try:
            count = 0
            for edge_key, edge in self.message.knowledge_graph.edges.items():

                edge_attribute_dict = {x.name:x.value for x in self.message.knowledge_graph.edges[edge_key].attributes}
                if edge_attribute_dict['is_defined_by'] != 'ARAX':

                    nodes_info[self.message.knowledge_graph.edges[edge_key].subject]['edge_index'].append(count)
                    nodes_info[self.message.knowledge_graph.edges[edge_key].object]['edge_index'].append(count)

                    if rel_edge_key:
                        if rel_edge_key in edge.qedge_keys:
                            if subject_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].subject]['qnode_keys']:
                                edge_expand_kp.append(edge_attribute_dict['is_defined_by'])
                                rel_edge_type.update([self.message.knowledge_graph.edges[edge_key].predicate])
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].subject)
                                if self.message.knowledge_graph.edges[edge_key].object not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object] = {self.message.knowledge_graph.edges[edge_key].subject}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object].update([self.message.knowledge_graph.edges[edge_key].subject])
                            else:
                                edge_expand_kp.append(edge_attribute_dict['is_defined_by'])
                                rel_edge_type.update([self.message.knowledge_graph.edges[edge_key].predicate])
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].object)
                                if self.message.knowledge_graph.edges[edge_key].subject not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject] = {self.message.knowledge_graph.edges[edge_key].object}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject].update([self.message.knowledge_graph.edges[edge_key].object])
                        else:
                            pass
                    else:
                        if subject_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].subject]['qnode_keys']:
                            if object_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].object]['qnode_keys']:
                                edge_expand_kp.append(edge_attribute_dict['is_defined_by'])
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].subject)
                                if self.message.knowledge_graph.edges[edge_key].object not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object] = {self.message.knowledge_graph.edges[edge_key].subject}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object].update([self.message.knowledge_graph.edges[edge_key].subject])

                            else:
                                pass
                        elif object_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].subject]['qnode_keys']:
                            if subject_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].object]['qnode_keys']:
                                edge_expand_kp.append(edge_attribute_dict['is_defined_by'])
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].object)
                                if self.message.knowledge_graph.edges[edge_key].subject not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject] = {self.message.knowledge_graph.edges[edge_key].object}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject].update([self.message.knowledge_graph.edges[edge_key].object])

                            else:
                                pass
                        else:
                            pass

                else:
                    pass

                count = count + 1 ## record edge position in message.knowledge_graph

        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving edges in message KG")
            return self.response

        subject_node_list = list(set(subject_node_list)) ## remove the duplicate subject node key

        ## check if there is no subject node in message KG
        if len(subject_node_list) == 0:
            self.response.error(f"No subject node found in message KG for Fisher's Exact Test")
            return self.response

        ## check if there is no object node in message KG
        if len(object_node_dict) == 0:
            self.response.error(f"No object node found in message KG for Fisher's Exact Test")
            return self.response

        ## check if subject node has more than one type. If so, throw an error
        if subject_node_category is None:
            self.response.error(f"Subject node with qnode key {subject_qnode_key} was set to None in Query Graph. Please specify the node type")
            return self.response
        else:
            pass

        ## check if object node has more than one type. If so, throw an error
        if object_node_category is None:
            self.response.error(f"Object node with qnode key {object_qnode_key} was set to None in Query Graph. Please specify the node type")
            return self.response
        else:
            pass

        ##check how many kps were used in message KG. If more than one, the one with the max number of edges connnected to both subject nodes and object nodes was used
        if len(collections.Counter(edge_expand_kp))==1:
            kp = edge_expand_kp[0]
        else:
            occurrences = collections.Counter(edge_expand_kp)
            max_index = max([(value, index) for index, value in enumerate(occurrences.values())])[1] # if there are more than one kp having the maximum number of edges, then the last one based on alphabetical order will be chosen.
            kp = list(occurrences.keys())[max_index]
            self.response.debug(f"{occurrences}")
            self.response.warning(f"More than one knowledge provider was detected to be used for expanding the edges connected to both subject node with qnode key {subject_qnode_key} and object node with qnode key {object_qnode_key}")
            self.response.warning(f"The knowledge provider {kp} was used to calculate Fisher's exact test because it has the maximum number of edges both subject node with qnode key {subject_qnode_key} and object node with qnode key {object_qnode_key}")

        ## Print out some information used to calculate FET
        if len(subject_node_list) == 1:
            self.response.debug(f"{len(subject_node_list)} subject node with qnode key {subject_qnode_key} and node type {subject_node_category} was found in message KG and used to calculate Fisher's Exact Test")
        else:
            self.response.debug(f"{len(subject_node_list)} subject nodes with qnode key {subject_qnode_key} and node type {subject_node_category} was found in message KG and used to calculate Fisher's Exact Test")
        if len(object_node_dict) == 1:
            self.response.debug(f"{len(object_node_dict)} object node with qnode key {object_qnode_key} and node type {object_node_category} was found in message KG and used to calculate Fisher's Exact Test")
        else:
            self.response.debug(f"{len(object_node_dict)} object nodes with qnode key {object_qnode_key} and node type {object_node_category} was found in message KG and used to calculate Fisher's Exact Test")


        # find all nodes with the same type of 'subject_qnode_key' nodes in specified KP ('ARAX/KG1','ARAX/KG2','BTE') that are adjacent to target nodes
        use_parallel = False

        if not use_parallel:
            # query adjacent node in one DSL command by providing a list of query nodes to add_qnode()
            if rel_edge_key:
                if len(rel_edge_type) == 1:  # if the edge with rel_edge_key has only type, we use this rel_edge_predicate to find all subject nodes in KP
                    self.response.debug(f"{kp} and edge relation type {list(rel_edge_type)[0]} were used to calculate total object nodes in Fisher's Exact Test")
                    result = self.query_size_of_adjacent_nodes(node_curie=list(object_node_dict.keys()), source_type=object_node_category, adjacent_type=subject_node_category, kp = kp, rel_type=list(rel_edge_type)[0], use_cypher_command=False)
                else:  # if the edge with rel_edge_key has more than one type, we ignore the edge predicate and use all categories to find all subject nodes in KP
                    self.response.warning(f"The edges with specified qedge key {rel_edge_key} have more than one category, we ignore the edge predicate and use all categories to calculate Fisher's Exact Test")
                    self.response.debug(f"{kp} was used to calculate total object nodes in Fisher's Exact Test")
                    result = self.query_size_of_adjacent_nodes(node_curie=list(object_node_dict.keys()), source_type=object_node_category, adjacent_type=subject_node_category, kp=kp, rel_type=None, use_cypher_command=False)
            else:  # if no rel_edge_key is specified, we ignore the edge predicate and use all categories to find all subject nodes in KP
                self.response.debug(f"{kp} was used to calculate total object nodes in Fisher's Exact Test")
                result = self.query_size_of_adjacent_nodes(node_curie=list(object_node_dict.keys()), source_type=object_node_category, adjacent_type=subject_node_category, kp=kp, rel_type=None, use_cypher_command=False)

            if result is None:
                return self.response ## Something wrong happened for querying the adjacent nodes
            else:
                res, removed_nodes = result
                if len(removed_nodes)==0:
                    size_of_object = res
                else:
                    if len(removed_nodes) == 1:
                        self.response.warning(f"One object node which is {removed_nodes[0]} can't find its neighbors. This node will be ignored for FET calculation.")
                    else:
                        self.response.warning(f"{len(removed_nodes)} object nodes which are {removed_nodes} can't find its neighbors. These nodes will be ignored for FET calculation.")
                    for node in removed_nodes:
                        del object_node_dict[node]
                    size_of_object = res
        else:
            # query adjacent node for query nodes one by one in parallel
            if rel_edge_key:
                if len(rel_edge_type) == 1:  # if the edge with rel_edge_key has only type, we use this rel_edge_predicate to find all subject nodes in KP
                    self.response.debug(f"{kp} and edge relation type {list(rel_edge_type)[0]} were used to calculate total adjacent nodes in Fisher's Exact Test")
                    parameter_list = [(node, object_node_category, subject_node_category, kp, list(rel_edge_type)[0]) for node in list(object_node_dict.keys())]
                else:  # if the edge with rel_edge_key has more than one type, we ignore the edge type and use all types to find all source nodes in KP
                    self.response.warning(f"The edges with specified qedge key {rel_edge_key} have more than one type, we ignore the edge type and use all types to calculate Fisher's Exact Test")
                    self.response.debug(f"{kp} was used to calculate total adjacent nodes in Fisher's Exact Test")
                    parameter_list = [(node, object_node_category, subject_node_category, kp, None) for node in list(object_node_dict.keys())]
            else:  # if no rel_edge_key is specified, we ignore the edge type and use all types to find all source nodes in KP
                self.response.debug(f"{kp} was used to calculate total adjacent nodes in Fisher's Exact Test")
                parameter_list = [(node, object_node_category, subject_node_category, kp, None) for node in list(object_node_dict.keys())]

            ## get the count of all nodes with the type of 'subject_qnode_key' nodes in KP for each target node in parallel
            try:
                with multiprocessing.Pool() as executor:
                    object_count_res = [elem for elem in executor.map(self._query_size_of_adjacent_nodes_parallel, parameter_list)]
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with querying adjacent nodes in parallel")
                return self.response

            if any([type(elem) is list for elem in object_count_res]):
                for msg in [elem2 for elem1 in object_count_res if type(elem1) is list for elem2 in elem1]:
                    if type(msg) is tuple:
                        self.response.error(msg[0], error_code=msg[1])
                    else:
                        self.response.error(msg)
                return self.response  ## Something wrong happened for querying the adjacent nodes
            else:
                for index in range(len(object_node_dict)):
                    node = list(object_node_dict.keys())[index]
                    size_of_object[node] = object_count_res[index]

        if len(object_node_dict) != 0:
            ## Based on KP detected in message KG, find the total number of node with the same type of source node
            if kp=='ARAX/KG1':
                size_of_total = self.size_of_given_type_in_KP(node_type=subject_node_category, use_cypher_command=False, kg='KG1')
                if size_of_total != 0:
                    self.response.debug(f"ARAX/KG1 and cypher query were used to calculate total number of node with the same type of source node in Fisher's Exact Test")
                    self.response.debug(f"Total {size_of_total} unique concepts with node category {subject_node_category} was found in ARAX/KG1")
                else:
                    print(f'######## {subject_node_category} ######', flush=True)
                    size_of_total = self.size_of_given_type_in_KP(node_type=subject_node_category, use_cypher_command=False, kg='KG2') ## If cypher query fails, then try kgNodeIndex
                    if size_of_total==0:
                        self.response.error(f"Both KG1 and KG2 have 0 node with the same type of subject node with qnode key {subject_qnode_key}")
                        return self.response
                    else:
                        self.response.debug(f"Since KG1 can't find the any nodes with node category {subject_node_category}, ARAX/KG2C were used to calculate total number of node with the same type of source node in Fisher's Exact Test")
                        self.response.debug(f"Total {size_of_total} unique concepts with node category {subject_node_category} was found in ARAX/KG2C")

            elif kp=='ARAX/KG2' or kp == 'ARAX/KG2c':
                ## check KG1 first as KG2 might have many duplicates. If KG1 is 0, then check KG2
                size_of_total = self.size_of_given_type_in_KP(node_type=subject_node_category, use_cypher_command=False, kg='KG2') ## Try cypher query first
                self.response.debug(f"ARAX/KG2C were used to calculate total number of node with the same type of source node in Fisher's Exact Test")
                self.response.debug(f"Total {size_of_total} unique concepts with node category {subject_node_category} was found in ARAX/KG2C")

            else:
                self.response.error(f"Only KG1 or KG2 is allowable to calculate the Fisher's exact test temporally")
                return self.response

            size_of_query_sample = len(subject_node_list)

            self.response.debug(f"Computing Fisher's Exact Test P-value")
            # calculate FET p-value for each target node in parallel
            del_list = []
            parameter_list = []
            for node in object_node_dict:
                if size_of_object[node]-len(object_node_dict[node]) < 0:
                    del_list.append(node)
                    self.response.warning(f"Skipping node {node} to calculate FET p-value due to issue897 (which causes negative value).")
                    continue
                else:
                    parameter_list += [(node, len(object_node_dict[node]), size_of_object[node]-len(object_node_dict[node]), size_of_query_sample - len(object_node_dict[node]), (size_of_total - size_of_object[node]) - (size_of_query_sample - len(object_node_dict[node])))]

            for del_node in del_list:
                del object_node_dict[del_node]
            # parameter_list = [(node, len(target_node_dict[node]), size_of_target[node]-len(target_node_dict[node]), size_of_query_sample - len(target_node_dict[node]), (size_of_total - size_of_target[node]) - (size_of_query_sample - len(target_node_dict[node]))) for node in target_node_dict]

            try:
                with multiprocessing.Pool() as executor:
                    FETpvalue_list = [elem for elem in executor.map(self._calculate_FET_pvalue_parallel, parameter_list)]
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with computing Fisher's Exact Test P-value")
                return self.response

            if any([type(elem) is list for elem in FETpvalue_list]):
                for msg in [elem2 for elem1 in FETpvalue_list if type(elem1) is list for elem2 in elem1]:
                    if type(msg) is tuple:
                        self.response.error(msg[0], error_code=msg[1])
                    else:
                        self.response.error(msg)
                return self.response
            else:
                output = dict(FETpvalue_list)

            # check if the results need to be filtered
            output = dict(sorted(output.items(), key=lambda x: x[1]))
            if cutoff:
                output = dict(filter(lambda x: x[1] < cutoff, output.items()))
            else:
                pass
            if top_n:
                output = dict(list(output.items())[:top_n])
            else:
                pass

            # add the virtual edge with FET result to message KG
            self.response.debug(f"Adding virtual edge with FET result to message KG")
            count = 0
            for index, value in enumerate([(virtual_relation_label, output[adj], node, adj) for adj in object_node_dict if adj in output.keys() for node in object_node_dict[adj]], 1):

                edge_attribute_list =  [
                    EdgeAttribute(type="EDAM:data_1669", name="fisher_exact_test_p-value", value=str(value[1]), url=None),
                    EdgeAttribute(name="is_defined_by", value="ARAX", type="ARAX_TYPE_PLACEHOLDER"),
                    EdgeAttribute(name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), type="metatype:Datetime"),
                    EdgeAttribute(name="provided_by", value="ARAX", type="biolink:provided_by"),
                    #EdgeAttribute(name="confidence", value=None, type="biolink:ConfidenceLevel"),
                    #EdgeAttribute(name="weight", value=None, type="metatype:Float")
                ]
                edge_id = f"{value[0]}_{index}"
                edge = Edge(predicate='biolink:has_fisher_exact_test_p-value_with', subject=value[2], object=value[3], relation=value[0],
                            attributes=edge_attribute_list)
                edge.qedge_keys = [value[0]]

                self.message.knowledge_graph.edges[edge_id] = edge

                count = count + 1

            self.response.debug(f"{count} new virtual edges were added to message KG")

            # add the virtual edge to message QG
            if count > 0:
                self.response.debug(f"Adding virtual edge to message QG")
                edge_type = "biolink:has_fisher_exact_test_p-value_with"
                option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key,
                                                                          self.message.query_graph, self.response)
                qedge_id = virtual_relation_label
                q_edge = QEdge(predicate=edge_type, relation=virtual_relation_label,
                               subject=subject_qnode_key, object=object_qnode_key,
                               option_group_id=option_group_id)
                self.message.query_graph.edges[qedge_id] = q_edge
                self.response.debug(f"One virtual edge was added to message QG")

        return self.response


    def query_size_of_adjacent_nodes(self, node_curie, source_type, adjacent_type, kp="ARAX/KG1", rel_type=None, use_cypher_command=False):
        """
        Query adjacent nodes of a given source node based on adjacent node type.
        :param node_curie: (required) the curie id of query node. It accepts both single curie id or curie id list eg. "UniProtKB:P14136" or ['UniProtKB:P02675', 'UniProtKB:P01903', 'UniProtKB:P09601', 'UniProtKB:Q02878']
        :param source_type: (required) the type of source node, eg. "gene"
        :param adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        :param kp: (optional) the knowledge provider to use, eg. "ARAX/KG1"(default)
        :param rel_type: (optional) edge type to consider, eg. "involved_in"
        :param use_cypher_command: Boolean (True or False). If True, it used cypher command to the size of query adjacent nodes(default:True)
        :return a tuple with a dict containing the number of adjacent nodes for the query node and a list of removed nodes
        """

        res = None

        if kp=='ARAX/KG2' or kp == 'ARAX/KG2c':
            kp="ARAX/KG2"

        if use_cypher_command is True:

            #create the RTXConfiguration object
            rtxConfig = RTXConfiguration()
            # Connection information for the neo4j server, populated with orangeboard
            if kp=="ARAX/KG1":
                driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
            elif kp=="ARAX/KG2":
                rtxConfig.live = "KG2"
                driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
            else:
                self.response.error(f"The 'kp' argument of 'query_size_of_adjacent_nodes' method within FET only accepts 'ARAX/KG1' or 'ARAX/KG2' for cypher query right now")
                return res

            session = driver.session()

            # check if node_curie is a str or a list
            if type(node_curie) is str:
                if not rel_type:
                    query = f"match (n00:{adjacent_type})-[]-(n01) where n01.id='{node_curie}' with collect(distinct n00.id) as nodes_n00, n01 as node_n01 return node_n01.id as curie, size(nodes_n00) as count"
                else:
                    query = f"match (n00:{adjacent_type})-[:{rel_type}]-(n01) where n01.id='{node_curie}' with collect(distinct n00.id) as nodes_n00, n01 as node_n01 return node_n01.id as curie, size(nodes_n00) as count"
            elif type(node_curie) is list:
                if not rel_type:
                    query = f"match (n00:{adjacent_type})-[]-(n01) where n01.id in {node_curie} with collect(distinct n00.id) as nodes_n00, n01 as node_n01 return node_n01.id as curie, size(nodes_n00) as count"
                else:
                    query = f"match (n00:{adjacent_type})-[:{rel_type}]-(n01) where n01.id in {node_curie} with collect(distinct n00.id) as nodes_n00, n01 as node_n01 return node_n01.id as curie, size(nodes_n00) as count"
            else:
                self.response.error("The 'node_curie' argument of 'query_size_of_adjacent_nodes' method within FET only accepts str or list")
                return res

            try:
                cypher_res = session.run(query)
                result = pd.DataFrame(cypher_res.data())
                if result.shape[0] == 0:
                    self.response.error(f"Fail to query adjacent nodes from {kp} for {node_curie}")
                    return res
                else:
                    res_dict = dict()
                    has_error = False
                    if type(node_curie) is str:
                        res_dict[node_curie] = result['count'][0]
                        return res_dict
                    else:
                        for node in node_curie:
                            if node in list(result['curie']):
                                row_ind = list(result['curie']).index(node)
                                res_dict[node] = result.iloc[row_ind, 1]
                            else:
                                self.response.error(f"Fail to query adjacent nodes from {kp} for {node}")
                                has_error = True

                        if len(res_dict)==0:
                            return res
                        elif has_error is True:
                            return res
                        else:
                            return res_dict
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with querying adjacent nodes from {kp} for {node_curie}")
                return res

        else:

            # construct the instance of ARAXQuery class
            araxq = ARAXQuery()

            # check if node_curie is a str or a list
            if type(node_curie) is str:
                query_node_curie = node_curie
            elif type(node_curie) is list:
                node_id_list_str = "["
                for index in range(len(node_curie)):
                    node = node_curie[index]
                    if index + 1 == len(node_curie):
                        node_id_list_str = node_id_list_str + str(node) + "]"
                    else:
                        node_id_list_str = node_id_list_str + str(node) + ","

                query_node_curie = node_id_list_str
            else:
                self.response.error(
                    "The 'node_curie' argument of 'query_size_of_adjacent_nodes' method within FET only accepts str or list")
                return res

            # call the method of ARAXQuery class to query adjacent node
            if rel_type:
                query = {"operations": {"actions": [
                    "create_message",
                    f"add_qnode(id={query_node_curie}, category={source_type}, key=FET_n00)",
                    f"add_qnode(category={adjacent_type}, key=FET_n01)",
                    f"add_qedge(subject=FET_n00, object=FET_n01, key=FET_e00, predicate={rel_type})",
                    f"expand(edge_key=FET_e00,kp={kp})",
                    #"resultify()",
                    "return(message=true, store=false)"
                ]}}
            else:
                query = {"operations": {"actions": [
                    "create_message",
                    f"add_qnode(id={query_node_curie}, category={source_type}, key=FET_n00)",
                    f"add_qnode(category={adjacent_type}, key=FET_n01)",
                    f"add_qedge(subject=FET_n00, object=FET_n01, key=FET_e00)",
                    f"expand(edge_key=FET_e00,kp={kp})",
                    #"resultify()",
                    "return(message=true, store=false)"
                ]}}

            try:
                result = araxq.query(query)
                if result.status != 'OK':
                    self.response.error(f"Fail to query adjacent nodes from {kp} for {node_curie}")
                    return res
                else:
                    res_dict = dict()
                    message = araxq.response.envelope.message
                    if type(node_curie) is str:
                        tmplist = set([edge_key for edge_key in message.knowledge_graph.edges if message.knowledge_graph.edges[edge_key].subject == node_curie or message.knowledge_graph.edges[edge_key].object == node_curie])  ## edge has no direction
                        if len(tmplist) == 0:
                            self.response.warning(f"Fail to query adjacent nodes from {kp} for {node_curie} in FET probably because expander ignores node type. For more details, please see issue897.")
                            return (res_dict,[node_curie])
                        res_dict[node_curie] = len(tmplist)
                        return (res_dict,[])
                    else:
                        check_empty = False
                        failure_node = list()
                        for node in node_curie:
                            tmplist = set([edge_key for edge_key in message.knowledge_graph.edges if message.knowledge_graph.edges[edge_key].subject == node or message.knowledge_graph.edges[edge_key].object == node])  ## edge has no direction
                            if len(tmplist) == 0:
                                self.response.warning(f"Fail to query adjacent nodes from {kp} for {node} in FET probably because expander ignores node type. For more details, please see issue897.")
                                failure_node.append(node)
                                check_empty = True
                                continue
                            res_dict[node] = len(tmplist)

                        if check_empty is True:
                            return (res_dict,failure_node)
                        else:
                            return (res_dict,failure_node)
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with querying adjacent nodes from {kp} for {node_curie}")
                return res


    def _query_size_of_adjacent_nodes_parallel(self, this):
        # This method is expected to be run within this class
        """
        Query the size of adjacent nodes of a given source node based on adjacent node type in parallel.
        :param this is a list containing five sub-arguments below since this function is exectued in parallel.
        :return the number of adjacent nodes for the query node
        """
        #:sub-argument node_curie: (required) the curie id of query node, eg. "UniProtKB:P14136"
        #:sub-argument source_type: (required) the type of source node, eg. "gene"
        #:sub-argument adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        #:sub-argument kp: (optional) the knowledge provider to use, eg. "ARAX/KG1"(default)
        #:sub-argument rel_type: (optional) edge type to consider, eg. "involved_in"

        error_message = []
        if len(this) == 5:
            # this contains four arguments and assign them to different variables
            node_curie, source_type, adjacent_type, kp, rel_type = this
        elif len(this) == 4:
            node_curie, source_type, adjacent_type, kp = this
            rel_type = None
        elif len(this) == 3:
            node_curie, source_type, adjacent_type = this
            kp = "ARAX/KG1"
            rel_type = None
        else:
            error_message.append("The '_query_size_of_adjacent_nodes_parallel' method within FET only accepts four arguments: node_curie, adjacent_type, kp, rel_type")
            return error_message

        if kp=='ARAX/KG2' or kp == 'ARAX/KG2c':
            kp="ARAX/KG2"

        # construct the instance of ARAXQuery class
        araxq = ARAXQuery()

        # check if node_curie is a str
        if type(node_curie) is str:
            pass
        else:
            error_message.append("The 'node_curie' argument of '_query_size_of_adjacent_nodes_parallel' method within FET only accepts str")
            return error_message

        # call the method of ARAXQuery class to query adjacent node

        if rel_type:
            query = {"operations": {"actions": [
                "create_message",
                f"add_qnode(id={node_curie}, category={source_type}, key=FET_n00)",
                f"add_qnode(category={adjacent_type}, key=FET_n01)",
                f"add_qedge(subject=FET_n00, object=FET_n01, key=FET_e00, predicate={rel_type})",
                f"expand(edge_key=FET_e00,kp={kp})",
                #"resultify()",
                "return(message=true, store=false)"
            ]}}
        else:
            query = {"operations": {"actions": [
                "create_message",
                f"add_qnode(id={node_curie}, category={source_type}, key=FET_n00)",
                f"add_qnode(category={adjacent_type}, key=FET_n01)",
                f"add_qedge(subject=FET_n00, object=FET_n01, key=FET_e00)",
                f"expand(edge_key=FET_e00,kp={kp})",
                #"resultify()",
                "return(message=true, store=false)"
            ]}}

        try:
            result = araxq.query(query)
            if result.status != 'OK':
                error_message.append(f"Fail to query adjacent nodes from {kp} for {node_curie}")
                return error_message
            else:
                message = araxq.response.envelope.message
                tmplist = set([edge_key for edge_key in message.knowledge_graph.edges if message.knowledge_graph[edge_key].subject == node_curie or message.knowledge_graph[edge_key].object == node_curie]) ## edge has no direction
                if len(tmplist) == 0:
                    error_message.append(f"Fail to query adjacent nodes from {kp} for {node_curie}")
                    return error_message
                res = len(tmplist)
                return res
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            error_message.append((tb, error_type.__name__))
            error_message.append(f"Something went wrong with querying adjacent nodes from {kp} for {node_curie}")
            return error_message

    def size_of_given_type_in_KP(self, node_type, use_cypher_command=False, kg='KG1'):
        """
        find all nodes of a certain type in KP
        :param node_type: the query node type
        :param use_cypher_command: Boolean (True or False). If True, it used cypher command to query all nodes otherwise used NodeSynonymizer
        :param kg: only allowed for choosing 'KG1' or 'KG2' now. Will extend to BTE later
        """
        # TODO: extend this to KG2, BTE, and other KP's we know of

        size_of_total = None

        if kg == 'KG1' or kg == 'KG2':
            pass
        else:
            self.response.error(f"Only KG1 or KG2 is allowable to calculate the Fisher's exact test temporally")
            return size_of_total

        node_type = ComputeFTEST.convert_string_to_snake_case(node_type.replace('biolink:',''))
        node_type = ComputeFTEST.convert_string_biolinkformat(node_type)

        if kg == 'KG1':
            if use_cypher_command:
                rtxConfig = RTXConfiguration()
                # Connection information for the neo4j server, populated with orangeboard
                driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
                session = driver.session()

                query = "MATCH (n:%s) return count(distinct n)" % (node_type)
                res = session.run(query)
                size_of_total = res.single()["count(distinct n)"]
                return size_of_total
            else:
                nodesynonymizer = NodeSynonymizer()
                size_of_total = nodesynonymizer.get_total_entity_count(node_type, kg_name=kg)
                return size_of_total
        else:
            if use_cypher_command:
                self.response.warning(f"KG2 is only allowable to use NodeSynonymizer to query the total number of node with query type. It was set to use kgNodeIndex")
                nodesynonymizer = NodeSynonymizer()
                size_of_total = nodesynonymizer.get_total_entity_count(node_type, kg_name=kg)
                return size_of_total

            else:
                nodesynonymizer = NodeSynonymizer()
                size_of_total = nodesynonymizer.get_total_entity_count(node_type, kg_name=kg)
                return size_of_total

    def _calculate_FET_pvalue_parallel(self, this):
        # *Note*: The arugment 'this' is a list containing five sub-arguments below since this function is exectued in parallel.
        # This method is expected to be run within this class
        """
        Calculate Fisher Exact Test' p-value.
        *param this is a list containing five sub-arguments below since this function is exectued in parallel.
        :return a list of FET p-values
        """
        #:sub-argument node: (required) the curie name of node, eg. "UniProtKB:Q13330"
        #:sub-argument a: (required) count of in_sample and in_pathway
        #:sub-argument b: (required) count of not_in_sample but in_pathway
        #:sub-argument c: (required) count of in_sample but not in_pathway
        #:sub-argument d: (required) count of not in_sample and not in_pathway

        # this should contain five variables and assign them to different variables
        node, a, b, c, d = this
        error_message = []

        try:
            contingency_table = [[a, b],[c,d]]
            pvalue = stats.fisher_exact(contingency_table)[1]
            return (node, pvalue)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            error_message.append((tb, error_type.__name__))
            error_message.append(f"Something went wrong for target node {node} to calculate FET p-value")
            return error_message

    @staticmethod
    def convert_string_to_snake_case(input_string: str) -> str:
        # Converts a string like 'ChemicalSubstance' or 'chemicalSubstance' to 'chemical_substance'
        if len(input_string) > 1:
            snake_string = input_string[0].lower()
            for letter in input_string[1:]:
                if letter.isupper():
                    snake_string += "_"
                snake_string += letter.lower()
            return snake_string
        else:
            return input_string.lower()

    @staticmethod
    def convert_string_biolinkformat(input_string: str) -> str:

        if 'biolink' in input_string:
            return input_string
        else:
            if len(input_string) > 1:
                modified_string = input_string[0].upper()
                make_upper = False
                for letter in input_string[1:]:
                    if letter == '_':
                        make_upper = True
                        next
                    else:
                        if make_upper is True:
                            modified_string += letter.upper()
                            make_upper = False
                        else:
                            modified_string += letter
                return 'biolink:'+ modified_string
            else:
                return input_string
