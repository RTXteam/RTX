#!/bin/env python3
# This class will perform fisher's exact test to evalutate the significance of connection between
# a list of source nodes with certain qnode_id in KG and each of the target nodes with specified type.

# relative imports
import scipy.stats as stats
import traceback
import sys
import os
import re
import multiprocessing
from datetime import datetime
from neo4j import GraphDatabase, basic_auth
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
RTXConfig.live = "Production"
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
import sqlite3
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

        ## check if the new model files exists in /predictor/retrain_data. If not, scp it from arax.ncats.io
        pathlist = os.path.realpath(__file__).split(os.path.sep)
        RTXindex = pathlist.index("RTX")
        filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'KG2c'])

        ## check if there is kg2c.sqlite
        sqlite_name = RTXConfig.kg2c_sqlite_path.split("/")[-1]
        sqlite_file_path = f"{filepath}{os.path.sep}{sqlite_name}"
        if os.path.exists(sqlite_file_path):
            pass
        else:
            os.system(f"scp {RTXConfig.kg2c_sqlite_username}@{RTXConfig.kg2c_sqlite_host}:{RTXConfig.kg2c_sqlite_path} {sqlite_file_path}")
        self.sqlite_file_path = sqlite_file_path

        if rel_edge_key is not None:
            self.response.warning(f"The 'rel_edge_key' option in FET is specified, it will cause slow for the calculation of FEST test.")

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
        object_node_category = None

        ## Check if subject_qnode_key and object_qnode_key are in the Query Graph
        try:
            if len(self.message.query_graph.nodes) != 0:
                for node_key in self.message.query_graph.nodes:
                    if node_key == subject_qnode_key:
                        subject_node_exist = True
                        subject_node_category = self.message.query_graph.nodes[node_key].categories
                    elif node_key == object_qnode_key:
                        object_node_exist = True
                        object_node_category = self.message.query_graph.nodes[node_key].categories
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
                    qedge_relation = None
                    if hasattr(self.message.query_graph.edges[edge_key], "relation"):
                        qedge_relation = self.message.query_graph.edges[edge_key].relation
                    if self.message.query_graph.edges[edge_key].subject == subject_qnode_key and self.message.query_graph.edges[edge_key].object == object_qnode_key and qedge_relation == None:
                        query_edge_key.update([edge_key])  # only actual query edge is added
                    elif self.message.query_graph.edges[edge_key].subject == object_qnode_key and self.message.query_graph.edges[edge_key].object == subject_qnode_key and qedge_relation == None:
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
            for node_key, node in self.message.knowledge_graph.nodes.items():
                nodes_info[node_key] = {'qnode_keys': node.qnode_keys, 'category': self.message.knowledge_graph.nodes[node_key].categories[0]}
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving nodes in message KG")
            return self.response

        ## loop over all edges in KG and create subject node list and target node dict based on subject_qnode_key, object_qnode_key as well as rel_edge_id (optional, otherwise all edges are considered)
        try:
            for edge_key, edge in self.message.knowledge_graph.edges.items():

                edge_attribute_list = [x.value for x in self.message.knowledge_graph.edges[edge_key].attributes if x.original_attribute_name == 'is_defined_by']
                if len(edge_attribute_list) == 0:

                    ## Collect all knowldge source information for each edge between queried qnode_keys (eg. 'n01', 'n02')
                    temp_kp = []
                    for x in self.message.knowledge_graph.edges[edge_key].attributes:
                        if x.attribute_type_id == 'biolink:aggregator_knowledge_source' or x.attribute_type_id == 'biolink:knowledge_source':
                            temp_kp += self._change_kp_name(x.value)
                    if 'arax' in temp_kp:
                        temp_kp.remove('arax')

                    if rel_edge_key:
                        if rel_edge_key in edge.qedge_keys:
                            if subject_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].subject]['qnode_keys']:
                                edge_expand_kp.extend(temp_kp)
                                rel_edge_type.update([self.message.knowledge_graph.edges[edge_key].predicate])
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].subject)
                                if self.message.knowledge_graph.edges[edge_key].object not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object] = {self.message.knowledge_graph.edges[edge_key].subject}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object].update([self.message.knowledge_graph.edges[edge_key].subject])
                            else:
                                edge_expand_kp.extend(temp_kp)
                                rel_edge_type.update([self.message.knowledge_graph.edges[edge_key].predicate])
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].object)
                                if self.message.knowledge_graph.edges[edge_key].subject not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject] = {self.message.knowledge_graph.edges[edge_key].object}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject].update([self.message.knowledge_graph.edges[edge_key].object])
                    else:
                        if subject_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].subject]['qnode_keys']:
                            if object_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].object]['qnode_keys']:
                                edge_expand_kp.extend(temp_kp)
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].subject)
                                if self.message.knowledge_graph.edges[edge_key].object not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object] = {self.message.knowledge_graph.edges[edge_key].subject}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].object].update([self.message.knowledge_graph.edges[edge_key].subject])

                        elif object_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].subject]['qnode_keys']:
                            if subject_qnode_key in nodes_info[self.message.knowledge_graph.edges[edge_key].object]['qnode_keys']:
                                edge_expand_kp.extend(temp_kp)
                                subject_node_list.append(self.message.knowledge_graph.edges[edge_key].object)
                                if self.message.knowledge_graph.edges[edge_key].subject not in object_node_dict.keys():
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject] = {self.message.knowledge_graph.edges[edge_key].object}
                                else:
                                    object_node_dict[self.message.knowledge_graph.edges[edge_key].subject].update([self.message.knowledge_graph.edges[edge_key].object])

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
            self.response.warning(f"More than one knowledge provider were detected to be used for expanding the edges connected to both subject node with qnode key {subject_qnode_key} and object node with qnode key {object_qnode_key}")
            self.response.warning(f"The knowledge provider {kp} was used to calculate Fisher's exact test because it has the maximum number of edges connected to both subject node with qnode key {subject_qnode_key} and object node with qnode key {object_qnode_key}")

        ## check if kp is "ARAX/KG1" or "RTX-KG2", if not, report error
        if kp == "rtx_kg1_kp":
            kp = 'ARAX/KG1'
        elif kp == "rtx-kg2":
            kp = 'RTX-KG2'
        else:
            kp = 'RTX-KG2'
            self.response.warning(f"Most of edges between the subject node with qnode key {subject_qnode_key} and object node with qnode key {object_qnode_key} are from {kp} rather than RTX-KG2. But we can't access the total number of nodes with specific node type from {kp}, so RTX-KG2 was still used to calcualte Fisher's exact test.")

        if kp == 'ARAX/KG1':
            ## This warning can be removed once KG1 is deprecated
            self.response.warning(f"Since KG1 will be deprecated soon and the total count of nodes is based on kg2c, currently querying with 'expand(kp=ARAX/KG1)' might cause little discrepancy for FET probability.")

        ## Print out some information used to calculate FET
        if len(subject_node_list) == 1:
            self.response.debug(f"{len(subject_node_list)} subject node with qnode key {subject_qnode_key} and node type {subject_node_category[0]} was found in message KG and used to calculate Fisher's Exact Test")
        else:
            self.response.debug(f"{len(subject_node_list)} subject nodes with qnode key {subject_qnode_key} and node type {subject_node_category[0]} was found in message KG and used to calculate Fisher's Exact Test")
        if len(object_node_dict) == 1:
            self.response.debug(f"{len(object_node_dict)} object node with qnode key {object_qnode_key} and node type {object_node_category[0]} was found in message KG and used to calculate Fisher's Exact Test")
        else:
            self.response.debug(f"{len(object_node_dict)} object nodes with qnode key {object_qnode_key} and node type {object_node_category[0]} was found in message KG and used to calculate Fisher's Exact Test")


        # find all nodes with the same type of 'subject_qnode_key' nodes in specified KP ('ARAX/KG1','RTX-KG2') that are adjacent to target nodes
        # if rel_edge_key is not None, query adjacent node from database otherwise query adjacent node with DSL command by providing a list of query nodes to add_qnode()
        ## Note: Regarding of whether kp='ARAX/KG1' or kp='RTX-KG2', it will always query adjacent node count based on kg2c
        if rel_edge_key:
            if len(rel_edge_type) == 1:  # if the edge with rel_edge_key has only type, we use this rel_edge_predicate to find all subject nodes in KP
                self.response.debug(f"{kp} and edge relation type {list(rel_edge_type)[0]} were used to calculate total object nodes in Fisher's Exact Test")
                result = self.query_size_of_adjacent_nodes(node_curie=list(object_node_dict.keys()), source_type=object_node_category[0], adjacent_type=subject_node_category[0], kp=kp, rel_type=list(rel_edge_type)[0])
            else:  # if the edge with rel_edge_key has more than one type or no edge, we ignore the edge predicate and use all categories to find all subject nodes in KP
                if len(rel_edge_key) == 0:
                    self.response.warning(f"The edges with specified qedge key {rel_edge_key} have no category, we ignore the edge predicate and use all categories to calculate Fisher's Exact Test")
                else:
                    self.response.warning(f"The edges with specified qedge key {rel_edge_key} have more than one category, we ignore the edge predicate and use all categories to calculate Fisher's Exact Test")
                self.response.debug(f"RTX-KG2 was used to calculate total object nodes in Fisher's Exact Test")
                result = self.query_size_of_adjacent_nodes(node_curie=list(object_node_dict.keys()), source_type=object_node_category[0], adjacent_type=subject_node_category[0], kp='RTX-KG2', rel_type=None)
        else:  # if no rel_edge_key is specified, we ignore the edge predicate and use all categories to find all subject nodes in KP
            self.response.debug(f"RTX-KG2 was used to calculate total object nodes in Fisher's Exact Test")
            result = self.query_size_of_adjacent_nodes(node_curie=list(object_node_dict.keys()), source_type=object_node_category[0], adjacent_type=subject_node_category[0], kp='RTX-KG2', rel_type=None)

        if result is None:
            return self.response  ## Something wrong happened for querying the adjacent nodes
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

        if len(object_node_dict) != 0:
            ## Based on KP detected in message KG, find the total count of node with the same type of source node
            ## Note: Regardless of whether kg='KG1' or kg='KG2' is specified in self.size_of_given_type_in_KP, it will always query total count based on kg2c
            if kp=='ARAX/KG1' or kp=='RTX-KG2':
                size_of_total = self.size_of_given_type_in_KP(node_type=subject_node_category[0])
                self.response.debug(f"Total {size_of_total} unique concepts with node category {subject_node_category[0]} was found in KG2c based on 'nodesynonymizer.get_total_entity_count' and this number will be used for Fisher's Exact Test")
            else:
                self.response.error(f"Only KG1 or KG2 is allowable to calculate the Fisher's exact test temporally")
                return self.response

            size_of_query_sample = len(subject_node_list)

            self.response.debug(f"Computing Fisher's Exact Test P-value")
            # calculate FET p-value for each target node in parallel

            parameter_list = []
            del_list = []
            for node in object_node_dict:
                temp = [len(object_node_dict[node]), size_of_object[node]-len(object_node_dict[node]), size_of_query_sample - len(object_node_dict[node]), (size_of_total - size_of_object[node]) - (size_of_query_sample - len(object_node_dict[node]))]
                if any([value < 0 for value in temp]) is True:
                    del_list.append(node)
                    self.response.warning(f"Skipping node {node} to calculate FET p-value due to issue1438 (which causes negative value).")

            for del_node in del_list:
                del object_node_dict[del_node]
            parameter_list = [(node, len(object_node_dict[node]), size_of_object[node]-len(object_node_dict[node]), size_of_query_sample - len(object_node_dict[node]), (size_of_total - size_of_object[node]) - (size_of_query_sample - len(object_node_dict[node]))) for node in object_node_dict]

            try:
                # with multiprocessing.Pool() as executor:
                #     FETpvalue_list = [elem for elem in executor.map(self._calculate_FET_pvalue_parallel, parameter_list)]
                FETpvalue_list = [elem for elem in map(self._calculate_FET_pvalue_parallel, parameter_list)]
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
                    EdgeAttribute(attribute_type_id="EDAM:data_1669", original_attribute_name="fisher_exact_test_p-value", value=str(value[1]), value_url=None),
                    EdgeAttribute(original_attribute_name="virtual_relation_label", value=value[0], attribute_type_id="biolink:Unknown"),
                    #EdgeAttribute(original_attribute_name="is_defined_by", value="ARAX", attribute_type_id="biolink:Unknown"),
                    EdgeAttribute(original_attribute_name="defined_datetime", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attribute_type_id="metatype:Datetime"),
                    EdgeAttribute(original_attribute_name="provided_by", value="infores:arax", attribute_type_id="biolink:aggregator_knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                    EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="biolink:computed_value", attribute_source="infores:arax-reasoner-ara", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges.")
                    #EdgeAttribute(original_attribute_name="confidence", value=None, type="biolink:ConfidenceLevel"),
                    #EdgeAttribute(original_attribute_name="weight", value=None, type="metatype:Float")
                ]
                edge_id = f"{value[0]}_{index}"
                edge = Edge(predicate='biolink:has_fisher_exact_test_p_value_with', subject=value[2], object=value[3],
                            attributes=edge_attribute_list)
                edge.qedge_keys = [value[0]]

                self.message.knowledge_graph.edges[edge_id] = edge

                if self.message.results is not None and len(self.message.results) > 0:
                    ou.update_results_with_overlay_edge(subject_knode_key=value[2], object_knode_key=value[3], kedge_key=edge_id, message=self.message, log=self.response)

                count = count + 1

            self.response.debug(f"{count} new virtual edges were added to message KG")

            # add the virtual edge to message QG
            if count > 0:
                self.response.debug(f"Adding virtual edge to message QG")
                edge_type = ["biolink:has_fisher_exact_test_p_value_with"]
                option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key,
                                                                          self.message.query_graph, self.response)
                qedge_id = virtual_relation_label
                q_edge = QEdge(predicates=edge_type,
                               subject=subject_qnode_key, object=object_qnode_key,
                               option_group_id=option_group_id)
                q_edge.relation = virtual_relation_label
                self.message.query_graph.edges[qedge_id] = q_edge
                self.response.debug(f"One virtual edge was added to message QG")

        return self.response


    def query_size_of_adjacent_nodes(self, node_curie, source_type, adjacent_type, kp="RTX-KG2", rel_type=None):
        """
        Query adjacent nodes of a given source node based on adjacent node type.
        :param node_curie: (required) the curie id of query node. It accepts both single curie id or curie id list eg. "UniProtKB:P14136" or ['UniProtKB:P02675', 'UniProtKB:P01903', 'UniProtKB:P09601', 'UniProtKB:Q02878']
        :param source_type: (required) the type of source node, eg. "gene"
        :param adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        :param kp: (optional) the knowledge provider to use, eg. "RTX-KG2"(default)
        :param rel_type: (optional) edge type to consider, eg. "involved_in"
        :return a tuple with a dict containing the number of adjacent nodes for the query node and a list of removed nodes
        """

        res = None
        source_type = ComputeFTEST.convert_string_to_snake_case(source_type.replace('biolink:',''))
        source_type = ComputeFTEST.convert_string_biolinkformat(source_type)
        adjacent_type = ComputeFTEST.convert_string_to_snake_case(adjacent_type.replace('biolink:',''))
        adjacent_type = ComputeFTEST.convert_string_biolinkformat(adjacent_type)

        if rel_type is None:
            nodesynonymizer = NodeSynonymizer()
            normalized_nodes = nodesynonymizer.get_canonical_curies(node_curie)
            failure_nodes = list()
            mapping = {node:normalized_nodes[node]['preferred_curie'] for node in normalized_nodes if normalized_nodes[node] is not None}
            failure_nodes += list(normalized_nodes.keys() - mapping.keys())
            query_nodes = list(set(mapping.values()))
            query_nodes = [curie_id.replace("'", "''") if "'" in curie_id else curie_id for curie_id in query_nodes]
            # special_curie_ids = [curie_id for curie_id in query_nodes if "'" in curie_id]

            # Get connected to kg2c sqlite
            connection = sqlite3.connect(self.sqlite_file_path)
            cursor = connection.cursor()

            # Extract the neighbor count data
            node_keys_str = "','".join(query_nodes)  # SQL wants ('node1', 'node2') format for string lists
            sql_query = f"SELECT N.id, N.neighbor_counts " \
                        f"FROM neighbors AS N " \
                        f"WHERE N.id IN ('{node_keys_str}')"
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            rows = [curie_id.replace("\'","'").replace("''", "'") if "'" in curie_id else curie_id for curie_id in rows]
            connection.close()

            # Load the counts into a dictionary
            neighbor_counts_dict = {row[0]:eval(row[1]) for row in rows}

            res_dict = {node:neighbor_counts_dict[mapping[node]].get(adjacent_type) for node in mapping if mapping[node] in neighbor_counts_dict and neighbor_counts_dict[mapping[node]].get(adjacent_type) is not None}
            failure_nodes += list(mapping.keys() - res_dict.keys())

            if len(failure_nodes) != 0:
                return (res_dict, failure_nodes)
            else:
                return (res_dict, [])

        else:
            if kp == 'ARAX/KG1':
                self.response.warning(f"Since the edge type '{rel_type}' is from KG1, we still use the DSL expand(kg=ARAX/KG1) to query neighbor count. However, the total node count is based on KG2c from 'nodesynonymizer.get_total_entity_count'. So the FET result might not be accurate.")

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
                self.response.error("The 'node_curie' argument of 'query_size_of_adjacent_nodes' method within FET only accepts str or list")
                return res

            # call the method of ARAXQuery class to query adjacent node
            query = {"operations": {"actions": [
                "create_message",
                f"add_qnode(ids={query_node_curie}, categories={source_type}, key=FET_n00)",
                f"add_qnode(categories={adjacent_type}, key=FET_n01)",
                f"add_qedge(subject=FET_n00, object=FET_n01, key=FET_e00, predicates={rel_type})",
                f"expand(edge_key=FET_e00,kp={kp})",
                #"resultify()",
                "return(message=true, store=false)"
            ]}}

            try:
                result = araxq.query(query)
                if result.status != 'OK':
                    self.response.error(f"Fail to query adjacent nodes from RTX-KG2 for {node_curie}")
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
                        failure_nodes = list()
                        for node in node_curie:
                            tmplist = set([edge_key for edge_key in message.knowledge_graph.edges if message.knowledge_graph.edges[edge_key].subject == node or message.knowledge_graph.edges[edge_key].object == node])  ## edge has no direction
                            if len(tmplist) == 0:
                                self.response.warning(f"Fail to query adjacent nodes from {kp} for {node} in FET probably because expander ignores node type. For more details, please see issue897.")
                                failure_nodes.append(node)
                                check_empty = True
                                continue
                            res_dict[node] = len(tmplist)

                        if check_empty is True:
                            return (res_dict,failure_nodes)
                        else:
                            return (res_dict,[])
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with querying adjacent nodes from {kp} for {node_curie}")
                return res

    def size_of_given_type_in_KP(self, node_type):
        """
        find all nodes of a certain type in KP
        :param node_type: the query node type
        :param kg: only allowed for choosing 'KG1' or 'KG2' now. Will extend to BTE later
        """
        # TODO: extend this to KG2, BTE, and other KP's we know of

        size_of_total = None

        node_type = ComputeFTEST.convert_string_to_snake_case(node_type.replace('biolink:',''))
        node_type = ComputeFTEST.convert_string_biolinkformat(node_type)

        # Get connected to kg2c sqlite
        connection = sqlite3.connect(self.sqlite_file_path)
        cursor = connection.cursor()

        # Extract total count of nodes with certain type in kg2c
        sql_query = f"SELECT C.count " \
                    f"FROM category_counts AS C " \
                    f"WHERE C.category = '{node_type}'"

        cursor.execute(sql_query)
        rows = cursor.fetchall()
        size_of_total = rows[0][0]
        connection.close()

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
            contingency_table = [[a, b], [c, d]]
            pvalue = stats.fisher_exact(contingency_table)[1]
            return (node, pvalue)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            error_message.append((tb, error_type.__name__))
            error_message.append(f"Something went wrong for target node {node} to calculate FET p-value")
            error_message.append(f"a, b, c, d are respectively {a}, {b}, {c}, {d} ")
            return error_message

    @staticmethod
    def convert_string_to_snake_case(input_string: str) -> str:
        # Converts a string like 'ChemicalEntity' or 'chemicalEntity' to 'chemical_entity'
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

    @staticmethod
    def _change_kp_name(name) -> list:

        if type(name) is str:
            return [re.sub("infores:", "", name)]
        else:
            return [re.sub("infores:", "", x) for x in name]
