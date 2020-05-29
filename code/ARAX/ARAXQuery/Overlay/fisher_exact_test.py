#!/bin/env python3
# This class will perform fisher's exact test to evalutate the significance of connection between
# a list of nodes with certain type in KG and each of the adjacent nodes with specified type.

# relative imports
import scipy.stats as stats
import traceback
import sys
import os
import concurrent.futures
from datetime import datetime
from neo4j.v1 import GraphDatabase, basic_auth
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../") # code directory
from ARAX_query import ARAXQuery
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.edge import Edge
from swagger_server.models.q_edge import QEdge


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

        self.response.debug(f"Computing Fisher's Exact Test P-value")
        self.response.info(f"Performing Fisher's Exact Test to add p-value to edge attribute of virtual edge")

        # check the input parameters
        if 'query_node_id' not in self.parameters:
            self.response.error(f"The argument 'query_node_id' is required for fisher_exact_test function")
            return self.response
        else:
            query_node_id = self.parameters['query_node_id']
        if 'virtual_edge_type' not in self.parameters:
            self.response.error(f"The argument 'virtual_edge_type' is required for fisher_exact_test function")
            return self.response
        else:
            virtual_edge_type = str(self.parameters['virtual_edge_type'])
        if 'adjacent_node_type' not in self.parameters:
            self.response.error(f"The argument 'adjacent_node_type' is required for fisher_exact_test function")
            return self.response
        else:
            adjacent_node_type = self.parameters['adjacent_node_type']
        query_edge_id = self.parameters['query_edge_id'] if 'query_edge_id' in self.parameters else None
        adjacent_edge_type = self.parameters['adjacent_edge_type'] if 'adjacent_edge_type' in self.parameters else None
        top_n = int(self.parameters['top_n']) if 'top_n' in self.parameters else None
        cutoff = float(self.parameters['cutoff']) if 'cutoff' in self.parameters else None
        if 'added_flag' in self.parameters:
            if self.parameters['added_flag'].upper() == 'TRUE':
                added_flag = True
            else:
                added_flag = False
        else:
            added_flag = True

        # initialize some variables
        nodes_info = {}
        kp = set()
        query_node_list = []
        size_of_adjacent = {}
        adjacent_graph_list = dict()
        adjacent_node_dict = {}
        query_node_type = set()

        # collect input node list for the FET based on provided query node id and edge type
        if query_edge_id:
            # iterate over KG nodes and edges and collect information
            try:
                count = 0
                for node in self.message.knowledge_graph.nodes:
                    nodes_info[node.id] = {'count': count, 'qnode_id': node.qnode_id, 'type': node.type[0],
                                           'edge_index': []}
                    count = count + 1
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with retrieving nodes in message KG")
                return self.response

            try:
                count = 0
                for edge in self.message.knowledge_graph.edges:
                    # edges_info[count] = {'source_id': edge.source_id, 'target_id': edge.target_id, 'type': edge.type}
                    if edge.qedge_id == query_edge_id:
                        if nodes_info[edge.source_id]['qnode_id'] == query_node_id:
                            query_node_list.append(edge.source_id)
                            query_node_type.update([nodes_info[edge.source_id]['type']])
                        elif nodes_info[edge.target_id]['qnode_id'] == query_node_id:
                            query_node_list.append(edge.target_id)
                            query_node_type.update([nodes_info[edge.target_id]['type']])
                        else:
                            continue
                    else:
                        continue
                    kp.update([edge.is_defined_by])
                    nodes_info[edge.source_id]['edge_index'].append(count)
                    nodes_info[edge.target_id]['edge_index'].append(count)
                    count = count + 1
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with retrieving edges in message KG")
                return self.response
        else:
            # iterate over KG nodes and edges and collect information
            try:
                count = 0
                for node in self.message.knowledge_graph.nodes:
                    nodes_info[node.id] = {'count': count, 'qnode_id': node.qnode_id, 'type': node.type[0],
                                           'edge_index': []}
                    if node.qnode_id == query_node_id:
                        query_node_list.append(node.id)
                        query_node_type.update([nodes_info[node.id]['type']])
                    else:
                        continue
                    count = count + 1
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with retrieving nodes in message KG")
                return self.response

            try:
                count = 0
                for edge in self.message.knowledge_graph.edges:
                    kp.update([edge.is_defined_by])
                    nodes_info[edge.source_id]['edge_index'].append(count)
                    nodes_info[edge.target_id]['edge_index'].append(count)
                    count = count + 1
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with retrieving edges in message KG")
                return self.response

        query_node_list = list(set(query_node_list))

        if len(query_node_list) == 0:
            self.response.error(f"No query nodes found in message KG for the FET")
            return self.response

        # Update the original Query Graph
        #qnode = QNode(curie=None, id=f"{query_node_id}_n00", is_set=None, type=adjacent_node_type)
        #self.message.query_graph.nodes.append(qnode)
        # FIXME: This is causing the main issue: the target_id **must** correspond to something in the QG.
        #      Check if the query_target_id is in the QG, if so, just add the virtual edge to the QG
        #      If the query_target_id is not in the QG, add the node the QG
        if added_flag:
            qedge = QEdge(id=virtual_edge_type, source_id=query_node_id, target_id=f"{query_node_id}_{virtual_edge_type}", type="FET")
            self.message.query_graph.edges.append(qedge)

        # find all the nodes adjacent to those in query_node_list with query_node_id in KG
        parament_list = [(node, virtual_edge_type, adjacent_node_type, list(kp)[0], adjacent_edge_type, False) for node in query_node_list]
        with concurrent.futures.ProcessPoolExecutor() as executor:
            adjacent_graph_res = list(executor.map(self.query_adjacent_nodes, parament_list))

        for index in range(len(adjacent_graph_res)):
            if adjacent_graph_res[index].edges:
                adjacent_graph_list[query_node_list[index]] = adjacent_graph_res[index]
                for node in adjacent_graph_res[index].nodes:
                    if node.id != query_node_list[index]:
                        if node.id not in adjacent_node_dict.keys():
                            adjacent_node_dict[node.id] = [query_node_list[index]]
                        else:
                            adjacent_node_dict[node.id].append(query_node_list[index])
            else:
                self.response.warning(
                    f"Node {query_node_list[index]} can't find the adjacent node with {adjacent_node_type} type in {list(kp)[0]}")

        # find all nodes with the type of query_node_id nodes that are associated with adjacent nodes in KG
        parament_list = [(node, f"{virtual_edge_type}_n01", list(query_node_type)[0], list(kp)[0], adjacent_edge_type, True) for node in list(adjacent_node_dict.keys())]
        with concurrent.futures.ProcessPoolExecutor() as executor:
            adjacent_count_res = list(executor.map(self.query_adjacent_nodes, parament_list))

        for index in range(len(adjacent_node_dict)):
            node = list(adjacent_node_dict.keys())[index]
            if adjacent_count_res != -1:
                size_of_adjacent[node] = adjacent_count_res[index]
            else:
                self.response.error(
                    f"The adjacent node {node} can't find the associated nodes with {list(query_node_type)[0]} type in {list(kp)[0]}")
                return self.response

        size_of_total = self.size_of_given_type_in_KP(node_type=list(query_node_type)[0])
        size_of_query_sample = len(query_node_list)

        output = {}
        for node in adjacent_node_dict:  # perform FET for each adjacent node
            contingency_table = [[len(adjacent_node_dict[node]), size_of_adjacent[node]-len(adjacent_node_dict[node])],
                                 [size_of_query_sample - len(adjacent_node_dict[node]), (size_of_total - size_of_adjacent[node]) - (size_of_query_sample - len(adjacent_node_dict[node]))]]
            output[node] = stats.fisher_exact(contingency_table)[1]

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

        # assign the results as node attribute to message
        # FIXME: if the KG source_id and target_id are in the KG, just decorate the virtual edge with the FET edge attribute
        #       if either the KG source_id or the target_id are NOT in the KG, add the appropriate node to the KG (via appending to the message.knowledge_graph.nodes list)
        #       in this later case, you will need to append the WHOLE node object (not just the CURIE). i.e. only object of the class node.py should be appended to message.knowledge_graph.nodes)
        count = 0
        for adj in adjacent_node_dict:
            if adj not in output.keys():
                continue
            else:
                for node in adjacent_node_dict[adj]:
                    for kg_edge in adjacent_graph_list[node].edges:
                        if kg_edge.source_id == adj or kg_edge.target_id == adj:
                            # make the edge, add the attribute
                            id = f"{virtual_edge_type}_{count}"
                            edge_attribute = EdgeAttribute(type="float", name="Fisher Exact Test P-value", value=str(output[adj]), url=None)  # FIXME: will need a url for this
                            now = datetime.now()
                            defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                            edge_type = 'virtual_edge'
                            qedge_id = kg_edge.qedge_id
                            relation = kg_edge.relation
                            is_defined_by = kg_edge.is_defined_by
                            provided_by = "ARAX/RTX"
                            confidence = 1
                            weight = None
                            source_id = kg_edge.source_id
                            target_id = kg_edge.target_id

                            new_edge = Edge(id=id, type=edge_type, relation=relation, source_id=source_id,
                                        target_id=target_id,
                                        is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                                        provided_by=provided_by,
                                        confidence=confidence, weight=weight, edge_attributes=[edge_attribute],
                                        qedge_id=qedge_id)

                            self.message.knowledge_graph.edges.append(new_edge)
                            count = count + 1
                        else:
                            continue

        return self.response

    def query_adjacent_nodes(self, this):
        # FIXME: doc string does not match function definition
        """
        Query adjacent nodes of a given query node based on adjacent node type.
        :param node_curie: (required) the curie id of query node, eg. "UniProtKB:P14136"
        :param id: (required) any string to label this call, eg. "FET1"
        :param adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        :param kp: (optional) the knowledge provider to use, eg. "ARAX/KG1"(default)
        :param rel_type: (optional) edge type to consider, eg. "involved_in"
        :param return_len: (optional) return the number of adjacent nodes (default:False)
        :return adjacent node ids
        """

        if len(this) == 6:
            # this contains six variables and assign them to different variables
            node_curie, id, adjacent_type, kp, rel_type, return_len = this
        elif len(this) == 5:
            node_curie, id, adjacent_type, kp, rel_type = this
            return_len = False
        elif len(this) == 4:
            node_curie, id, adjacent_type, kp = this
            rel_type = None
            return_len = False
        elif len(this) == 3:
            node_curie, id, adjacent_type = this
            kp = "ARAX/KG1"
            rel_type = None
            return_len = False

        # construct the instance of ARAXQuery class
        araxq = ARAXQuery()
        res = None

        # call the method of ARAXQuery class to query adjacent node

        if rel_type:
            query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                f"add_qnode(curie={node_curie}, id={id}_n00)",
                f"fadd_qnode(type={adjacent_type}, id={id}_n01)",
                f"add_qedge(source_id={id}_n00, target_id={id}_n01, id={id}_e00, type={rel_type})",
                f"expand(edge_id={id}_e00,kp={kp})",
                "resultify()",
                "return(message=true, store=false)"
            ]}}
        else:
            query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                f"add_qnode(curie={node_curie}, id={id}_n00)",
                f"add_qnode(type={adjacent_type}, id={id}_n01)",
                f"add_qedge(source_id={id}_n00, target_id={id}_n01, id={id}_e00)",
                f"expand(edge_id={id}_e00,kp={kp})",
                "resultify()",
                "return(message=true, store=false)"
            ]}}

        if not return_len:
            try:
                result = araxq.query(query)
                if result.status != 'OK':
                    if not isinstance(araxq.message.knowledge_graph, dict):
                        res = araxq.message.knowledge_graph
                    else:
                        res
                else:
                    res = araxq.message.knowledge_graph
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with querying adjacent nodes from KP")
                return res
            return res

        else:
            try:
                result = araxq.query(query)
                if result.status != 'OK':
                    if not isinstance(araxq.message.knowledge_graph, dict):
                        res = len(araxq.message.knowledge_graph.nodes) - 1
                    else:
                        res
                else:
                    res = len(araxq.message.knowledge_graph.nodes) - 1
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong with querying adjacent nodes from KP")
                return res
            return res


    def size_of_given_type_in_KP(self,node_type, use_cypher_command=True):
        """
        find all nodes of a certain type in KP
        """
        # TODO: extend this to KG2, BTE, and other KP's we know of
        if use_cypher_command:
            rtxConfig = RTXConfiguration()
            # Connection information for the neo4j server, populated with orangeboard
            driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
            session = driver.session()

            query = "MATCH (n:%s) return count(distinct n)" % (node_type)
            res = session.run(query)
            size_of_total = res.single()["count(distinct n)"]

        else:
            pass

        return size_of_total

