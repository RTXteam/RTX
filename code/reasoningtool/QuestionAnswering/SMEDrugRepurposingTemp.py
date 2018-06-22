# This is a script for testing
import os
import sys
import argparse
import ReasoningUtilities as RU
import FormatOutput
import networkx as nx
from QueryCOHD import QueryCOHD
from COHDUtilities import COHDUtilities
import CustomExceptions
import SimilarNodesInCommon
disease_id = "DOID:8398"
# Initialize the response class
response = FormatOutput.FormatResponse(6)

# get the description of the disease
disease_description = RU.get_node_property(disease_id, 'name')

# Initialize the response class
response = FormatOutput.FormatResponse(6)

# get the description of the disease
disease_description = RU.get_node_property(disease_id, 'name')

# What are the defining symptoms of the disease?
# get diseases that have many raw symptoms in common
# select top N of them
# get subraph of these with the input disease
# weight by COHD data
# pick diseases with maximal (since frequency) average distance i.e. maximal expected graph distance

# get disease that have many raw symptoms in common
similar_nodes_in_common = SimilarNodesInCommon.SimilarNodesInCommon()
node_jaccard_tuples_sorted, error_code, error_message = similar_nodes_in_common.get_similar_nodes_in_common_source_target_association(
	disease_id, "disease", "phenotypic_feature", 0)
# select top N of them
num_diseases_to_select = 10
diseases_selected = []
for n, j in node_jaccard_tuples_sorted[0:num_diseases_to_select]:
	diseases_selected.append(n)

# get subgraph of these with the input disease
# get all symptoms of input disease
all_symptoms = RU.get_one_hop_target("disease", disease_id, "phenotypic_feature", "has_phenotype")
g = RU.get_graph_from_nodes(all_symptoms + diseases_selected + [disease_id], edges=True)

# weight by COHD data
RU.weight_disease_phenotype_by_cohd(g, max_phenotype_oxo_dist=1)

# get the networkx location of the input disease
node_properties = nx.get_node_attributes(g, 'properties')
node_ids = dict()
node_labels = dict()
for node in node_properties.keys():
	node_ids[node] = node_properties[node]['id']
	node_labels[node] = node_properties[node]['category']
for node in node_ids.keys():
	if node_ids[node] == disease_id:
		disease_networkx_id = node

# get the networkx location of the other diseases
other_disease_networkx_ids = []
for node in node_ids.keys():
	if node_labels[node] == "disease":
		if node != disease_networkx_id:
			other_disease_networkx_ids.append(node)

# get the mean path lengths of all the diseases
other_disease_median_path_weight = dict()
for other_disease_networkx_id in other_disease_networkx_ids:
	other_disease_median_path_weight[node_ids[other_disease_networkx_id]] = np.median(
		[RU.get_networkx_path_weight(g, path, 'cohd_freq') for path in
		 nx.all_simple_paths(g, disease_networkx_id, other_disease_networkx_id, cutoff=2)])

other_disease_median_path_weight_sorted = []
for key in other_disease_median_path_weight.keys():
	weight = other_disease_median_path_weight[key]
	other_disease_median_path_weight_sorted.append((key, weight))

other_disease_median_path_weight_sorted.sort(key=lambda x: x[1], reverse=True)