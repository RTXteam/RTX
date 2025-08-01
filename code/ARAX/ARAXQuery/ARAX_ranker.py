#!/bin/env python3
import math
import os
import networkx as nx
import numpy as np
import numpy.typing as npt
import scipy.stats
import sys
import json
import ast
import re


from typing import Union, Dict, Callable
from ARAX_response import ARAXResponse
from query_graph_info import QueryGraphInfo

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.result import Result
from openapi_server.models.edge import Edge


edge_confidence_manual_agent = 0.90


def _get_query_graph_networkx_from_query_graph(query_graph: QueryGraph) -> nx.MultiDiGraph:
    query_graph_nx = nx.MultiDiGraph()
    query_graph_nx.add_nodes_from([key for key, node in query_graph.nodes.items() if 'creative_' not in key])
    edge_list = [[edge.subject, edge.object, key, {'weight': 0.0}] for key,edge in query_graph.edges.items() if 'creative_' not in key]
    query_graph_nx.add_edges_from(edge_list)
    return query_graph_nx


def _calculate_final_individual_edge_confidence(base_score: float, attribute_scores: list[float]) -> float:
    
    # use Eric's loop algorithm
    W_r = base_score
    
    sorted_attribute_scores = sorted(attribute_scores, reverse=True)
    for W_i in sorted_attribute_scores:
        W_r = W_r + (1 - W_r) * W_i

    return W_r


def _calculate_final_result_score(all_edge_scores: list[float]) -> float:
    """
    Calculate the final result score for a given edge binding list considering the individual base edge confidence scores. The looping aglorithm is used:
        W_r = W_r + (1 - W_r) * W_i
    
    Here are the steps:
    1. sort all edge scores in descending order
    2. use looping algorithm to combine all sorted edge scores
    
    Here is an example:
    Given score list: 0.994, 0.93, 0.85, 0.68

    We have:
    Round   W_i W_r
    1 0.994   0.994
    2 0.93    0.99958
    3 0.85    0.999937
    4 0.68    0.99997984
    Final result score = 0.99997984
    
    Parameters:
        kg_edge_id_to_edge (dict[str, Edge]): A dictionary mapping edge IDs to Edge objects.
        edge_binding_list (list[Dict]): A list of dictionaries containing edge bindings.
    Returns:
        float: The final combined score between 0 and 1.
    """
    # Calculate the final score
    final_score = _calculate_final_individual_edge_confidence(0, all_edge_scores)

    return final_score

def _process_valid_edge_ids(valid_edge_id_info: dict[str, Dict], kg_edge_id_to_edge: dict[str, Edge]) -> dict[str, dict[str, list[float]]]:
    
    results: dict[str, dict[str, list[float]]] = {}
    
    for qedge_key, edge_info in valid_edge_id_info.items():
        results[qedge_key] = {}
        results[qedge_key]['edge_tuple'] = edge_info['edge_tuple']
        results[qedge_key]['scores'] = []

        same_edge_ids: dict[str, list[float]] = {}
        for edge_binding in edge_info['edge_binding_list']:
            edge_id = edge_binding.id.split(':', 2)[-1]
            if edge_id not in same_edge_ids:
                same_edge_ids[edge_id] = []
            same_edge_ids[edge_id].append(kg_edge_id_to_edge[edge_binding.id].confidence)
            
        # Take the average of the scores for each edge id
        for edge_id, scores in same_edge_ids.items():
            results[qedge_key]['scores'].append(sum(scores) / len(scores))
            
    return results


def _get_weighted_graph_networkx_from_result_graph(kg_edge_id_to_edge: dict[str, Edge],
                                                   qg_nx: Union[nx.MultiDiGraph, nx.MultiGraph],
                                                   result: Result) -> Union[nx.MultiDiGraph,
                                                                            nx.MultiGraph]:
    res_graph = qg_nx.copy()
    qg_edge_tuples = tuple(qg_nx.edges(keys=True, data=True))
    qg_edge_key_to_edge_tuple = {edge_tuple[2]: edge_tuple for edge_tuple in qg_edge_tuples}
    
    # Get all valid edge ids from the edge binding list
    valid_edge_id_info = {}
    for analysis in result.analyses:  # For now we only ever have one Analysis per Result
        for qedge_key, edge_binding_list in analysis.edge_bindings.items():
            if 'creative_' not in qedge_key: # ignore all xDTD/xCRG supported edges
                qedge_tuple = qg_edge_key_to_edge_tuple[qedge_key]
                valid_edge_id_info[qedge_key] = {
                    'edge_tuple': qedge_tuple,
                    'edge_binding_list': edge_binding_list
                }
                
    # Process all valid edge ids (possibly combine multiple duplicate edges into one)
    processed_valid_edge_ids = _process_valid_edge_ids(valid_edge_id_info, kg_edge_id_to_edge)
                
    for qedge_key, edge_info in processed_valid_edge_ids.items():
        qedge_tuple = edge_info['edge_tuple']
        scores = edge_info['scores']
        res_graph[qedge_tuple[0]][qedge_tuple[1]][qedge_tuple[2]]['weight'] = _calculate_final_result_score(scores)
                
    return res_graph


