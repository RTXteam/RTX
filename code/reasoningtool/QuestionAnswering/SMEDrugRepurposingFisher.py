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
from fisher_exact import rtx_fisher_test


class SMEDrugRepurposing:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=20):
		num_omim_keep = 10  # number of genetic conditions to keep
		num_drugs_keep = 10  # number of drugs that target those proteins to keep

		# The kinds of paths we're looking for
		path_type = ["gene_mutations_contribute_to", "protein", "participates_in", "pathway", "participates_in",
					 "protein", "physically_interacts_with", "chemical_substance"]

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

		genetic_diseases_selected = diseases_selected_on_desired_path


		# select representative diseases
		# Do nothing for now (use all of them)

		# get drugs that are connected along the paths we want and count how many such paths there are
		genetic_diseases_to_chemical_substance_dict = dict()
		for selected_disease in genetic_diseases_selected:
			res = RU.count_paths_of_type_source_fixed_target_free(selected_disease, "disease", path_type,
																  limit=num_drugs_keep)
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

		if not use_json:
			for drug, count in drugs_path_counts_tuples:
				name = RU.get_node_property(drug, "name", node_label="chemical_substance")
				print("%s: %d\n" % (name, count))

	@staticmethod
	def describe():
		output = "Answers questions of the form: 'What are some potential treatments for $disease?'" + "\n"
		# TODO: subsample disease nodes
		return output


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the form: 'What are some potential treatments for $disease?'",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-d', '--disease', type=str, help="disease curie ID", default="OMIM:605724")
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
