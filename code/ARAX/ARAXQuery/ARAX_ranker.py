#!/bin/env python3
import math
import os
import networkx as nx
import numpy as np
import scipy.stats
import sys
import json
import ast
import re

from typing import Set, Union, Dict, List, Callable
from response import Response
from query_graph_info import QueryGraphInfo

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.result import Result
from swagger_server.models.edge import Edge


def _get_nx_edges_by_attr(G: Union[nx.MultiDiGraph, nx.MultiGraph], key: str, val: str) -> Set[tuple]:
    res_set = set()
    for edge_tuple in G.edges(data=True):
        edge_val = edge_tuple[2].get(key, None)
        if edge_val is not None and edge_val == val:
            res_set.add(edge_tuple)
    return res_set


def _get_query_graph_networkx_from_query_graph(query_graph: QueryGraph) -> nx.MultiDiGraph:
    query_graph_nx = nx.MultiDiGraph()
    query_graph_nx.add_nodes_from([node.id for node in query_graph.nodes])
    edge_list = [[edge.source_id, edge.target_id, edge.id, {'weight': 0.0}] for edge in query_graph.edges]
    query_graph_nx.add_edges_from(edge_list)
    return query_graph_nx


def _get_weighted_graph_networkx_from_result_graph(kg_edge_id_to_edge: Dict[str, Edge],
                                                   qg_nx: Union[nx.MultiDiGraph, nx.MultiGraph],
                                                   result: Result) -> Union[nx.MultiDiGraph,
                                                                            nx.MultiGraph]:
    res_graph = qg_nx.copy()
    qg_edge_tuples = tuple(qg_nx.edges(keys=True, data=True))
    qg_edge_id_to_edge_tuple = {edge_tuple[2]: edge_tuple for edge_tuple in qg_edge_tuples}
    for edge in result.edge_bindings:
        kg_edge = kg_edge_id_to_edge[edge.kg_id]
        kg_edge_conf = kg_edge.confidence
        qedge_ids = kg_edge.qedge_ids
        for qedge_id in qedge_ids:
            qedge_tuple = qg_edge_id_to_edge_tuple[qedge_id]
            res_graph[qedge_tuple[0]][qedge_tuple[1]][qedge_id]['weight'] = kg_edge_conf
    return res_graph


def _get_weighted_graphs_networkx_from_result_graphs(kg_edge_id_to_edge: Dict[str, Edge],
                                                     qg_nx: Union[nx.MultiDiGraph, nx.MultiGraph],
                                                     results: List[Result]) -> List[Union[nx.MultiDiGraph,
                                                                                          nx.MultiGraph]]:
    res_list = []
    for result in results:
        res_list.append(_get_weighted_graph_networkx_from_result_graph(kg_edge_id_to_edge,
                                                                       qg_nx,
                                                                       result))
    return res_list


# credit: StackOverflow:15590812
def _collapse_nx_multigraph_to_weighted_graph(graph_nx: Union[nx.MultiDiGraph,
                                                              nx.MultiGraph]) -> Union[nx.DiGraph,
                                                                                       nx.Graph]:
    if type(graph_nx) == nx.MultiGraph:
        ret_graph = nx.Graph()
    elif type(graph_nx) == nx.MultiDiGraph:
        ret_graph = nx.DiGraph()
    for u, v, data in graph_nx.edges(data=True):
        w = data['weight'] if 'weight' in data else 1.0
        if ret_graph.has_edge(u, v):
            ret_graph[u][v]['weight'] += w
        else:
            ret_graph.add_edge(u, v, weight=w)
    return ret_graph


# computes quantile ranks in *ascending* order (so a higher x entry has a higher
# "rank"), where ties have the same (average) rank (the reason for using scipy.stats
# here is specifically in order to handle ties correctly)
def _quantile_rank_list(x: List[float]) -> np.array:
    y = scipy.stats.rankdata(x)
    return y/len(y)


def _score_networkx_graphs_by_max_flow(result_graphs_nx: List[Union[nx.MultiDiGraph,
                                                                    nx.MultiGraph]]) -> List[float]:
    max_flow_values = []
    for result_graph_nx in result_graphs_nx:
        if len(result_graph_nx) > 1:
            apsp_dict = dict(nx.algorithms.shortest_paths.unweighted.all_pairs_shortest_path_length(result_graph_nx))
            path_len_with_pairs_list = [(node_i, node_j, path_len) for node_i, node_i_dict in apsp_dict.items() for node_j, path_len in node_i_dict.items()]
            max_path_len = max([path_len_with_pair_list_item[2] for path_len_with_pair_list_item in
                                path_len_with_pairs_list])
            pairs_with_max_path_len = [path_len_with_pair_list_item[0:2] for path_len_with_pair_list_item in path_len_with_pairs_list if
                                       path_len_with_pair_list_item[2] == max_path_len]
            max_flow_values_for_node_pairs = []
            result_graph_collapsed_nx = _collapse_nx_multigraph_to_weighted_graph(result_graph_nx)
            for source_node_id, target_node_id in pairs_with_max_path_len:
                max_flow_values_for_node_pairs.append(nx.algorithms.flow.maximum_flow_value(result_graph_collapsed_nx,
                                                                                            source_node_id,
                                                                                            target_node_id,
                                                                                            capacity="weight"))
            max_flow_value = 0.0
            if len(max_flow_values_for_node_pairs) > 0:
                max_flow_value = sum(max_flow_values_for_node_pairs)/float(len(max_flow_values_for_node_pairs))
        else:
            max_flow_value = 1.0
        max_flow_values.append(max_flow_value)
    return max_flow_values