def _get_weighted_graphs_networkx_from_result_graphs(kg_edge_id_to_edge: dict[str, Edge],
                                                     qg_nx: Union[nx.MultiDiGraph, nx.MultiGraph],
                                                     results: list[Result]) -> list[Union[nx.MultiDiGraph,
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
    if type(graph_nx) is nx.MultiGraph:
        ret_graph = nx.Graph()
    elif type(graph_nx) is nx.MultiDiGraph:
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
def _quantile_rank_list(x: list[float]) -> npt.NDArray[np.float64]:
    y = scipy.stats.rankdata(x, method='max')
    return y/len(y)


def _score_networkx_graphs_by_max_flow(result_graphs_nx: list[Union[nx.MultiDiGraph,
                                                                    nx.MultiGraph]]) -> list[float]:
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
                max_flow_value = _calculate_final_individual_edge_confidence(0, max_flow_values_for_node_pairs)
        else:
            max_flow_value = 1.0
        max_flow_values.append(max_flow_value)
    return max_flow_values


def _score_networkx_graphs_by_longest_path(result_graphs_nx: list[Union[nx.MultiDiGraph,
                                                                        nx.MultiGraph]]) -> list[float]:
    result_scores = []
    for result_graph_nx in result_graphs_nx:
        apsp_dict = dict(nx.algorithms.shortest_paths.unweighted.all_pairs_shortest_path_length(result_graph_nx))
        path_len_with_pairs_list = [(node_i, node_j, path_len) for node_i, node_i_dict in apsp_dict.items() for node_j, path_len in node_i_dict.items()]
        max_path_len = max([path_len_with_pair_list_item[2] for path_len_with_pair_list_item in
                            path_len_with_pairs_list])
        pairs_with_max_path_len = [path_len_with_pair_list_item[0:2] for path_len_with_pair_list_item in path_len_with_pairs_list if
                                   path_len_with_pair_list_item[2] == max_path_len]
        map_node_name_to_index = {node_id: node_index for node_index, node_id in enumerate(result_graph_nx.nodes)}
        adj_matrix = nx.to_numpy_array(result_graph_nx)
        adj_matrix_power = np.linalg.matrix_power(adj_matrix, max_path_len)/math.factorial(max_path_len)
        score_list = [adj_matrix_power[map_node_name_to_index[node_i],
                                       map_node_name_to_index[node_j]] for node_i, node_j in pairs_with_max_path_len]
        result_score = _calculate_final_individual_edge_confidence(0, score_list)
        result_scores.append(result_score)
    return result_scores


def _score_networkx_graphs_by_frobenius_norm(result_graphs_nx: list[Union[nx.MultiDiGraph,
                                                                          nx.MultiGraph]]) -> list[float]:
    result_scores = []
    for result_graph_nx in result_graphs_nx:
        adj_matrix = nx.to_numpy_array(result_graph_nx)
        result_score = np.linalg.norm(adj_matrix, ord='fro')
        result_scores.append(float(result_score))
    return result_scores


def _score_result_graphs_by_networkx_graph_scorer(kg_edge_id_to_edge: dict[str, Edge],
                                                  qg_nx: Union[nx.MultiDiGraph, nx.MultiGraph],
                                                  results: list[Result],
                                                  nx_graph_scorer: Callable[[list[Union[nx.MultiDiGraph,
                                                                                        nx.MultiGraph]]],
                                                                            list[float]]) -> list[float]:
    result_graphs_nx = _get_weighted_graphs_networkx_from_result_graphs(kg_edge_id_to_edge,
                                                                        qg_nx,
                                                                        results)
    return nx_graph_scorer(result_graphs_nx)


def _break_ties_and_preserve_order(scores):
    adjusted_scores = scores.copy()
    n = len(scores)
    # if there are more than 1,000 scores, apply the fix to the first 1000 scores and ignore the rest
    if n > 1000:
        n = 1000
    # set all scores below the 1000th to 0
    for i in range(n, len(adjusted_scores)):
        adjusted_scores[i] = 0

    # round all scores to 3 decimal places initially to make adjustment easier
    adjusted_scores = [round(score, 3) for score in adjusted_scores]

    # Adjust scores in descending order to ensure no tie or inversion
    for i in range(1, n):
        if adjusted_scores[i] >= adjusted_scores[i - 1]:
            # Decrease the current score to make it strictly less than the previous score
            new_score = adjusted_scores[i - 1] - 0.001
            adjusted_scores[i] = max(new_score, 0)  # Prevent going below 0

    # Final check to ensure all scores are within bounds
    adjusted_scores = [round(max(min(score, 1), 0), 3) for score in adjusted_scores]

    return adjusted_scores


class ARAXRanker:

    # #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = None
        # how much we trust each of the edge attributes
        self.known_attributes_to_trust = {'probability': 0.8,
                                          'normalized_google_distance': 0.8,
                                          'jaccard_index': 0.5,
                                          'probability_treats': 0.8,
                                          'paired_concept_frequency': 0.5,
                                          'observed_expected_ratio': 0.8,
                                          'chi_square': 0.8,
                                          'chi_square_pvalue': 0.8,
                                          'MAGMA-pvalue': 1.0,
                                          'Genetics-quantile': 1.0,
                                          'pValue': 1.0,
                                          'fisher_exact_test_p-value': 0.8,
                                          'Richards-effector-genes': 0.5,
                                          'feature_coefficient': 1.0,
                                          'CMAP similarity score': 1.0,
                                          }
        # how much we trust each data source
        self.data_source_base_weights = {'infores:semmeddb': 0.5, # downweight semmeddb
                                         'infores:text-mining-provider-targeted': 0.85,
                                         'infores:drugcentral': 0.93,
                                         'infores:drugbank': 0.99
                                         # we can define the more customized weights for other data sources here later if needed.
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

    def edge_attribute_score_combiner(self, edge_key, edge):
        """
        This function takes a single edge and decides how to combine its attribute scores into a single confidence
        Eventually we will want
        1. To weight different attributes by different amounts
        2. Figure out what to do with edges that have no attributes
        """
        
        edge_default_base = 0.5
        edge_attribute_score_list = []
        
        #  Retrieve edge data source
        data_source = edge_key.split('--')[-1]
        
        # find data source from edge_key
        if data_source in self.data_source_base_weights:
            base = self.data_source_base_weights[data_source]
        elif 'infores' in data_source: # default score for other data sources
            base = edge_default_base
        else: # virtual edges or inferred edges
            base = 0 # no base score for these edges. Its score is based on its attribute scores.
        
        if edge.attributes is not None:
            for edge_attribute in edge.attributes:
                # if edge_attribute.original_attribute_name == "biolink:knowledge_level": # this probably means it's a fact or high-quality edge from reliable source, we tend to trust it.
                # TODO: we might consider the value from this attrubute name in the future

                # if a specific attribute found, normalize its score and add it to the list
                if edge_attribute.original_attribute_name is not None:
                    normalized_score = self.edge_attribute_score_normalizer(edge_attribute.original_attribute_name, edge_attribute.value)
                else:
                    normalized_score = self.edge_attribute_score_normalizer(edge_attribute.attribute_type_id, edge_attribute.value)
                if edge_attribute.attribute_type_id == "biolink:publications" and data_source == "infores:semmeddb":
                    # only publications from semmeddb are used to calculate the confidence in this way
                    normalized_score = self.edge_attribute_publication_normalizer(edge_attribute.attribute_type_id, edge_attribute.value)

                #  Collect scores from attributes that we used to calculate the final confidence
                if self.known_attributes_to_trust.get(edge_attribute.original_attribute_name, None):
                    if normalized_score > 0:
                        edge_attribute_score_list.append(normalized_score * self.known_attributes_to_trust[edge_attribute.original_attribute_name])
                elif self.known_attributes_to_trust.get(edge_attribute.attribute_type_id, None):
                    if normalized_score > 0:
                        edge_attribute_score_list.append(normalized_score * self.known_attributes_to_trust[edge_attribute.attribute_type_id])
                elif edge_attribute.attribute_type_id == "biolink:publications" and data_source == "infores:semmeddb":
                    if normalized_score > 0:
                        edge_attribute_score_list.append(normalized_score)
                else:
                    # this means we have no current normalization of this kind of attribute,
                    # so don't do anything to the score since we don't know what to do with it yet
                    # add more rules in the future
                    continue 
            
            if len(edge_attribute_score_list) == 0: # if no appropriate attribute for score calculation, set the confidence to default base score (0.5)
                edge_confidence = base
            else:
                edge_confidence = _calculate_final_individual_edge_confidence(base, edge_attribute_score_list)
        else:
            edge_confidence = base

        return edge_confidence

    def edge_attribute_score_normalizer(self, edge_attribute_name: str, edge_attribute_value) -> float:
        """
        Takes an input edge attribute and value, dispatches it to the appropriate method that translates the value into
        something in the interval [0,1] where 0 is worse and 1 is better
        """
        if edge_attribute_name not in self.known_attributes_to_trust:
            return -1  # TODO: might want to change this
        else:
            if edge_attribute_value == "no value!":
                edge_attribute_value = 0
            try:
                # check to see if it's convertible to a float (will catch None's as well)
                edge_attribute_value = float(edge_attribute_value)
            except TypeError:
                return 0.
            except ValueError:
                return 0.
            # check to see if it's NaN, if so, return 0
            if np.isnan(edge_attribute_value):
                return 0.
            # else it's all good to proceed
            else:
                # Fix hyphens or spaces to underscores in names
                edge_attribute_name = re.sub(r'[- \:]','_',edge_attribute_name)
                # then dispatch to the appropriate function that does the score normalizing to get it to be in [0, 1] with 1 better
                return getattr(self, '_' + self.__class__.__name__ + '__normalize_' + edge_attribute_name)(value=edge_attribute_value)

    def edge_attribute_publication_normalizer(self, attribute_type_id: str, edge_attribute_value) -> float:
        """
        Normalize the publication count into a value between 0 and 1
        """
        if attribute_type_id != "biolink:publications":
            return -1
        
        if isinstance(edge_attribute_value,str):
            publications = [edge_attribute_value]
        elif isinstance(edge_attribute_value,list):
            publications = edge_attribute_value
        else:
            return -1 # this means the data format storing publications has changed.
        
        n_publications = len(set(publications))
        if n_publications == 0:
            pub_value = 0.0001
        else:
            pub_value = np.log(n_publications)
            max_value = 1.0
            curve_steepness = 3.16993
            logistic_midpoint = 1.60943 # log(5) = 1.60943 meaning having 5 publications is a mid point
            normalized_value = max_value / float(1 + np.exp(-curve_steepness * (pub_value - logistic_midpoint)))
        return normalized_value

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

    def __normalize_chi_square_pvalue(self, value):
        return self.__normalize_chi_square(value)

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

    def __normalize_pValue(self, value):
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
        the quantile as-is is best. With DMK, SAR, EWD.
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
        try:
            if value <= np.finfo(float).eps:
                normalized_value = 1.
            else:
                value = -np.log(value)
                max_value = 1.0
                curve_steepness = 3
                logistic_midpoint = 2.7
                normalized_value = max_value / float(1 + np.exp(-curve_steepness * (value - logistic_midpoint)))
        except RuntimeWarning:  # this is the case when value is 0 (or nearly so), so should award the max value
            normalized_value = 1.

        return normalized_value

    def __normalize_CMAP_similarity_score(self, value):
        normalized_value = abs(value/100)
        return normalized_value

    def __normalize_Richards_effector_genes(self, value):
        return value

    def __normalize_feature_coefficient(self, value):
        log_abs_value = np.log(abs(value))
        max_value = 1
        curve_steepness = 2.75
        logistic_midpoint = 0.15
        normalized_value = max_value / float(1+np.exp(-curve_steepness*(log_abs_value - logistic_midpoint)))
        return normalized_value

    def aggregate_scores_dmk(self, response):
        """
        Take in a message,
        decorate all edges with confidences,
        take each result and use edge confidences and other info to populate result confidences,
        populate the result.row_data and message.table_column_names
        Does everything in place (no result returned)
        """
        self.response = response
        response.debug("Starting to rank results")
        message = response.envelope.message
        self.message = message

        # #### Compute some basic information about the query_graph
        query_graph_info = QueryGraphInfo()
        result = query_graph_info.assess(message)
        # response.merge(result)
        # if result.status != 'OK':
        #     print(response.show(level=ARAXResponse.DEBUG))
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
        for edge_key, edge in message.knowledge_graph.edges.items():
            kg_edge_id_to_edge[edge_key] = edge
            if edge.attributes is not None:
                for edge_attribute in edge.attributes:
                    for attribute_name in self.known_attributes_to_trust:
                        if edge_attribute.original_attribute_name == attribute_name or edge_attribute.attribute_type_id == attribute_name:
                            if edge_attribute.value == "no value!":
                                edge_attribute.value = 0
                                value = 0
                            else:
                                try:
                                    value = float(edge_attribute.value)
                                except ValueError:
                                    continue
                                except TypeError:
                                    continue
                            # initialize if not None already
                            if attribute_name not in score_stats:
                                score_stats[attribute_name] = {'minimum': None, 'maximum': None}  # FIXME: doesn't handle the case when all values are inf|NaN
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
                        "No non-infinite value was encountered in any edge attribute in the knowledge graph.")
        response.info(f"Summary of available edge metrics: {score_stats}")

        edge_ids_manual_agent = set()
        # Loop over the entire KG and normalize and combine the score of each edge, place that information in the confidence attribute of the edge
        for edge_key, edge in message.knowledge_graph.edges.items():
            if edge.attributes is not None:
                edge_attributes = {x.original_attribute_name:x.value for x in edge.attributes}
                for edge_attribute in edge.attributes:
                    if edge_attribute.attribute_type_id == "biolink:agent_type" and edge_attribute.value == "manual_agent":
                        edge_attributes['confidence'] = edge_confidence_manual_agent
                        edge.confidence = edge_confidence_manual_agent
                        edge_ids_manual_agent.add(edge_key)
                        break
            else:
                edge_attributes = {}

            if edge_attributes.get("confidence", None):
                edge.confidence = edge_attributes['confidence']
            else:                
                edge.confidence = self.edge_attribute_score_combiner(edge_key, edge)

        # Now that each edge has a confidence attached to it based on it's attributes, we can now:
        # 1. consider edge types of the results
        # 2. number of edges in the results
        # 3. possibly conflicting information, etc.

        results = message.results

        ###################################
        # TODO: Replace this with a more "intelligent" separate function
        # now we can loop over all the results, and combine their edge confidences (now populated)
        qg_nx = _get_query_graph_networkx_from_query_graph(message.query_graph)
        kg_edge_id_to_edge = self.kg_edge_id_to_edge
        kg_edge_id_to_edge = self.kg_edge_id_to_edge

        ranks_list = list(map(_quantile_rank_list,
                              map(lambda scorer_func: _score_result_graphs_by_networkx_graph_scorer(kg_edge_id_to_edge,
                                                                                                    qg_nx,
                                                                                                    results,
                                                                                                    scorer_func),
                                  [_score_networkx_graphs_by_max_flow,
                                   _score_networkx_graphs_by_longest_path,
                                   _score_networkx_graphs_by_frobenius_norm])))

        result_scores = sum(ranks_list)/float(len(ranks_list))


        for result, score in zip(results, result_scores):
            result.analyses[0].score = score  # For now we only ever have one Analysis per Result

        ###################################

            # Make all scores at least 0.001. This is all way low anyway, but let's not have anything that rounds to zero
            # This is a little bad in that 0.0005 becomes better than 0.0011, but this is all way low, so who cares
            if result.analyses[0].score < 0.001:
                result.analyses[0].score += 0.001

            # Round to reasonable precision. Keep only 3 digits after the decimal
            score = int(result.analyses[0].score * 1000 + 0.5) / 1000.0

            result.row_data = [score, result.essence, result.essence_category]

        # Add table columns name
        response.envelope.table_column_names = ['score', 'essence', 'essence_category']

        # Re-sort the final results
        message.results.sort(key=lambda result: result.analyses[0].score, reverse=True)
        # break ties and preserve order, round to 3 digits and make sure none are < 0
        scores_with_ties = [result.analyses[0].score for result in message.results]
        scores_without_ties = _break_ties_and_preserve_order(scores_with_ties)
        # print(scores_with_ties)
        # print(scores_without_ties)
        # reinsert these scores into the results
        for result, score in zip(message.results, scores_without_ties):
            result.analyses[0].score = score
            result.row_data[0] = score
        response.debug("Results have been ranked and sorted")



##########################################################################################


def main():
    # For faster testing, cache the testing messages locally
    import requests_cache
    requests_cache.install_cache('ARAX_ranker_testing_cache')

    import argparse
    argparser = argparse.ArgumentParser(description='Ranker system')
    argparser.add_argument('--local', action='store_true', help='If set, use local ResponseCache database to fetch messages')
    params = argparser.parse_args()

    # --- Create a response object
    response = ARAXResponse()
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
        sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ResponseCache")
        from response_cache import ResponseCache
        response_cache = ResponseCache()
        message_dict = response_cache.get_response(314204)
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
        # add_qedge(subject=n00, object=n01, id=e00)
        # add_qedge(subject=n01, object=n02, id=e01, type=physically_interacts_with)
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
    print(response.show(level=ARAXResponse.DEBUG))
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
