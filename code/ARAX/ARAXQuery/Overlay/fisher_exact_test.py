#!/bin/env python3
# This class will perform fisher's exact test to evalutate the significance of connection between
# a list of source nodes with certain qnode_id in KG and each of the target nodes with specified type.

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
        kp = set()
        source_node_list = []
        target_node_dict = {}
        size_of_target = {}
        target_graph_list = dict()
        source_node_exist = False
        target_node_exist = False
        source_node_type = []
        target_node_type = []
        query_edge_id = set()
        rel_edge_type = set()

        ## Check if source_qnode_id and target_qnode_id are in the Query Graph
        try:
            if len(self.message.query_graph.nodes) != 0:
                for node in self.message.query_graph.nodes:
                    if node.id == source_qnode_id:
                        source_node_exist = True
                        source_node_type.append(node.type)
                    elif node.id == target_qnode_id:
                        target_node_exist = True
                        target_node_type.append(node.type)
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
                self.response.error(f"No query node with target id {target_qnode_id} detected in QG for Fisher's Exact Test")
                return self.response
        else:
            self.response.error(f"No query node with source id {source_qnode_id} detected in QG for Fisher's Exact Test")
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
                    self.response.error(f"No query edge with id {rel_edge_id} connected to both source node with id {source_qnode_id} and target node with id {target_qnode_id} detected in QG for Fisher's Exact Test")
                    return self.response
            else:
                pass
        else:
            self.response.error(
                f"No query edge connected to both source node with id {source_qnode_id} and target node with id {target_qnode_id} detected in QG for Fisher's Exact Test")
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
                                kp.update([edge.is_defined_by])
                                rel_edge_type.update([edge.type])
                                source_node_list.append(edge.source_id)
                                if edge.target_id not in target_node_dict.keys():
                                    target_node_dict[edge.target_id] = set([edge.source_id])
                                else:
                                    target_node_dict[edge.target_id].update([edge.source_id])
                            else:
                                kp.update([edge.is_defined_by])
                                rel_edge_type.update([edge.type])
                                source_node_list.append(edge.target_id)
                                if edge.source_id not in target_node_dict.keys():
                                    target_node_dict[edge.source_id] = set([edge.target_id])
                                else:
                                    target_node_dict[edge.source_id].update([edge.target_id])
                        else:
                            pass
                    else:
                        if source_qnode_id in nodes_info[edge.source_id]['qnode_ids']:
                            if target_qnode_id in nodes_info[edge.target_id]['qnode_ids']:
                                kp.update([edge.is_defined_by])
                                source_node_list.append(edge.source_id)
                                if edge.target_id not in target_node_dict.keys():
                                    target_node_dict[edge.target_id] = set([edge.source_id])
                                else:
                                    target_node_dict[edge.target_id].update([edge.source_id])

                            else:
                                pass
                        elif target_qnode_id in nodes_info[edge.source_id]['qnode_ids']:
                            if source_qnode_id in nodes_info[edge.target_id]['qnode_ids']:
                                kp.update([edge.is_defined_by])
                                source_node_list.append(edge.target_id)
                                if edge.source_id not in target_node_dict.keys():
                                    target_node_dict[edge.source_id] = set([edge.target_id])
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

        # find all nodes with the type of 'source_qnode_id' nodes in specified KP ('ARAX/KG1','ARAX/KG2','BTE') that are adjacent to target nodes
        if rel_edge_id:
            if len(rel_edge_type)==1: # if the edge with rel_edge_id has only type, we use this rel_edge_type to find all source nodes in KP
                parament_list = [(node, f"{virtual_relation_label}", source_node_type[0], list(kp)[0], list(rel_edge_type)[0], True) for node in list(target_node_dict.keys())]
            else: # if the edge with rel_edge_id has more than one type, we ignore the edge type and use all types to find all source nodes in KP
                parament_list = [(node, f"{virtual_relation_label}", source_node_type[0], list(kp)[0], None, True) for node in list(target_node_dict.keys())]
        else: # if no rel_edge_id is specified, we ignore the edge type and use all types to find all source nodes in KP
            parament_list = [(node, f"{virtual_relation_label}", source_node_type[0], list(kp)[0], None, True) for node in list(target_node_dict.keys())]

        ## get the count of all nodes with the type of 'source_qnode_id' nodes in KP for each target node in parallel
        with concurrent.futures.ProcessPoolExecutor() as executor:
            target_count_res = list(executor.map(self.query_adjacent_nodes, parament_list))

        for index in range(len(target_node_dict)):
            node = list(target_node_dict.keys())[index]
            if target_count_res != -1:
                size_of_target[node] = target_count_res[index]
            else:
                self.response.error(f"The target node {node} can't find any adjacent nodes with type of {source_qnode_id} nodes in {list(kp)[0]}")
                return self.response

        size_of_total = self.size_of_given_type_in_KP(node_type=source_node_type[0])
        size_of_query_sample = len(source_node_list)


        output = {}
        self.response.debug(f"Computing Fisher's Exact Test P-value")
        try:
            for node in target_node_dict:  # perform FET p-value for each target node
                contingency_table = [[len(target_node_dict[node]), size_of_target[node]-len(target_node_dict[node])],
                                     [size_of_query_sample - len(target_node_dict[node]), (size_of_total - size_of_target[node]) - (size_of_query_sample - len(target_node_dict[node]))]]
                output[node] = stats.fisher_exact(contingency_table)[1]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with calculating FET p-value")
            return self.response

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
        count = 0
        self.response.debug(f"Adding virtual edge with FET result to message KG")
        for adj in target_node_dict:
            if adj not in output.keys():
                continue
            else:
                for node in target_node_dict[adj]:
                    # make the virtual edge, add the FET p-value as an attribute
                    id = f"{virtual_relation_label}_{count}"
                    edge_attribute = EdgeAttribute(type="data:1669", name="fisher_exact_test_p-value", value=str(output[adj]), url=None)  # FIXME: will need a url for this
                    now = datetime.now()
                    defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                    edge_type = 'has_fisher_exact_test_p-value_with'
                    qedge_ids = [virtual_relation_label]
                    is_defined_by = "ARAX"
                    provided_by = "ARAX"
                    confidence = None
                    weight = None
                    source_id = node
                    target_id = adj

                    new_edge = Edge(id=id, type=edge_type, relation=virtual_relation_label, source_id=source_id,
                                        target_id=target_id,
                                        is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                                        provided_by=provided_by,
                                        confidence=confidence, weight=weight, edge_attributes=[edge_attribute],
                                        qedge_ids=qedge_ids)

                    self.message.knowledge_graph.edges.append(new_edge)

                    count = count + 1
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

    def query_adjacent_nodes(self, this):
        # *Note*: The arugment 'this' is a list containing six sub-arguments below since this function is exectued in parallel.
        # This method is expected to be run within this class
        """
        Query adjacent nodes of a given source node based on adjacent node type.
        *Note*: The arugment 'this' is a list containing six sub-arguments below since this function is exectued in parallel.
        :param node_curie: (required) the curie id of query node, eg. "UniProtKB:P14136"
        :param id: (required) any string to label this call, eg. "FET"
        :param adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        :param kp: (optional) the knowledge provider to use, eg. "ARAX/KG2"(default)
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
            kp = "ARAX/KG2"
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
                f"add_qnode(type={adjacent_type}, id={id}_n01)",
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

