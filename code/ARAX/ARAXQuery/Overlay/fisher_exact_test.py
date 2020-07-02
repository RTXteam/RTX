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
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.edge import Edge
from swagger_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/kg-construction/")
from KGNodeIndex import KGNodeIndex
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
        if 'source_qnode_id' not in self.parameters:
            self.response.error(f"The argument 'source_qnode_id' is required for fisher_exact_test function")
            return self.response
        else:
            source_qnode_id = self.parameters['source_qnode_id']
        if 'virtual_relation_label' not in self.parameters:
            self.response.error(f"The argument 'virtual_relation_label' is required for fisher_exact_test function")
            return self.response
        else:
            virtual_relation_label = str(self.parameters['virtual_relation_label'])
        if 'target_qnode_id' not in self.parameters:
            self.response.error(f"The argument 'target_qnode_id' is required for fisher_exact_test function")
            return self.response
        else:
            target_qnode_id = self.parameters['target_qnode_id']
        rel_edge_id = self.parameters['rel_edge_id'] if 'rel_edge_id' in self.parameters else None
        top_n = int(self.parameters['top_n']) if 'top_n' in self.parameters else None
        cutoff = float(self.parameters['cutoff']) if 'cutoff' in self.parameters else None

        # initialize some variables
        nodes_info = {}
        edge_expand_kp = []
        source_node_list = []
        target_node_dict = {}
        size_of_target = {}
        source_node_exist = False
        target_node_exist = False
        query_edge_id = set()
        rel_edge_type = set()
        source_node_type = None
        target_node_type = None

        ## Check if source_qnode_id and target_qnode_id are in the Query Graph
        try:
            if len(self.message.query_graph.nodes) != 0:
                for node in self.message.query_graph.nodes:
                    if node.id == source_qnode_id:
                        source_node_exist = True
                        source_node_type = node.type
                    elif node.id == target_qnode_id:
                        target_node_exist = True
                        target_node_type = node.type
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

        if source_node_exist:
            if target_node_exist:
                pass
            else:
                self.response.error(f"No query node with target qnode id {target_qnode_id} detected in QG for Fisher's Exact Test")
                return self.response
        else:
            self.response.error(f"No query node with source qnode id {source_qnode_id} detected in QG for Fisher's Exact Test")
            return self.response

        ## Check if there is a query edge connected to both source_qnode_id and target_qnode_id in the Query Graph
        try:
            if len(self.message.query_graph.edges) != 0:
                for edge in self.message.query_graph.edges:
                    if edge.source_id == source_qnode_id and edge.target_id == target_qnode_id and edge.relation == None:
                        query_edge_id.update([edge.id]) # only actual query edge is added
                    elif edge.source_id == target_qnode_id and edge.target_id == source_qnode_id and edge.relation == None:
                        query_edge_id.update([edge.id]) # only actual query edge is added
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

        if len(query_edge_id)!=0:
            if rel_edge_id:
                if rel_edge_id in query_edge_id:
                    pass
                else:
                    self.response.error(f"No query edge with qedge id {rel_edge_id} connected to both source node with qnode id {source_qnode_id} and target node with qnode id {target_qnode_id} detected in QG for Fisher's Exact Test")
                    return self.response
            else:
                pass
        else:
            self.response.error(
                f"No query edge connected to both source node with qnode id {source_qnode_id} and target node with qnode id {target_qnode_id} detected in QG for Fisher's Exact Test")
            return self.response

        ## loop over all nodes in KG and collect their node information
        try:
            count = 0
            for node in self.message.knowledge_graph.nodes:
                nodes_info[node.id] = {'count': count, 'qnode_ids': node.qnode_ids, 'type': node.type[0], 'edge_index': []}
                count = count + 1
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving nodes in message KG")
            return self.response

        ## loop over all edges in KG and create source node list and target node dict based on source_qnode_id, target_qnode_id as well as rel_edge_id (optional, otherwise all edges are considered)
        try:
            count = 0
            for edge in self.message.knowledge_graph.edges:
                if edge.provided_by != "ARAX":

                    nodes_info[edge.source_id]['edge_index'].append(count)
                    nodes_info[edge.target_id]['edge_index'].append(count)

                    if rel_edge_id:
                        if rel_edge_id in edge.qedge_ids:
                            if source_qnode_id in nodes_info[edge.source_id]['qnode_ids']:
                                edge_expand_kp.append(edge.is_defined_by)
                                rel_edge_type.update([edge.type])
                                source_node_list.append(edge.source_id)
                                if edge.target_id not in target_node_dict.keys():
                                    target_node_dict[edge.target_id] = {edge.source_id}
                                else:
                                    target_node_dict[edge.target_id].update([edge.source_id])
                            else:
                                edge_expand_kp.append(edge.is_defined_by)
                                rel_edge_type.update([edge.type])
                                source_node_list.append(edge.target_id)
                                if edge.source_id not in target_node_dict.keys():
                                    target_node_dict[edge.source_id] = {edge.target_id}
                                else:
                                    target_node_dict[edge.source_id].update([edge.target_id])
                        else:
                            pass
                    else:
                        if source_qnode_id in nodes_info[edge.source_id]['qnode_ids']:
                            if target_qnode_id in nodes_info[edge.target_id]['qnode_ids']:
                                edge_expand_kp.append(edge.is_defined_by)
                                source_node_list.append(edge.source_id)
                                if edge.target_id not in target_node_dict.keys():
                                    target_node_dict[edge.target_id] = {edge.source_id}
                                else:
                                    target_node_dict[edge.target_id].update([edge.source_id])

                            else:
                                pass
                        elif target_qnode_id in nodes_info[edge.source_id]['qnode_ids']:
                            if source_qnode_id in nodes_info[edge.target_id]['qnode_ids']:
                                edge_expand_kp.append(edge.is_defined_by)
                                source_node_list.append(edge.target_id)
                                if edge.source_id not in target_node_dict.keys():
                                    target_node_dict[edge.source_id] = {edge.target_id}
                                else:
                                    target_node_dict[edge.source_id].update([edge.target_id])

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

        source_node_list = list(set(source_node_list)) ## remove the duplicate source node id

        ## check if there is no source node in message KG
        if len(source_node_list) == 0:
            self.response.error(f"No source node found in message KG for Fisher's Exact Test")
            return self.response

        ## check if there is no target node in message KG
        if len(target_node_dict) == 0:
            self.response.error(f"No target node found in message KG for Fisher's Exact Test")
            return self.response

        ## check if source node has more than one type. If so, throw an error
        if source_node_type is None:
            self.response.error(f"Source node with qnode id {source_qnode_id} was set to None in Query Graph. Please specify the node type")
            return self.response
        else:
            pass

        ## check if target node has more than one type. If so, throw an error
        if target_node_type is None:
            self.response.error(f"Target node with qnode id {target_qnode_id} was set to None in Query Graph. Please specify the node type")
            return self.response
        else:
            pass

        ##check how many kps were used in message KG. If more than one, the one with the max number of edges connnected to both source nodes and target nodes was used
        if len(collections.Counter(edge_expand_kp))==1:
            kp = edge_expand_kp[0]
        else:
            occurrences = collections.Counter(edge_expand_kp)
            max_index = max([(value, index) for index, value in enumerate(occurrences.values())])[1] # if there are more than one kp having the maximum number of edges, then the last one based on alphabetical order will be chosen.
            kp = list(occurrences.keys())[max_index]
            self.response.debug(f"{occurrences}")
            self.response.warning(f"More than one knowledge provider was detected to be used for expanding the edges connected to both source node with qnode id {source_qnode_id} and target node with qnode id {target_qnode_id}")
            self.response.warning(f"The knowledge provider {kp} was used to calculate Fisher's exact test because it has the maximum number of edges both source node with qnode id {source_qnode_id} and target node with qnode id {target_qnode_id}")

        ## Print out some information used to calculate FET
        if len(source_node_list) == 1:
            self.response.debug(f"{len(source_node_list)} source node with qnode id {source_qnode_id} and node type {source_node_type} was found in message KG and used to calculate Fisher's Exact Test")
        else:
            self.response.debug(f"{len(source_node_list)} source nodes with qnode id {source_qnode_id} and node type {source_node_type} was found in message KG and used to calculate Fisher's Exact Test")
        if len(target_node_dict) == 1:
            self.response.debug(f"{len(target_node_dict)} target node with qnode id {target_qnode_id} and node type {target_node_type} was found in message KG and used to calculate Fisher's Exact Test")
        else:
            self.response.debug(f"{len(target_node_dict)} target nodes with qnode id {target_qnode_id} and node type {target_node_type} was found in message KG and used to calculate Fisher's Exact Test")


        # find all nodes with the same type of 'source_qnode_id' nodes in specified KP ('ARAX/KG1','ARAX/KG2','BTE') that are adjacent to target nodes
        use_parallel = False

        if not use_parallel:
            # query adjacent node in one DSL command by providing a list of query nodes to add_qnode()
            if rel_edge_id:
                if len(rel_edge_type) == 1:  # if the edge with rel_edge_id has only type, we use this rel_edge_type to find all source nodes in KP
                    self.response.debug(f"{kp} and edge relation type {list(rel_edge_type)[0]} were used to calculate total adjacent nodes in Fisher's Exact Test")
                    result = self.query_size_of_adjacent_nodes(node_curie=list(target_node_dict.keys()), adjacent_type=source_node_type, kp = kp, rel_type=list(rel_edge_type)[0], use_cypher_command=False)
                else:  # if the edge with rel_edge_id has more than one type, we ignore the edge type and use all types to find all source nodes in KP
                    self.response.warning(f"The edges with specified qedge id {rel_edge_id} have more than one type, we ignore the edge type and use all types to calculate Fisher's Exact Test")
                    self.response.debug(f"{kp} was used to calculate total adjacent nodes in Fisher's Exact Test")
                    result = self.query_size_of_adjacent_nodes(node_curie=list(target_node_dict.keys()), adjacent_type=source_node_type, kp=kp, rel_type=None, use_cypher_command=False)
            else:  # if no rel_edge_id is specified, we ignore the edge type and use all types to find all source nodes in KP
                self.response.debug(f"{kp} was used to calculate total adjacent nodes in Fisher's Exact Test")
                result = self.query_size_of_adjacent_nodes(node_curie=list(target_node_dict.keys()), adjacent_type=source_node_type, kp=kp, rel_type=None, use_cypher_command=False)

            if result is None:
                return self.response ## Something wrong happened for querying the adjacent nodes
            else:
                size_of_target = result
        else:
            # query adjacent node for query nodes one by one in parallel
            if rel_edge_id:
                if len(rel_edge_type) == 1:  # if the edge with rel_edge_id has only type, we use this rel_edge_type to find all source nodes in KP
                    self.response.debug(f"{kp} and edge relation type {list(rel_edge_type)[0]} were used to calculate total adjacent nodes in Fisher's Exact Test")
                    parameter_list = [(node, source_node_type, kp, list(rel_edge_type)[0]) for node in list(target_node_dict.keys())]
                else:  # if the edge with rel_edge_id has more than one type, we ignore the edge type and use all types to find all source nodes in KP
                    self.response.warning(f"The edges with specified qedge id {rel_edge_id} have more than one type, we ignore the edge type and use all types to calculate Fisher's Exact Test")
                    self.response.debug(f"{kp} was used to calculate total adjacent nodes in Fisher's Exact Test")
                    parameter_list = [(node, source_node_type, kp, None) for node in list(target_node_dict.keys())]
            else:  # if no rel_edge_id is specified, we ignore the edge type and use all types to find all source nodes in KP
                self.response.debug(f"{kp} was used to calculate total adjacent nodes in Fisher's Exact Test")
                parameter_list = [(node, source_node_type, kp, None) for node in list(target_node_dict.keys())]

            ## get the count of all nodes with the type of 'source_qnode_id' nodes in KP for each target node in parallel
            try:
                with multiprocessing.Pool() as executor:
                    target_count_res = [elem for elem in executor.map(self._query_size_of_adjacent_nodes_parallel, parameter_list)]
                    executor.close()
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with querying adjacent nodes in parallel")
                return self.response

            if any([type(elem) is list for elem in target_count_res]):
                for msg in [elem2 for elem1 in target_count_res if type(elem1) is list for elem2 in elem1]:
                    if type(msg) is tuple:
                        self.response.error(msg[0], error_code=msg[1])
                    else:
                        self.response.error(msg)
                return self.response  ## Something wrong happened for querying the adjacent nodes
            else:
                for index in range(len(target_node_dict)):
                    node = list(target_node_dict.keys())[index]
                    size_of_target[node] = target_count_res[index]

        ## Based on KP detected in message KG, find the total number of node with the same type of source node
        if kp=='ARAX/KG1':
            size_of_total = self.size_of_given_type_in_KP(node_type=source_node_type,use_cypher_command=True, kg='KG1') ## Try cypher query first
            if size_of_total is not None:
                if size_of_total != 0:
                    self.response.debug(f"ARAX/KG1 and cypher query were used to calculate total number of node with the same type of source node in Fisher's Exact Test")
                    self.response.debug(f"Total {size_of_total} nodes with node type {source_node_type} was found in ARAX/KG1")
                    pass
                else:
                    size_of_total = self.size_of_given_type_in_KP(node_type=source_node_type, use_cypher_command=False, kg='KG1') ## If cypher query fails, then try kgNodeIndex
                    if size_of_total==0:
                        self.response.error(f"KG1 has 0 node with the same type of source node with qnode id {source_qnode_id}")
                        return self.response
                    else:
                        self.response.debug(f"ARAX/KG1 and kgNodeIndex were used to calculate total number of node with the same type of source node in Fisher's Exact Test")
                        self.response.debug(f"Total {size_of_total} nodes with node type {source_node_type} was found in ARAX/KG1")
                        pass
            else:
                return self.response ## Something wrong happened for querying total number of node with the same type of source node

        elif kp=='ARAX/KG2':
            ## check KG1 first as KG2 might have many duplicates. If KG1 is 0, then check KG2
            size_of_total = self.size_of_given_type_in_KP(node_type=source_node_type, use_cypher_command=True, kg='KG1') ## Try cypher query first
            if size_of_total is not None:
                if size_of_total!=0:
                    self.response.warning(f"Although ARAX/KG2 was found to have the maximum number of edges connected to both {source_qnode_id} and {target_qnode_id}, ARAX/KG1 and cypher query were used to find the total number of nodes with the same type of source node with qnode id {source_qnode_id} as KG2 might have many duplicates")
                    self.response.debug(f"Total {size_of_total} nodes with node type {source_node_type} was found in ARAX/KG1")
                    pass
                else:
                    size_of_total = self.size_of_given_type_in_KP(node_type=source_node_type, use_cypher_command=False, kg='KG1') ## If cypher query fails, then try kgNodeIndex
                    if size_of_total is not None:
                        if size_of_total != 0:
                            self.response.warning(f"Although ARAX/KG2 was found to have the maximum number of edges connected to both {source_qnode_id} and {target_qnode_id}, ARAX/KG1 and kgNodeIndex were used to find the total number of nodes with the same type of source node with qnode id {source_qnode_id} as KG2 might have many duplicates")
                            self.response.debug(f"Total {size_of_total} nodes with node type {source_node_type} was found in ARAX/KG1")
                            pass
                        else:
                            size_of_total = self.size_of_given_type_in_KP(node_type=source_node_type, use_cypher_command=False, kg='KG2')
                            if size_of_total is None:
                                return self.response  ## Something wrong happened for querying total number of node with the same type of source node
                            elif size_of_total==0:
                                self.response.error(f"KG2 has 0 node with the same type of source node with qnode id {source_qnode_id}")
                                return self.response
                            else:
                                self.response.debug(f"ARAX/KG2 and kgNodeIndex were used to calculate total number of node with the same type of source node in Fisher's Exact Test")
                                self.response.debug(f"Total {size_of_total} nodes with node type {source_node_type} was found in ARAX/KG2")
                                pass
                    else:
                        return self.response  ## Something wrong happened for querying total number of node with the same type of source node
            else:
                return self.response  ## Something wrong happened for querying total number of node with the same type of source node
        else:
            self.response.error(f"Only KG1 or KG2 is allowable to calculate the Fisher's exact test temporally")
            return self.response

        size_of_query_sample = len(source_node_list)


        self.response.debug(f"Computing Fisher's Exact Test P-value")
        # calculate FET p-value for each target node in parallel
        parameter_list = [(node, len(target_node_dict[node]), size_of_target[node]-len(target_node_dict[node]), size_of_query_sample - len(target_node_dict[node]), (size_of_total - size_of_target[node]) - (size_of_query_sample - len(target_node_dict[node]))) for node in target_node_dict]

        try:
            with multiprocessing.Pool() as executor:
                FETpvalue_list = [elem for elem in executor.map(self._calculate_FET_pvalue_parallel, parameter_list)]
                executor.close()
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

        virtual_edge_list = [Edge(id=f"{value[0]}_{index}",
                                  type='has_fisher_exact_test_p-value_with',
                                  relation=value[0],
                                  source_id=value[2],
                                  target_id=value[3],
                                  is_defined_by="ARAX",
                                  defined_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  provided_by="ARAX",
                                  confidence=None,
                                  weight=None,
                                  edge_attributes=[EdgeAttribute(type="data:1669", name="fisher_exact_test_p-value", value=str(value[1]), url=None)],
                                  qedge_ids=[value[0]]) for index, value in enumerate([(virtual_relation_label, output[adj], node, adj) for adj in target_node_dict if adj in output.keys() for node in target_node_dict[adj]], 1)]

        self.message.knowledge_graph.edges.extend(virtual_edge_list)

        count = len(virtual_edge_list)

        self.response.debug(f"{count} new virtual edges were added to message KG")

        # add the virtual edge to message QG
        if count > 0:
            self.response.debug(f"Adding virtual edge to message QG")
            edge_type = "has_fisher_exact_test_p-value_with"
            q_edge = QEdge(id=virtual_relation_label, type=edge_type, relation=virtual_relation_label,
                           source_id=source_qnode_id, target_id=target_qnode_id)
            self.message.query_graph.edges.append(q_edge)
            self.response.debug(f"One virtual edge was added to message QG")

        return self.response


    def query_size_of_adjacent_nodes(self, node_curie, adjacent_type, kp="ARAX/KG1", rel_type=None, use_cypher_command=True):
        """
        Query adjacent nodes of a given source node based on adjacent node type.
        :param node_curie: (required) the curie id of query node. It accepts both single curie id or curie id list eg. "UniProtKB:P14136" or ['UniProtKB:P02675', 'UniProtKB:P01903', 'UniProtKB:P09601', 'UniProtKB:Q02878']
        :param adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        :param kp: (optional) the knowledge provider to use, eg. "ARAX/KG1"(default)
        :param rel_type: (optional) edge type to consider, eg. "involved_in"
        :param use_cypher_command: Boolean (True or False). If True, it used cypher command to the size of query adjacent nodes(default:True)
        :return the number of adjacent nodes for the query node
        """

        res = None

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
                self.response.error(f"The 'kp' argument of 'query_size_of_adjacent_nodes' method within FET only accepts 'ARAX/KG1' or 'ARAX/KG2' right now")
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
                query = {"previous_message_processing_plan": {"processing_actions": [
                    "create_message",
                    f"add_qnode(curie={query_node_curie}, id=FET_n00)",
                    f"add_qnode(type={adjacent_type}, id=FET_n01)",
                    f"add_qedge(source_id=FET_n00, target_id=FET_n01, id=FET_e00, type={rel_type})",
                    f"expand(edge_id=FET_e00,kp={kp})",
                    #"resultify()",
                    "return(message=true, store=false)"
                ]}}
            else:
                query = {"previous_message_processing_plan": {"processing_actions": [
                    "create_message",
                    f"add_qnode(curie={query_node_curie}, id=FET_n00)",
                    f"add_qnode(type={adjacent_type}, id=FET_n01)",
                    f"add_qedge(source_id=FET_n00, target_id=FET_n01, id=FET_e00)",
                    f"expand(edge_id=FET_e00,kp={kp})",
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
                    message = araxq.message
                    if type(node_curie) is str:
                        tmplist = set([edge.id for edge in message.knowledge_graph.edges if edge.source_id == node_curie or edge.target_id == node_curie])  ## edge has no direction
                        if len(tmplist) == 0:
                            self.response.error(f"Fail to query adjacent nodes from {kp} for {node_curie}")
                            return res
                        res_dict[node_curie] = len(tmplist)
                        return res_dict
                    else:
                        check_empty = False
                        for node in node_curie:
                            tmplist = set([edge.id for edge in message.knowledge_graph.edges if edge.source_id == node or edge.target_id == node])  ## edge has no direction
                            if len(tmplist) == 0:
                                self.response.error(f"Fail to query adjacent nodes from {kp} for {node}")
                                check_empty = True
                            res_dict[node] = len(tmplist)
                        if check_empty is True:
                            return res
                        else:
                            return res_dict
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
        :param this is a list containing four sub-arguments below since this function is exectued in parallel.
        :return the number of adjacent nodes for the query node
        """
        #:sub-argument node_curie: (required) the curie id of query node, eg. "UniProtKB:P14136"
        #:sub-argument adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        #:sub-argument kp: (optional) the knowledge provider to use, eg. "ARAX/KG1"(default)
        #:sub-argument rel_type: (optional) edge type to consider, eg. "involved_in"

        error_message = []
        if len(this) == 4:
            # this contains four arguments and assign them to different variables
            node_curie, adjacent_type, kp, rel_type = this
        elif len(this) == 3:
            node_curie, adjacent_type, kp = this
            rel_type = None
        elif len(this) == 2:
            node_curie, adjacent_type = this
            kp = "ARAX/KG1"
            rel_type = None
        else:
            error_message.append("The '_query_size_of_adjacent_nodes_parallel' method within FET only accepts four arguments: node_curie, adjacent_type, kp, rel_type")
            return error_message

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
            query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                f"add_qnode(curie={node_curie}, id=FET_n00)",
                f"add_qnode(type={adjacent_type}, id=FET_n01)",
                f"add_qedge(source_id=FET_n00, target_id=FET_n01, id=FET_e00, type={rel_type})",
                f"expand(edge_id=FET_e00,kp={kp})",
                #"resultify()",
                "return(message=true, store=false)"
            ]}}
        else:
            query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                f"add_qnode(curie={node_curie}, id=FET_n00)",
                f"add_qnode(type={adjacent_type}, id=FET_n01)",
                f"add_qedge(source_id=FET_n00, target_id=FET_n01, id=FET_e00)",
                f"expand(edge_id=FET_e00,kp={kp})",
                #"resultify()",
                "return(message=true, store=false)"
            ]}}

        try:
            result = araxq.query(query)
            if result.status != 'OK':
                error_message.append(f"Fail to query adjacent nodes from {kp} for {node_curie}")
                return error_message
            else:
                message = araxq.message
                tmplist = set([edge.id for edge in message.knowledge_graph.edges if edge.source_id == node_curie or edge.target_id == node_curie]) ## edge has no direction
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

    def size_of_given_type_in_KP(self, node_type, use_cypher_command=True, kg='KG1'):
        """
        find all nodes of a certain type in KP
        :param node_type: the query node type
        :param use_cypher_command: Boolean (True or False). If True, it used cypher command to query all nodes otherwise used kgNodeIndex
        :param kg: only allowed for choosing 'KG1' or 'KG2' now. Will extend to BTE later
        """
        # TODO: extend this to KG2, BTE, and other KP's we know of

        size_of_total = None

        if kg == 'KG1' or kg == 'KG2':
            pass
        else:
            self.response.error(f"Only KG1 or KG2 is allowable to calculate the Fisher's exact test temporally")
            return size_of_total

        if kg == 'KG1':
            if use_cypher_command:
                rtxConfig = RTXConfiguration()
                # Connection information for the neo4j server, populated with orangeboard
                driver = GraphDatabase.driver(rtxConfig.neo4j_bolt,
                                              auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
                session = driver.session()

                query = "MATCH (n:%s) return count(distinct n)" % (node_type)
                res = session.run(query)
                size_of_total = res.single()["count(distinct n)"]
                return size_of_total
            else:
                kgNodeIndex = KGNodeIndex()
                size_of_total = kgNodeIndex.get_total_entity_count(node_type, kg_name=kg)
                return size_of_total
        else:
            if use_cypher_command:
                self.response.warning(f"KG2 is only allowable to use kgNodeIndex to query the total number of node with query type. It was set to use kgNodeIndex")
                kgNodeIndex = KGNodeIndex()
                size_of_total = kgNodeIndex.get_total_entity_count(node_type, kg_name=kg)
                return size_of_total

            else:
                kgNodeIndex = KGNodeIndex()
                size_of_total = kgNodeIndex.get_total_entity_count(node_type, kg_name=kg)
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
