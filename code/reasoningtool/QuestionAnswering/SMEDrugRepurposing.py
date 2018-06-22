# This script will return X that are similar to Y based on high Jaccard index of common one-hop nodes Z (X<->Z<->Y)

import os
import sys
import argparse
# PyCharm doesn't play well with relative imports + python console + terminal
try:
	from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import ReasoningUtilities as RU

import FormatOutput
import networkx as nx
try:
	from QueryCOHD import QueryCOHD
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	try:
		from QueryCOHD import QueryCOHD
	except ImportError:
		sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kg-construction'))
		from QueryCOHD import QueryCOHD

from COHDUtilities import COHDUtilities
import SimilarNodesInCommon
import CustomExceptions
import numpy as np


class SMEDrugRepurposing:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=20):
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

		# select top N of them
		diseases_selected = []
		for n, j in node_jaccard_tuples_sorted[0:num_diseases_to_select]:
			diseases_selected.append(n)

		# get subgraph of these with the input disease
		# get all symptoms of input disease
		all_symptoms = RU.get_one_hop_target("disease", disease_id, "phenotypic_feature", "has_phenotype")
		g = RU.get_graph_from_nodes(all_symptoms + diseases_selected + [disease_id], edges=True)

		# weight by COHD data
		#RU.weight_disease_phenotype_by_cohd(g, max_phenotype_oxo_dist=1)

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

		# select the OMIMS TODO: blocking on #248
		# in the mean-time, use them all
		genetic_diseases_selected = diseases_selected

		# select representative diseases
		# Do nothing for now (use all of them)

		# find implicated proteins
		implicated_proteins = []
		for other_disease_id in genetic_diseases_selected:
			implicated_proteins += RU.get_one_hop_target("disease", other_disease_id, "protein", "causes_or_contributes_to")

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
			relevant_drugs += RU.get_one_hop_target("protein", protein_id, "chemical_substance", "directly_interacts_with")

		# get the most frequent drugs
		top_relevant_drugs = RU.get_top_n_most_frequent_from_list(relevant_drugs, num_drugs_keep)







	@staticmethod
	def describe():
		output = "Answers questions of the form: 'What are some potential treatments for $disease?'" + "\n"
		# TODO: subsample disease nodes
		return output


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the form: 'What are some potential treatments for $disease?'",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-d', '--disease', type=str, help="disease curie ID", default="DOID:8398")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
	parser.add_argument('--num_show', type=int, help='Maximum number of results to return', default=20)

	# Parse and check args
	args = parser.parse_args()
	disease_id = args.disease
	use_json = args.json
	describe_flag = args.describe
	num_show = args.num_show


	# Initialize the question class
	Q = SMEDrugRepurposing()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		Q.answer(disease_id, use_json=use_json, num_show=num_show)


if __name__ == "__main__":
	main()
