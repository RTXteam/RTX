#!/bin/env python3
# This class will perform fisher's exact test to evalutate the significance of connection between
# a list of nodes with certain type in KG and each of the adjacent nodes with specified type.

# relative imports
import scipy.stats as stats
import traceback
import sys
import os
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

    def fisher_exact_test(self, query_node_label, adjacent_node_label, rel_type=None, top_n=None, cutoff=None):
        """
        Iterate over all the adjacent nodes with 'adjacent_node_label' (e.g. "biological_process") type in knowledge provider
        (e.g KG1) with respect to the nodes with
        'query_node_label' (e.g. "protein") type in the knowledge graph to compute the p-value and assign it to
        its node attribute
        :param query_node_label: node label of ALL the node in message KG eg. "protein"
        :param adjacent_node_label: target type of adjacent nodes, eg. "biological_process"
        :param rel_type: optional relationship type to consider, eg. "has_phenotype"
        :param top_n: optional number of results to return eg. 10
        :param cutoff: optional cutoff of p-value to filter adjacent nodes eg. 0.05
        :return: response
        """

        self.response.debug(f"Adding node with attribute 'Fisher Exact Test P-value'")
        self.response.info(f"Adding Fisher Exact Test P-value to node attribute")

        option_node_type_list = ["metabolite", "biological_process" ,"chemical_substance", "microRNA", "protein",
                                 "anatomical_entity", "pathway", "cellular_component", "phenotypic_feature", "disease",
                                 "molecular_function"]
        option_edge_type_list = ["physically_interacts_with", "subclass_of", "involved_in", "affects", "capable_of",
                                 "contraindicated_for", "indicated_for", "regulates", "expressed_in", "gene_associated_with_condition",
                                 "has_phenotype", "gene_mutations_contribute_to", "participates_in", "has_part"]

        # check if the input parameters are correct
        if query_node_label in option_node_type_list:
            pass
        else:
            self.response.error(f"The 'query_node_label' in fisher_exact_test function provided by user doesn't exist")
            return self.response
        if adjacent_node_label in option_node_type_list:
            pass
        else:
            self.response.error(f"The 'adjacent_node_label' in fisher_exact_test function provided by user doesn't exist")
            return self.response
        if rel_type in option_edge_type_list:
            pass
        else:
            self.response.error(f"The 'rel_type' in fisher_exact_test function provided by user doesn't exist")
            return self.response

        # initialize some variables
        nodes_info = {}
        edges_info = {}
        kp = set()
        query_node_list = []
        adjacent_node_dict = {}

        # iterate over KG nodes and edges and collect information
        try:
            for node in self.message.knowledge_graph.nodes:
                nodes_info[node.id] = {'type': node.type[0], 'edge_index': []}
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving nodes in message KG")
            return self.response

        try:
            count = 0
            for edge in self.message.knowledge_graph.edges:
                count = count + 1
                edges_info[count] = {'source_id': edge.source_id, 'target_id': edge.target_id, 'type': edge.type}
                kp.update([edge.is_defined_by])
                nodes_info[edge.source_id]['edge_index'].append(count)
                nodes_info[edge.target_id]['edge_index'].append(count)
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong with retrieving edges in message KG")
            return self.response

        # collect input node list for the FET based on provided query node type and edge type
        if rel_type:
            for key in edges_info.keys():
                if edges_info[key]['type'] == rel_type:
                    if nodes_info[edges_info[key]['source_id']] == query_node_label:
                        query_node_list.append(edges_info[key]['source_id'])
                    elif nodes_info[edges_info[key]['target_id']] == query_node_label:
                        query_node_list.append(edges_info[key]['target_id'])
                    else:
                        continue
                else:
                    continue
        else:
            for key in nodes_info.keys():
                if nodes_info[key]['type'] == query_node_label:
                    query_node_list.append(key)
                else:
                    continue

        query_node_list = list(set(query_node_list))

        if len(query_node_list) == 0:
            self.response.error(f"No query nodes found in message KG for the FET")
            return self.response

        # find all the nodes adjacent to those in query_node_list with query_node_label in KG
        for node in query_node_list:
            result_list = self.query_adjacent_node_based_on_edge_type(node_id=node, adjacent_type=adjacent_node_label, kp=list(kp)[0], rel_type=rel_type)
            if result_list:
                for adj in result_list:
                    if adj not in adjacent_node_dict:
                        adjacent_node_dict[adj] = [node]
                    else:
                        adjacent_node_dict[adj].append(node)
            else:
                return self.response

        # find all nodes with query_node_label associated with adjacent nodes in KG
        size_of_adjacent={}
        for node in adjacent_node_dict:
            result_list = self.query_adjacent_node_based_on_edge_type(node_id=node, adjacent_type=query_node_label, kp=list(kp)[0], rel_type=rel_type)
            if result_list:
                size_of_adjacent[node]=len(result_list)
            else:
                return self.response

        size_of_total = self.size_of_given_type_in_KP(node_type=query_node_label)
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
                    if 'adjacent' not in nodes_info.keys():
                        nodes_info[node]['adjacent'] = [output[adj]]
                    else:
                        nodes_info[node]['adjacent'].append(output[adj])

        for node in self.message.knowledge_graph.nodes:
            if 'adjacent' not in nodes_info[node.id].keys():
                pass
            else:
                node.node_attributes.append(nodes_info[node.id]['adjacent']) # append it to the list of attributes

        return self.response

    def query_adjacent_node_based_on_edge_type(self, node_id, adjacent_type, kp="ARAX/KG1", rel_type=None):
        """
        Query adjacent nodes of a given node based on adjacent node type.
        :param node_id: the id of query node eg. "UniProtKB:P14136"
        :param adjacent_type: the type of adjacent node eg. "biological_process"
        :param kp: the knowledge provider to use eg. "ARAX/KG1"(default)
        :param rel_type: optional relationship type to consider, eg. "involved_in"
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