def _score_networkx_graphs_by_longest_path(result_graphs_nx: List[Union[nx.MultiDiGraph,
                                                                        nx.MultiGraph]]) -> List[float]:
    result_scores = []
    for result_graph_nx in result_graphs_nx:
        apsp_dict = dict(nx.algorithms.shortest_paths.unweighted.all_pairs_shortest_path_length(result_graph_nx))
        path_len_with_pairs_list = [(node_i, node_j, path_len) for node_i, node_i_dict in apsp_dict.items() for node_j, path_len in node_i_dict.items()]
        max_path_len = max([path_len_with_pair_list_item[2] for path_len_with_pair_list_item in
                            path_len_with_pairs_list])
        pairs_with_max_path_len = [path_len_with_pair_list_item[0:2] for path_len_with_pair_list_item in path_len_with_pairs_list if
                                   path_len_with_pair_list_item[2] == max_path_len]
        map_node_name_to_index = {node_id: node_index for node_index, node_id in enumerate(result_graph_nx.nodes)}
        adj_matrix = nx.to_numpy_matrix(result_graph_nx)
        adj_matrix_power = np.linalg.matrix_power(adj_matrix, max_path_len)/math.factorial(max_path_len)
        score_list = [adj_matrix_power[map_node_name_to_index[node_i],
                                       map_node_name_to_index[node_j]] for node_i, node_j in pairs_with_max_path_len]
        result_score = np.mean(score_list)
        result_scores.append(result_score)
    return result_scores


def _score_networkx_graphs_by_frobenius_norm(result_graphs_nx: List[Union[nx.MultiDiGraph,
                                                                          nx.MultiGraph]]) -> List[float]:
    result_scores = []
    for result_graph_nx in result_graphs_nx:
        adj_matrix = nx.to_numpy_matrix(result_graph_nx)
        result_score = np.linalg.norm(adj_matrix, ord='fro')
        result_scores.append(result_score)
    return result_scores


def _score_result_graphs_by_networkx_graph_scorer(kg_edge_id_to_edge: Dict[str, Edge],
                                                  qg_nx: Union[nx.MultiDiGraph, nx.MultiGraph],
                                                  results: List[Result],
                                                  nx_graph_scorer: Callable[[List[Union[nx.MultiDiGraph,
                                                                                        nx.MultiGraph]]], np.array]) -> List[float]:
    result_graphs_nx = _get_weighted_graphs_networkx_from_result_graphs(kg_edge_id_to_edge,
                                                                        qg_nx,
                                                                        results)
    return nx_graph_scorer(result_graphs_nx)


class ARAXRanker:

    # #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        # edge attributes we know about
        self.known_attributes = {'probability', 'normalized_google_distance', 'jaccard_index',
                                 'probability_treats', 'paired_concept_frequency',
                                 'observed_expected_ratio', 'chi_square', 'MAGMA-pvalue', 'Genetics-quantile',
                                 'fisher_exact_test_p-value','Richards-effector-genes'}
        # how much we trust each of the edge attributes
        self.known_attributes_to_trust = {'probability': 0.5,
                                          'normalized_google_distance': 0.8,
                                          'jaccard_index': 0.5,
                                          'probability_treats': 1,
                                          'paired_concept_frequency': 0.5,
                                          'observed_expected_ratio': 0.8,
                                          'chi_square': 0.8,
                                          'MAGMA-pvalue': 1.0,
                                          'Genetics-quantile': 1.0,
                                          'fisher_exact_test_p-value': 0.8,
                                          'Richards-effector-genes': 0.5,
                                          }
        self.virtual_edge_types = {}
        self.score_stats = dict()  # dictionary that stores that max's and min's of the edge attribute values
        self.kg_edge_id_to_edge = dict()  # map between the edge id's in the results and the actual edges themselves

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """

        brief_description = """
rank_results iterates through all edges in the results list aggrigating and 
normalizing the scores stored within the edge_attributes property. After combining these scores into 
one score the ranker then scores each result through a combination of max flow, longest path, 
and frobenius norm.
        """
        description = """
