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
import numpy as np
disease_id = "OMIM:605724"

num_diseases_to_select = 10  # number of diseases with shared phenotypes to keep
num_omim_keep = 10  # number of genetic conditions to keep
num_proteins_keep = 10  # number of proteins implicated in diseases to keep
num_pathways_keep = 10  # number of relevant pathways to keep
num_proteins_in_pathways_keep = 10  # number of proteins in those pathways to keep
num_drugs_keep = 10  # number of drugs that target those proteins to keep

# The kinds of paths we're looking for
path_type = ["gene_mutations_contribute_to", "protein", "participates_in", "pathway", "participates_in", "protein", "physically_interacts_with", "chemical_substance"]

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

# select the omims
diseases_selected = []
for n, j in node_jaccard_tuples_sorted:
	if n.split(":")[0] == "OMIM":
		diseases_selected.append(n)

# if we found no genetic conditions, add error message and quit
if not diseases_selected:
	response.add_error_message("NoGeneticConditions", "There appears to be no genetic conditions with phenotypes in common with %s" % disease_description)
	response.print()
	return

# subset to top N omims that actually have the relationship types that we want:
num_selected = 0
diseases_selected_on_desired_path = []
for selected_disease in diseases_selected:
	if RU.paths_of_type_source_fixed_target_free_exists(selected_disease, "disease", path_type, limit=1):
		diseases_selected_on_desired_path.append(selected_disease)
		num_selected += 1
	if num_selected >= num_omim_keep:
		break

diseases_selected = diseases_selected_on_desired_path

# Find most representative symptoms by consulting COHD. TODO: see if this actually helps anything
# get subgraph of these with the input disease
# get all symptoms of input disease
#all_symptoms = set()
#for selected_disease in diseases_selected:
#	intermediate_phenotypes = RU.get_intermediate_node_ids(disease_id, "disease", "has_phenotype", "phenotypic_feature", "has_phenotype", selected_disease, "disease")
#	all_symptoms.update(intermediate_phenotypes)
# turn it back into a list
#all_symptoms = list(all_symptoms)
# get the subgraph of all relevant symptoms, the omims selected, and the input disease
#g = RU.get_graph_from_nodes(all_symptoms + diseases_selected + [disease_id], edges=True)

# weight by COHD data (if you want to)
#RU.weight_disease_phenotype_by_cohd(g, max_phenotype_oxo_dist=2)

# sort by COHD freq
#disease_path_weight_sorted = RU.get_sorted_path_weights_disease_to_disease(g, disease_id)
#genetic_diseases_selected = []
#num_omim = 0
#for id, weight in disease_path_weight_sorted:
#	if id.split(":")[0] == "OMIM":
#		genetic_diseases_selected.append(id)
#		num_omim += 1
#	if num_omim >= num_omim_keep:
#		break

# in the mean-time, use them all
genetic_diseases_selected = diseases_selected

# select representative diseases
# Do nothing for now (use all of them)

# get drugs that are connected along the paths we want and count how many such paths there are
genetic_diseases_to_chemical_substance_dict = dict()
for selected_disease in genetic_diseases_selected:
	res = RU.count_paths_of_type_source_fixed_target_free(selected_disease, "disease", path_type, limit=num_drugs_keep)
	# add it to our dictionary
	genetic_diseases_to_chemical_substance_dict[selected_disease] = res

# get the unique drugs
drug_counts_tuples = [item for items in genetic_diseases_to_chemical_substance_dict.values() for item in items]
drugs_path_counts = dict()
for drug, count in drug_counts_tuples:
	if drug not in drugs_path_counts:
		drugs_path_counts[drug] = count
	else:
		drugs_path_counts[drug] += count

# put them as tuples in a list, sorted by the ones with the most paths
drugs_path_counts_tuples = []
for drug in drugs_path_counts.keys():
	count = drugs_path_counts[drug]
	drugs_path_counts_tuples.append((drug, count))
drugs_path_counts_tuples.sort(key=lambda x: x[1], reverse=True)



















###################################################
# OLD CODE

num_diseases_to_select = 10  # number of diseases with shared phenotypes to keep
num_omim_keep = 10  # number of genetic conditions to keep
num_proteins_keep = 10  # number of proteins implicated in diseases to keep
num_pathways_keep = 10  # number of relevant pathways to keep
num_proteins_in_pathways_keep = 10  # number of proteins in those pathways to keep
num_drugs_keep = 10  # number of drugs that target those proteins to keep

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

# select the omims
diseases_selected = []
for n, j in node_jaccard_tuples_sorted:
	if n.split(":")[0] == "OMIM":
		diseases_selected.append(n)

# if we found no genetic conditions, add error message and quit
if not diseases_selected:
	response.add_error_message("NoGeneticConditions",
							   "There appears to be no genetic conditions with phenotypes in common with %s" % disease_description)
	response.print()
	#return

# get subgraph of these with the input disease
# get all symptoms of input disease
all_symptoms = RU.get_one_hop_target("disease", disease_id, "phenotypic_feature", "has_phenotype")
# get the subgraph of all symptoms, the omims selected, and the input disease
g = RU.get_graph_from_nodes(all_symptoms + diseases_selected + [disease_id], edges=True)

# weight by COHD data (if you want to)
# RU.weight_disease_phenotype_by_cohd(g, max_phenotype_oxo_dist=1)

# sort by COHD freq
# disease_path_weight_sorted = RU.get_sorted_path_weights_disease_to_disease(g, disease_id)
# genetic_diseases_selected = []
# num_omim = 0
# for id, weight in disease_path_weight_sorted:
#	if id.split(":")[0] == "OMIM":
#		genetic_diseases_selected.append(id)
#		num_omim += 1
#	if num_omim >= num_omim_keep:
#		break

# select the OMIMS TODO: blocking on #248
# in the mean-time, use them all
genetic_diseases_selected = diseases_selected

# select representative diseases
# Do nothing for now (use all of them)

# find implicated proteins
implicated_proteins = []
for other_disease_id in genetic_diseases_selected:
	implicated_proteins += RU.get_one_hop_target("disease", other_disease_id, "protein", "gene_mutations_contribute_to")

# get the most frequent proteins
top_implicated_proteins = RU.get_top_n_most_frequent_from_list(implicated_proteins, num_proteins_keep)

# what subset of these genes is most representative?
# do nothing for now

# what pathways are these genes members of?
relevant_pathways = []
for protein_id in top_implicated_proteins:
	relevant_pathways += RU.get_one_hop_target("protein", protein_id, "pathway", "participates_in")

# get the most frequent pathways
top_relevant_pathways = RU.get_top_n_most_frequent_from_list(relevant_pathways, num_pathways_keep)

# TODO: may need to prune this as it results in a LOT of pathways...

# find proteins in those pathways
proteins_in_pathway = []
for pathway_id in top_relevant_pathways:
	proteins_in_pathway += RU.get_one_hop_target("pathway", pathway_id, "protein", "participates_in")

# get the most frequent proteins
top_proteins_in_pathway = RU.get_top_n_most_frequent_from_list(proteins_in_pathway, num_proteins_in_pathways_keep)

# What drugs target those genes?
relevant_drugs = []
for protein_id in top_proteins_in_pathway:
	relevant_drugs += RU.get_one_hop_target("protein", protein_id, "chemical_substance", "physically_interacts_with")

# get the most frequent drugs
top_relevant_drugs = RU.get_top_n_most_frequent_from_list(relevant_drugs, num_drugs_keep)