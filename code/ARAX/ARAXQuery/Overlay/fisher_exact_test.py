#!/bin/env python3
# This class will perform fisher's exact test to evalutate the significance of connection between
# a list of nodes with certain type in KG and each of the adjacent nodes with specified type.

# relative imports
import scipy.stats as stats
import traceback
import sys
import os
import concurrent.futures
from neo4j.v1 import GraphDatabase, basic_auth
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # code directory
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../") # code directory
from ARAX_query import ARAXQuery

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

        self.response.info(f"Performing Fisher's Exact Test to expand the knowledge graph and adding p-value to edge attribute")

        # check the input parameters
        if 'query_node_id' not in self.parameters:
            self.response.error(f"The argument 'query_node_id' is required for fisher_exact_test function")
            return self.response
        else:
            query_node_id = self.parameters['query_node_id']
        if 'adjacent_node_type' not in self.parameters:
            self.response.error(f"The argument 'adjacent_node_type' is required for fisher_exact_test function")
            return self.response
        else:
            adjacent_node_type = self.parameters['adjacent_node_type']
        query_edge_id = self.parameters['query_edge_id'] if 'query_edge_id' in self.parameters else None
        adjacent_edge_type = self.parameters['adjacent_edge_type'] if 'adjacent_edge_type' in self.parameters else None
        top_n = int(self.parameters['top_n']) if 'top_n' in self.parameters else None
        cutoff = float(self.parameters['cutoff']) if 'cutoff' in self.parameters else None

        # initialize some variables
        nodes_info = {}
        edge_id = []
        kp = set()
        query_node_list = []
        adjacent_node_dict = {}
        size_of_adjacent={}

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
                        elif nodes_info[edge.target_id]['qnode_id'] == query_node_id:
                            query_node_list.append(edge.target_id)
                        else:
                            continue
                    else:
                        continue
                    edge_id.append(edge.edge_id)
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
                    edge_id.append(edge.edge_id)
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

        # find all the nodes adjacent to those in query_node_list with query_node_type in KG
        #parament_list = [(node, adjacent_node_type, list(kp)[0], adjacent_edge_type) for node in query_node_list]
        #with concurrent.futures.ProcessPoolExecutor() as executor:
        #    res = list(executor.map(self.query_adjacent_node_based_on_edge_type, parament_list))



        for index in range(len(query_node_list)):
            node = query_node_list[index]
            result_list = res[index]
            if result_list:
                for adj in result_list:
                    if adj not in adjacent_node_dict.keys():
                        adjacent_node_dict[adj] = [node]
                    else:
                        adjacent_node_dict[adj].append(node)
            else:
                self.response.warning(f"Node" + node + " can't find the adjacent node with " + adjacent_node_type + " type in " + list(kp)[0])

        # find all nodes with query_node_type associated with adjacent nodes in KG
        parament_list = [(node, query_node_type, list(kp)[0], adjacent_edge_type) for node in list(adjacent_node_dict.keys())]
        with concurrent.futures.ProcessPoolExecutor() as executor:
            res = list(executor.map(self.query_adjacent_node_based_on_edge_type, parament_list))

        for index in range(len(adjacent_node_dict)):
            node = list(adjacent_node_dict.keys())[index]
            result_list = res[index]
            if result_list:
                size_of_adjacent[node] = len(result_list)
            else:
                self.response.error(
                    f"The adjacent node" + node + " can't find the associated nodes with " + query_node_type + " type in " +
                    list(kp)[0])
                return self.response

        size_of_total = self.size_of_given_type_in_KP(node_type=query_node_type)
        size_of_query_sample = len(query_node_list)

        output = {}
        for node in adjacent_node_dict:  # perform FET for each adjacent node
            contingency_table = [[len(adjacent_node_dict[node]), size_of_adjacent[node]-len(adjacent_node_dict[node])],
                                 [size_of_query_sample - len(adjacent_node_dict[node]), (size_of_total - size_of_adjacent[node]) - (size_of_query_sample - len(adjacent_node_dict[node]))]]
            output[node] = stats.fisher_exact(contingency_table)

        # check if the results need to be filtered
        output = dict(sorted(output.items(), key=lambda x: x[1][1]))
        if cutoff:
            output = dict(filter(lambda x: x[1][1] < cutoff, output.items()))
        else:
            pass
        if top_n:
            output = dict(list(output.items())[:top_n])
        else:
            pass

        # assign the results as node attribute to message
        for adj in adjacent_node_dict:
            if adj not in output.keys():
                continue
            else:
                for node in adjacent_node_dict[adj]:
                    if 'adjacent' not in nodes_info[node].keys():
                        nodes_info[node]['adjacent'] = dict()
                        nodes_info[node]['adjacent'][adj] = output[adj]
#                        nodes_info[node]['adjacent'] = [(adj,output[adj])]
                    else:
                        nodes_info[node]['adjacent'][adj] = output[adj]
#                        nodes_info[node]['adjacent'].append((adj,output[adj]))

        for index in range(len(self.message.knowledge_graph.nodes)):
            node = self.message.knowledge_graph.nodes[index]
            if 'adjacent' not in nodes_info[node.id].keys():
                pass
            else:
                node.node_attributes.append(nodes_info[node.id]['adjacent']) # append it to the list of attributes

        return self.response

    def query_adjacent_nodes(self, node_id_list, adjacent_type, kp="ARAX/KG1", rel_type=None):
        """
        Query adjacent nodes of a given query node based on adjacent node type.
        :param node_id_list: (required) the curie id list of query nodes, eg. "['UniProtKB:P14136','UniProtKB:P35579','UniProtKB:P02647']"
        :param adjacent_type: (required) the type of adjacent node, eg. "biological_process"
        :param kp: (optional) the knowledge provider to use, eg. "ARAX/KG1"(default)
        :param rel_type: (optional) edge type to consider, eg. "involved_in"
        :return adjacent node ids
        """

        # Initialize variables
        adjacent_node_id = []

        # construct the instance of ARAXQuery class
        araxq = ARAXQuery()

        # call the method of ARAXQuery class to query adjacent node

        if rel_type:
            query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                "add_qnode(name=" + node_id + ", id=n00)",
                "add_qnode(type=" + adjacent_type + ", id=n01)",
                "add_qedge(source_id=n00, target_id=n01, id=e00, type=" + rel_type + ")",
                "expand(edge_id=e00,kp=" + kp + ")",
                "resultify(ignore_edge_direction=false)",
                "return(message=true, store=false)"
            ]}}
        else:
            query = {"previous_message_processing_plan": {"processing_actions": [
                "create_message",
                "add_qnode(name=" + node_id + ", id=n00)",
                "add_qnode(type=" + adjacent_type + ", id=n01)",
                "add_qedge(source_id=n00, target_id=n01, id=e00)",
                "expand(edge_id=e00,kp=" + kp + ")",
                "resultify(ignore_edge_direction=false)",
                "return(message=true, store=false)"
            ]}}

        try:
            result = araxq.query(query)
            if result.status != 'OK':
                if not isinstance(araxq.message.knowledge_graph,dict):
                    for node in araxq.message.knowledge_graph.nodes:
                        if node.id != node_id:
                            adjacent_node_id.append(node.id)
                        else:
                            continue
                else:
                    pass
            else:
                for node in araxq.message.knowledge_graph.nodes:
                    if node.id != node_id:
                        adjacent_node_id.append(node.id)
                    else:
                        continue
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with querying adjacent nodes from KP")
            return None

        return adjacent_node_id


    def size_of_given_type_in_KP(self,node_type, use_cypher_command=True):
        """
        find all nodes of a certain type in KP
        """
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