`rank_results` iterates through all edges in the results list aggrigating and 
normalizing the scores stored within the `edge_attributes` property. After combining these scores into 
one score the ranker then scores each result through a combination of 
[max flow](https://en.wikipedia.org/wiki/Maximum_flow_problem), 
[longest path](https://en.wikipedia.org/wiki/Longest_path_problem), 
and [frobenius norm](https://en.wikipedia.org/wiki/Matrix_norm#Frobenius_norm).
        """
        description_list = []
        params_dict = dict()
        params_dict['brief_description'] = brief_description
        params_dict['description'] = description
        params_dict["dsl_command"] = "rank_results()"
        description_list.append(params_dict)
        return description_list

    def result_confidence_maker(self, result):
        ###############################
        # old method of just multiplying ALL the edge confidences together
        if True:
            result_confidence = 1  # everybody gets to start with a confidence of 1
            for edge in result.edge_bindings:
                kg_edge_id = edge.kg_id
                # TODO: replace this with the more intelligent function
                # here we are just multiplying the edge confidences
                # --- to see what info is going into each result: print(f"{result.essence}: {kg_edges[kg_edge_id].type}, {kg_edges[kg_edge_id].confidence}")
                result_confidence *= self.kg_edge_id_to_edge[kg_edge_id].confidence
            result.confidence = result_confidence
        else:
            # consider each pair of nodes in the QG, then somehow combine that information
            # Idea:
            #   in each result
            #       for each source and target node:
            #           combine the confidences into a single edge with a single confidence that takes everything into account (
            #           edges, edge scores, edge types, etc)
            #       then assign result confidence as average/median of these "single" edge confidences?
            result.confidence = 1

    def edge_attribute_score_combiner(self, edge):
        """
        This function takes a single edge and decides how to combine its attribute scores into a single confidence
        Eventually we will want
        1. To weight different attributes by different amounts
        2. Figure out what to do with edges that have no attributes
        """
        # Currently a dead simple "just multiply them all together"
        edge_confidence = 1
        if edge.edge_attributes is not None:
            for edge_attribute in edge.edge_attributes:
                normalized_score = self.edge_attribute_score_normalizer(edge_attribute.name, edge_attribute.value)
                if normalized_score == -1:  # this means we have no current normalization of this kind of attribute,
                    continue  # so don't do anything to the score since we don't know what to do with it yet
                else:  # we have a way to normalize it, so multiply away
                    edge_confidence *= normalized_score
        return edge_confidence

    def edge_attribute_score_normalizer(self, edge_attribute_name: str, edge_attribute_value) -> float:
        """
        Takes an input edge attribute and value, dispatches it to the appropriate method that translates the value into
        something in the interval [0,1] where 0 is worse and 1 is better
        """
        if edge_attribute_name not in self.known_attributes:
            return -1  # TODO: might want to change this
        else:
            try:
                # check to see if it's convertible to a float (will catch None's as well)
                edge_attribute_value = float(edge_attribute_value)
            except TypeError:
                return 0.
            # check to see if it's NaN, if so, return 0
            if np.isnan(edge_attribute_value):
                return 0.
            # else it's all good to proceed
            else:
                # Fix hyphens or spaces to underscores in names
                edge_attribute_name = re.sub(r'[- ]','_',edge_attribute_name)
                # then dispatch to the appropriate function that does the score normalizing to get it to be in [0, 1] with 1 better
                return getattr(self, '_' + self.__class__.__name__ + '__normalize_' + edge_attribute_name)(value=edge_attribute_value)

    def __normalize_probability_treats(self, value):
        """
        Normalize the probability drug treats disease value.
        Empirically we've found that values greater than ~0.75 are "good" and <~0.75 are "bad" predictions of "treats"
        We will hence throw this in a logistic function so that higher scores remain high, and low scores drop off
        pretty quickly.
        To see this curve in Mathematica:
        L = 1;  (*max value returned*)
        k = 15;  (*steepness of the logistic curve*)
        x0 = 0.60;  (*mid point of the logistic curve*)
        Plot[L/(1 + Exp[-k (x - x0)]), {x, 0, 1}, PlotRange -> All, AxesOrigin -> {0, 0}]
        or
        import matplotlib.pyplot as plt
        max_value = 1
        curve_steepness = 15
        logistic_midpoint = 0.60
        x = np.linspace(0,1,200)
        y = [max_value / float(1+np.exp(-curve_steepness*(value - logistic_midpoint))) for value in x]
        plt.plot(x,y)
        plt.show()
        """
        max_value = 1
        curve_steepness = 15
        logistic_midpoint = 0.60
        normalized_value = max_value / float(1+np.exp(-curve_steepness*(value - logistic_midpoint)))
        # TODO: if "near" to the min value, set to zero (maybe one std dev from the min value of the logistic curve?)
        # TODO: make sure max value can be obtained
        return normalized_value

    def __normalize_normalized_google_distance(self, value):
        """
        Normalize the "normalized_google_distance
        """
        max_value = 1
        curve_steepness = -9
        logistic_midpoint = 0.60
        normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))
        # TODO: if "near" to the min value, set to zero (maybe one std dev from the min value of the logistic curve?)
        # TODO: make sure max value can be obtained
        return normalized_value

    def __normalize_probability(self, value):
        """
        These (as of 7/28/2020 in KG1 and KG2 only "drug->protein binding probabilities"
        As Vlado suggested, the lower ones are more rubbish, so again throw into a logistic function, but even steeper.
        see __normalize_probability_treats for how to visualize this
        """
        max_value = 1
        curve_steepness = 20
        logistic_midpoint = 0.8
        normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))
        # TODO: if "near" to the min value, set to zero (maybe one std dev from the min value of the logistic curve?)
        # TODO: make sure max value can be obtained
        return normalized_value

    def __normalize_jaccard_index(self, value):
        """
        The jaccard index is all relative to other results, so there is no reason to use a logistic here.
        Just compare the value to the maximum value
        """
        normalized_value = value / self.score_stats['jaccard_index']['maximum']
        # print(f"value: {value}, normalized: {normalized_value}")
        return normalized_value

    def __normalize_paired_concept_frequency(self, value):
        """
        Again, these are _somewhat_ relative values. In actuality, a logistic here would make sense,
        but I don't know the distribution of frequencies in COHD, so just go the relative route
        """
        # check to make sure we don't divide by zero
        # try:
        #    normalized_value = value / score_stats['paired_concept_frequency']['maximum']
        # except ZeroDivisionError:
        #    normalized_value = value / (score_stats['paired_concept_frequency']['maximum'] + np.finfo(float).eps)

        # Give logistic a try
        # TODO: see if we can adjust these params based on the scores stats (or see if that's even a good idea)
        max_value = 1
        curve_steepness = 2000  # really steep since the max values I've ever seen are quite small (eg .03)
        logistic_midpoint = 0.002  # seems like an ok mid point, but....
        normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))
        # TODO: if "near" to the min value, set to zero (maybe one std dev from the min value of the logistic curve?)
        # TODO: make sure max value can be obtained
        # print(f"value: {value}, normalized: {normalized_value}")
        return normalized_value

    def __normalize_observed_expected_ratio(self, value):
        """
        These are log ratios so should be interpreted as Exp[value] times more likely than chance
        """
        max_value = 1
        curve_steepness = 2  # Todo: need to fiddle with this as it's not quite weighting things enough
        logistic_midpoint = 2  # Exp[2] more likely than chance
        normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))
        # TODO: if "near" to the min value, set to zero (maybe one std dev from the min value of the logistic curve?)
        # TODO: make sure max value can be obtained
        # print(f"value: {value}, normalized: {normalized_value}")
        return normalized_value


    def __normalize_chi_square(self, value):
        """
        From COHD: Note that due to large sample sizes, the chi-square can become very large.
        Hence the p-values will be very, very small... Hard to use logistic function, so instead, take the
        -log(p_value) approach and use that (taking a page from the geneticist's handbook)
        """
        # Taking value as is:
        # max_value = 1
        # curve_steepness = -100
        # logistic_midpoint = 0.05
        # normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))

        # -Log[p_value] approach
        value = -np.log(value)
        max_value = 1
        curve_steepness = 0.03
        logistic_midpoint = 200
        normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))
        # TODO: if "near" to the min value, set to zero (maybe one std dev from the min value of the logistic curve?)
        # TODO: make sure max value can be obtained
        # print(f"value: {value}, normalized: {normalized_value}")
        return normalized_value


    def __normalize_MAGMA_pvalue(self, value):
        """
        For Genetics Provider MAGMA p-value: Convert provided p-value to a number between 0 and 1
        with 1 being best. Estimated conversion from SAR and DMK 2020-09-22
        """

        value = -np.log(value)
        max_value = 1.0
        curve_steepness = 0.849
        logistic_midpoint = 4.97
        normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))
        return normalized_value


    def __normalize_Genetics_quantile(self, value):
        """
        For Genetics Provider MAGMA quantile: We decide 2020-09-22 that just using
        the quantile as-is is best. With DML, SAR, EWD.
        """

        return value

    def __normalize_fisher_exact_test_p_value(self, value):
        """
        For FET p-values: Including two options
        The first option is to simply use 1-(p-value)
        The second is a custom logorithmic. 0.05 should correspond to ~0.95 after the logistic is applied.
        """

        # option 1:
        # normalized_value = 1-value

        # option 2:
        value = -np.log(value)
        max_value = 1.0
        curve_steepness = 2
        logistic_midpoint = 2.21
        normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))

        return normalized_value

    def __normalize_Richards_effector_genes(self, value):
        return value

    def aggregate_scores_dmk(self, message, response=None):
        """
        Take in a message,
        decorate all edges with confidences,
        take each result and use edge confidences and other info to populate result confidences,
        populate the result.row_data and message.table_column_names
        Does everything in place (no result returned)
        """

        # #### Set up the response object if one is not already available
        if response is None:
            if self.response is None:
                response = Response()
            else:
                response = self.response
        else:
            self.response = response
        self.message = message

        # #### Compute some basic information about the query_graph
        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(message)
        # response.merge(result)
        # if result.status != 'OK':
        #     print(response.show(level=Response.DEBUG))
        #     return response

        # DMK FIXME: This need to be refactored so that:
        #    1. The attribute names are dynamically mapped to functions that handle their weightings (for ease of renaming attribute names)
        #    2. Weighting of individual attributes (eg. "probability" should be trusted MUCH less than "probability_treats")
        #    3. Auto-handling of normalizing scores to be in [0,1] (eg. observed_expected ration \in (-inf, inf) while probability \in (0,1)
        #    4. Auto-thresholding of values (eg. if chi_square <0.05, penalize the most, if probability_treats < 0.8, penalize the most, etc.)
        #    5. Allow for ranked answers (eg. observed_expected can have a single, huge value, skewing the rest of them

        # #### Iterate through all the edges in the knowledge graph to:
        # #### 1) Create a dict of all edges by id
        # #### 2) Collect some min,max stats for edge_attributes that we may need later
        kg_edge_id_to_edge = self.kg_edge_id_to_edge
        score_stats = self.score_stats
        no_non_inf_float_flag = True
        for edge in message.knowledge_graph.edges:
            kg_edge_id_to_edge[edge.id] = edge
            if edge.edge_attributes is not None:
                for edge_attribute in edge.edge_attributes:
                    for attribute_name in self.known_attributes:
                        if edge_attribute.name == attribute_name:
                            if attribute_name not in score_stats:
                                score_stats[attribute_name] = {'minimum': None, 'maximum': None}  # FIXME: doesn't handle the case when all values are inf|NaN
                            value = float(edge_attribute.value)
                            # initialize if not None already
                            if not np.isinf(value) and not np.isinf(-value) and not np.isnan(value):  # Ignore inf, -inf, and nan
                                no_non_inf_float_flag = False
                                if not score_stats[attribute_name]['minimum']:
                                    score_stats[attribute_name]['minimum'] = value
                                if not score_stats[attribute_name]['maximum']:
                                    score_stats[attribute_name]['maximum'] = value
                                if value > score_stats[attribute_name]['maximum']:
                                    score_stats[attribute_name]['maximum'] = value
                                if value < score_stats[attribute_name]['minimum']:
                                    score_stats[attribute_name]['minimum'] = value

        if no_non_inf_float_flag:
            response.warning(
                        f"No non-infinate value was encountered in any edge attribute in the knowledge graph.")
        response.info(f"Summary of available edge metrics: {score_stats}")

        # Loop over the entire KG and normalize and combine the score of each edge, place that information in the confidence attribute of the edge
        for edge in message.knowledge_graph.edges:
            if edge.confidence is not None:
                # don't touch the confidence, since apparently someone already knows what the confidence should be
                continue
            else:
                confidence = self.edge_attribute_score_combiner(edge)
                edge.confidence = confidence

        # Now that each edge has a confidence attached to it based on it's attributes, we can now:
        # 1. consider edge types of the results
        # 2. number of edges in the results
        # 3. possibly conflicting information, etc.

        ###################################
        # TODO: Replace this with a more "intelligent" separate function
        # now we can loop over all the results, and combine their edge confidences (now populated)
        qg_nx = _get_query_graph_networkx_from_query_graph(message.query_graph)
        kg_edge_id_to_edge = self.kg_edge_id_to_edge
        results = message.results
        ranks_list = list(map(_quantile_rank_list,
                              map(lambda scorer_func: _score_result_graphs_by_networkx_graph_scorer(kg_edge_id_to_edge,
                                                                                                    qg_nx,
                                                                                                    results,
                                                                                                    scorer_func),
                                  [_score_networkx_graphs_by_max_flow,
                                   _score_networkx_graphs_by_longest_path,
                                   _score_networkx_graphs_by_frobenius_norm])))
        #print(ranks_list)
        result_scores = sum(ranks_list)/float(len(ranks_list))
        #print(result_scores)
        for result, score in zip(results, result_scores):
            result.confidence = score

        # for result in message.results:
        #     self.result_confidence_maker(result)
        ###################################

            # Make all scores at least 0.001. This is all way low anyway, but let's not have anything that rounds to zero
            # This is a little bad in that 0.0005 becomes better than 0.0011, but this is all way low, so who cares
            if result.confidence < 0.001:
                result.confidence += 0.001

            # Round to reasonable precision. Keep only 3 digits after the decimal
            score = int(result.confidence * 1000 + 0.5) / 1000.0

            result.row_data = [score, result.essence, result.essence_type]

        # Add table columns name
        message.table_column_names = ['confidence', 'essence', 'essence_type']

        # Re-sort the final results
        message.results.sort(key=lambda result: result.confidence, reverse=True)

    # ############################################################################################
    # #### For each result[], aggregate all available confidence metrics and other scores to compute a final score
    def aggregate_scores(self, message, response=None):

        # #### Set up the response object if one is not already available
        if response is None:
            if self.response is None:
                response = Response()
            else:
                response = self.response
        else:
            self.response = response
        self.message = message

        # #### Compute some basic information about the query_graph
        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(message)
        # response.merge(result)
        # if result.status != 'OK':
        #     print(response.show(level=Response.DEBUG))
        #     return response

        # DMK FIXME: This need to be refactored so that:
        #    1. The attribute names are dynamically mapped to functions that handle their weightings (for ease of renaming attribute names)
        #    2. Weighting of individual attributes (eg. "probability" should be trusted MUCH less than "probability_treats")
        #    3. Auto-handling of normalizing scores to be in [0,1] (eg. observed_expected ration \in (-inf, inf) while probability \in (0,1)
        #    4. Auto-thresholding of values (eg. if chi_square <0.05, penalize the most, if probability_treats < 0.8, penalize the most, etc.)
        #    5. Allow for ranked answers (eg. observed_expected can have a single, huge value, skewing the rest of them

        # #### Iterate through all the edges in the knowledge graph to:
        # #### 1) Create a dict of all edges by id
        # #### 2) Collect some min,max stats for edge_attributes that we may need later
        kg_edges = {}
        score_stats = {}
        for edge in message.knowledge_graph.edges:
            kg_edges[edge.id] = edge
            if edge.edge_attributes is not None:
                for edge_attribute in edge.edge_attributes:
                    # FIXME: DMK: We should probably have some some way to dynamically get the attribute names since they appear to be constantly changing
                    # DMK: Crazy idea: have the individual ARAXi commands pass along their attribute names along with what they think of is a
                    #      good way to handle them
                    # DMK: eg. "higher is better" or "my range of [0, inf]" or "my value is a probability", etc.
                    for attribute_name in ['probability', 'normalized_google_distance', 'jaccard_index',
                                           'probability_treats', 'paired_concept_frequency',
                                           'observed_expected_ratio', 'chi_square']:
                        if edge_attribute.name == attribute_name:
                            if attribute_name not in score_stats:
                                score_stats[attribute_name] = {'minimum': None, 'maximum': None}  # FIXME: doesn't handle the case when all values are inf|NaN
                            value = float(edge_attribute.value)
                            # TODO: don't set to max here, since returning inf for some edge attributes means "I have no data"
                            # if np.isinf(value):
                            #     value = 9999
                            # initialize if not None already
                            if not np.isinf(value) and not np.isinf(-value) and not np.isnan(value):  # Ignore inf, -inf, and nan
                                if not score_stats[attribute_name]['minimum']:
                                    score_stats[attribute_name]['minimum'] = value
                                if not score_stats[attribute_name]['maximum']:
                                    score_stats[attribute_name]['maximum'] = value
                                if value > score_stats[attribute_name]['maximum']:  # DMK FIXME: expected type 'float', got 'None' instead
                                    score_stats[attribute_name]['maximum'] = value
                                if value < score_stats[attribute_name]['minimum']:  # DMK FIXME: expected type 'float', got 'None' instead
                                    score_stats[attribute_name]['minimum'] = value
        response.info(f"Summary of available edge metrics: {score_stats}")

        # #### Loop through the results[] in order to compute aggregated scores
        i_result = 0
        for result in message.results:
            # response.debug(f"Metrics for result {i_result}  {result.essence}: ")

            # #### Begin with a default score of 1.0 for everything
            score = 1.0

            # #### There are often many edges associated with a result[]. Some are great, some are terrible.
            # #### For now, the score will be based on the best one. Maybe combining probabilities in quadrature would be better
            best_probability = 0.0  # TODO: What's this? the best probability of what?

            eps = np.finfo(np.float).eps  # epsilon to avoid division by 0
            penalize_factor = 0.7  # multiplicative factor to penalize by if the KS/KP return NaN or Inf indicating they haven't seen it before

            # #### Loop through each edge in the result
            for edge in result.edge_bindings:
                kg_edge_id = edge.kg_id

                # #### Set up a string buffer to keep some debugging information that could be printed
                buf = ''

                # #### If the edge has a confidence value, then multiply that into the final score
                if kg_edges[kg_edge_id].confidence is not None:
                    buf += f" confidence={kg_edges[kg_edge_id].confidence}"
                    score *= float(kg_edges[kg_edge_id].confidence)

                # #### If the edge has attributes, loop through those looking for scores that we know how to handle
                if kg_edges[kg_edge_id].edge_attributes is not None:
                    for edge_attribute in kg_edges[kg_edge_id].edge_attributes:

                        # FIXME: These are chemical_substance->protein binding probabilities, may not want be treating them like this....
                        # ### EWD: Vlado has suggested that any of these links with chemical_substance->protein binding probabilities are
                        # ### EWD: mostly junk. very low probablility of being correct. His opinion seemed to be that they shouldn't be in the KG
                        # ### EWD: If we keep them, maybe their probabilities should be knocked down even further, in half, in quarter..
                        # DMK: I agree: hence why I said we should probably not be treating them like this (and not trusting them a lot)

                        # #### If the edge_attribute is named 'probability', then for now use it to record the best probability only
                        if edge_attribute.name == 'probability':
                            value = float(edge_attribute.value)
                            buf += f" probability={edge_attribute.value}"
                            if value > best_probability:
                                best_probability = value

                        # #### If the edge_attribute is named 'probability_drug_treats', then for now we won't do anything
                        # #### because this value also seems to be copied into the edge confidence field, so is already
                        # #### taken into account
                        # if edge_attribute.name == 'probability_drug_treats':               # this is already put in confidence
                        #     buf += f" probability_drug_treats={edge_attribute.value}"
                        #     score *= value
                        # DMK FIXME: Do we actually have 'probability_drug_treats' attributes?, the probability_drug_treats is *not*
                        #            put in the confidence see: confidence = None in `predict_drug_treats_disease.py`
                        # DMK: also note the edge type is: edge_type = "probably_treats"

                        # If the edge_attribute is named 'probability_treats', use the value more or less as a probability
                        # ### EWD says: but note that when I last worked on this, the probability_treats was repeated in an edge attribute
                        # ### EWD says: as well as in the edge confidence score, so I commented out this section (see immediately above)
                        #     DMK (same re: comment above :) )
                        # ### EWD says: so that it wouldn't be counted twice. But that may have changed in the mean time.
                        if edge_attribute.name == "probability_treats":
                            prob_treats = float(edge_attribute.value)
                            # Don't treat as a good prediction if the ML model returns a low value
                            if prob_treats < penalize_factor:
                                factor = penalize_factor
                            else:
                                factor = prob_treats
                            score *= factor  # already a number between 0 and 1, so just multiply

                        # #### If the edge_attribute is named 'ngd', then use some hocus pocus to convert to a confidence
                        if edge_attribute.name == 'normalized_google_distance':
                            ngd = float(edge_attribute.value)
                            # If the distance is infinite, then set it to 10, a very large number in this context
                            if np.isinf(ngd):
                                ngd = 10.0
                            buf += f" ngd={ngd}"

                            # #### Apply a somewhat arbitrary transformation such that:
                            # #### NGD = 0.3 leads to a factor of 1.0. That's *really* close
                            # #### NGD = 0.5 leads to a factor of 0.88. That still a close NGD
                            # #### NGD = 0.7 leads to a factor of 0.76. Same ballpark
                            # #### NGD = 0.9 this is pretty far away. Still the factor is 0.64. Distantly related
                            # #### NGD = 1.0 is very far. Still, factor is 0.58. Grade inflation is rampant.
                            factor = 1 - (ngd - 0.3) * 0.6

                            # Apply limits of 1.0 and 0.01 to the linear fudge
                            if factor < 0.01:
                                factor = 0.01
                            if factor > 1:
                                factor = 1.0
                            buf += f" ngd_factor={factor}"
                            score *= factor

                        # #### If the edge_attribute is named 'jaccard_index', then use some hocus pocus to convert to a confidence
                        if edge_attribute.name == 'jaccard_index':
                            jaccard = float(edge_attribute.value)
                            # If the jaccard index is infinite, set to some arbitrarily bad score
                            if np.isinf(jaccard):
                                jaccard = 0.01

                            # #### Set the confidence factor so that the best value of all results here becomes 0.95
                            # #### Why not 1.0? Seems like in scenarios where we're computing a Jaccard index, nothing is really certain
                            factor = jaccard / score_stats['jaccard_index']['maximum'] * 0.95
                            buf += f" jaccard={jaccard}, factor={factor}"
                            score *= factor

                        # If the edge_attribute is named 'paired_concept_frequency', then ...
                        if edge_attribute.name == "paired_concept_frequency":
                            paired_concept_freq = float(edge_attribute.value)
                            if np.isinf(paired_concept_freq) or np.isnan(paired_concept_freq):
                                factor = penalize_factor
                            else:
                                try:
                                    factor = paired_concept_freq / score_stats['paired_concept_frequency']['maximum']
                                except ZeroDivisionError:
                                    factor = paired_concept_freq / (score_stats['paired_concept_frequency']['maximum'] + eps)
                            score *= factor
                            buf += f" paired_concept_frequency={paired_concept_freq}, factor={factor}"

                        # If the edge_attribute is named 'observed_expected_ratio', then ...
                        if edge_attribute.name == 'observed_expected_ratio':
                            obs_exp_ratio = float(edge_attribute.value)
                            if np.isinf(obs_exp_ratio) or np.isnan(obs_exp_ratio):
                                factor = penalize_factor  # Penalize for missing info
                            # Would love to throw this into a sigmoid like function customized by the max value observed
                            # for now, just throw into a sigmoid and see what happens
                            factor = 1 / float(1 + np.exp(-4*obs_exp_ratio))
                            score *= factor
                            buf += f" observed_expected_ratio={obs_exp_ratio}, factor={factor}"

                        # If the edge_attribute is named 'chi_square', then compute a factor based on the chisq and the max chisq
                        if edge_attribute.name == 'chi_square':
                            chi_square = float(edge_attribute.value)
                            if np.isinf(chi_square) or np.isnan(chi_square):
                                factor = penalize_factor
                            else:
                                try:
                                    factor = 1 - (chi_square / score_stats['chi_square']['maximum'])  # lower is better
                                except ZeroDivisionError:
                                    factor = 1 - (chi_square / (score_stats['chi_square']['maximum'] + eps))  # lower is better
                            score *= factor
                            buf += f" chi_square={chi_square}, factor={factor}"

                # #### When debugging, log the edge_id and the accumulated information in the buffer
                # response.debug(f"  - {kg_edge_id}  {buf}")

            # #### If there was a best_probability recorded, then multiply into the running score
            # ### EWD: This was commented out by DMK? I don't know why. I think it should be here             FIXME
            # if best_probability > 0.0:
            #     score *= best_probability
            # DMK: for some reason, this was causing my scores to be ridiculously low, so I commented it out and confidences went up "quite a bit"

            # #### Make all scores at least 0.01. This is all way low anyway, but let's not have anything that rounds to zero
            # #### This is a little bad in that 0.005 becomes better than 0.011, but this is all way low, so who cares
            if score < 0.01:
                score += 0.01

            # ### Round to reasonable precision. Keep only 3 digits after the decimal
            score = int(score * 1000 + 0.5) / 1000.0

            # response.debug(f"  ---> final score={score}")
            result.confidence = score
            result.row_data = [score, result.essence, result.essence_type]
            i_result += 1

        # -- Add table columns name
        message.table_column_names = ['confidence', 'essence', 'essence_type']

        # -- Re-sort the final results
        message.results.sort(key=lambda result: result.confidence, reverse=True)

##########################################################################################


def main():
    # For faster testing, cache the testing messages locally
    import requests_cache
    requests_cache.install_cache('ARAX_ranker_testing_cache')

    import argparse
    argparser = argparse.ArgumentParser(description='Ranker system')
    argparser.add_argument('--local', action='store_true', help='If set, use local RTXFeedback database to fetch messages')
    params = argparser.parse_args()

    # --- Create a response object
    response = Response()
    ranker = ARAXRanker()

    # --- Get a Message to work on
    from ARAX_messenger import ARAXMessenger
    messenger = ARAXMessenger()
    if not params.local:
        print("INFO: Fetching message to work on from arax.ncats.io", flush=True)
        message = messenger.fetch_message('https://arax.ncats.io/api/rtx/v1/message/2614')  # acetaminophen - > protein, just NGD as virtual edge
        # message = messenger.fetch_message('https://arax.ncats.io/api/rtx/v1/message/2687')  # neutropenia -> drug, predict_drug_treats_disease and ngd
        # message = messenger.fetch_message('https://arax.ncats.io/api/rtx/v1/message/2701') # observed_expected_ratio and ngd
        # message = messenger.fetch_message('https://arax.ncats.io/api/rtx/v1/message/2703')  # a huge one with jaccard
        # message = messenger.fetch_message('https://arax.ncats.io/api/rtx/v1/message/2706')  # small one with paired concept frequency
        # message = messenger.fetch_message('https://arax.ncats.io/api/rtx/v1/message/2709')  # bigger one with paired concept frequency

    # For local messages due to local changes in code not rolled out to production:
    if params.local:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/Feedback")
        from RTXFeedback import RTXFeedback
        araxdb = RTXFeedback()
        message_dict = araxdb.getMessage(294)  # local version of 2709 but with updates to COHD
        # message_dict = araxdb.getMessage(297)
        # message_dict = araxdb.getMessage(298)
        # message_dict = araxdb.getMessage(299)  # observed_expected_ratio different disease
        # message_dict = araxdb.getMessage(300)  # chi_square
        # message_dict = araxdb.getMessage(302)  # chi_square, different disease
        # message_dict = araxdb.getMessage(304)  # all clinical info, osteoarthritis
        # message_dict = araxdb.getMessage(305)  # all clinical info, neurtropenia
        # message_dict = araxdb.getMessage(306)  # all clinical info, neurtropenia, but with virtual edges
        # message_dict = araxdb.getMessage(307)  # all clinical info, osteoarthritis, but with virtual edges
        # message_dict = araxdb.getMessage(322)  # Parkinsons Jaccard, top 50
        # message_dict = araxdb.getMessage(324)  # chi_square, KG2
        # message_dict = araxdb.getMessage(325)  # chi_square, ngd, KG2
        # message_dict = araxdb.getMessage(326)  # prob drug treats disease as attribute to all edge thrombocytopenia
        # message_dict = araxdb.getMessage(327)
        # add_qnode(name=DOID:1227, id=n00)
        # add_qnode(type=protein, is_set=true, id=n01)
        # add_qnode(type=chemical_substance, id=n02)
        # add_qedge(source_id=n00, target_id=n01, id=e00)
        # add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)
        # expand(edge_id=[e00,e01], kp=ARAX/KG1)
        # overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)
        # overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)
        # overlay(action=overlay_clinical_info, chi_square=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n02)
        # overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n00, target_qnode_id=n01)
        # overlay(action=compute_ngd, virtual_relation_label=N2, source_qnode_id=n00, target_qnode_id=n02)
        # overlay(action=compute_ngd, virtual_relation_label=N3, source_qnode_id=n01, target_qnode_id=n02)
        # resultify(ignore_edge_direction=true)
        # filter_results(action=limit_number_of_results, max_results=100)
        from ARAX_messenger import ARAXMessenger
        message = ARAXMessenger().from_dict(message_dict)

    if message is None:
        print("ERROR: Unable to fetch message")
        return

    # ranker.aggregate_scores(message,response=response)
    ranker.aggregate_scores_dmk(message, response=response)

    # Show the final result
    print(response.show(level=Response.DEBUG))
    print("Results:")

    for result in message.results:
        confidence = result.confidence
        if confidence is None:
            confidence = 0.0
        print("  -" + '{:6.3f}'.format(confidence) + f"\t{result.essence}")
    # print(json.dumps(message.to_dict(),sort_keys=True,indent=2))

    # Show the message number
    print(json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
