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
node_properties = nx.get_node_attributes(g, 'properties')
node_ids = dict()
node_labels = dict()
for node in node_properties.keys():
	node_ids[node] = node_properties[node]['id']
	node_labels[node] = node_properties[node]['category']
for u, v, d in g.edges(data=True):
	source_id = node_ids[u]
	source_label = node_labels[u]
	target_id = node_ids[v]
	target_label = node_labels[v]
	if {source_label, target_label} != {"disease", "phenotypic_feature"}:
		d['cohd_freq'] = 0
		continue
	else:
		if source_label == "disease":
			disease_id = source_id
			symptom_id = target_id
		else:
			disease_id = target_id
			symptom_id = source_id
	# look up these in COHD
	# disease
	disease_omop_id = None
	for distance in [1, 2, 3]:
		xref = QueryCOHD.get_xref_to_OMOP(disease_id, distance=distance)
		for ref in xref:
			if ref['omop_domain_id'] == "Condition":
				disease_omop_id = str(ref["omop_standard_concept_id"])
				break
		if disease_omop_id:
			break
	print("here")
	# symptom, loop over them all and take the largest
	if not disease_omop_id:
		d['cohd_freq'] = 0
	else:
		xrefs = QueryCOHD.get_xref_to_OMOP(symptom_id, distance=1)
		freq = 0
		for xref in xrefs:
			symptom_omop_id = str(xref['omop_standard_concept_id'])
			res = QueryCOHD.get_paired_concept_freq(disease_omop_id, symptom_omop_id)
			print(res)
			if res:
				temp_freq = res['concept_frequency']
				if temp_freq > freq:
					freq = temp_freq
		d['cohd_freq'] = freq


# The other option is to get all the log ratio conditions, then map back to HP and try to intersect them
# with the known HP curies. Problem is that I would have to do this for each disease in the network...


# get the networkx location of the input disease
for node in node_ids.keys():
	if node_ids[node] == disease_id:
		disease_networkx_id = node

# get the networkx location of the other diseases
other_disease_networkx_ids = []
for node in node_ids.keys():
	if node_labels[node] == "disease":
		if node != disease_networkx_id:
			other_disease_networkx_ids.append(node)

# get the median path lengths of all the diseases
other_disease_median_path_weight = dict()
for other_disease_networkx_id in other_disease_networkx_ids:
	other_disease_median_path_weight[node_ids[other_disease_networkx_id]] = np.median([RU.get_networkx_path_weight(g, path, 'cohd_freq') for path in nx.all_simple_paths(g, disease_networkx_id, other_disease_networkx_id, cutoff=2)])
