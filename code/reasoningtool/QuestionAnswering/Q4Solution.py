# This script will try to return diseases based on phenotypic similarity

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


class Q4:

	def __init__(self):
		None

	def answer(self, disease_ID, use_json=False, threshold=0.2):

		# Initialize the response class
		response = FormatOutput.FormatResponse(4)

		# Check if node exists
		if not RU.node_exists_with_property(disease_ID, 'name'):
			error_message = "Sorry, the disease %s is not yet in our knowledge graph." % disease_ID
			error_code = "DiseaseNotFound"
			if not use_json:
				print(error_message)
				return 1
			else:
				response.add_error_message(error_code, error_message)
				response.print()
				return 1

		# Get label/kind of node the source is
		disease_label = RU.get_node_property(disease_ID, "label")
		if disease_label != "disont_disease" and disease_label != "omim_disease":
			error_message = "Sorry, the input has label %s and needs to be one of: omim_disease, disont_disease." \
							" Please try a different term" % disease_label
			error_code = "NotADisease"
			if not use_json:
				print(error_message)
				return 1
			else:
				response.add_error_message(error_code, error_message)
				response.print()
				return 1

		# get the description
		disease_description = RU.get_node_property(disease_ID, 'description')

		# get the phenotypes associated to the disease
		disease_phenotypes = RU.get_one_hop_target(disease_label, disease_ID, "phenont_phenotype", "phenotype_assoc_with")

		# Look more steps beyond if we didn't get any targets
		if disease_phenotypes == []:
			for max_path_len in range(2, 5):
				disease_phenotypes = RU.get_node_names_of_type_connected_to_target(disease_label, disease_ID, "phenont_phenotype", max_path_len=max_path_len, direction="u")
				if disease_phenotypes:
					break
		#print("Total of %d phenotypes" % len(disease_phenotypes))

		# Make sure you actually picked up at least one phenotype
		if not disease_phenotypes:
			error_message = "No phenotypes found for this disease."
			error_code = "NoPhenotypesFound"
			if not use_json:
				print(error_message)
				return 1
			else:
				response.add_error_message(error_code, error_message)
				response.print()
				return 1
		disease_phenotypes_set = set(disease_phenotypes)

		# get all the other disease that connect and get the phenotypes in common
		other_disease_IDs_to_intersection_counts = dict()
		for target_label in ["disont_disease", "omim_disease"]:

			# direct connection
			#print("direct")
			node_label_list = ["phenont_phenotype"]
			relationship_label_list = ["phenotype_assoc_with", "phenotype_assoc_with"]
			node_of_interest_position = 0
			names2counts, names2nodes = RU.count_nodes_of_type_on_path_of_type_to_label(disease_ID, disease_label, target_label, node_label_list,
													 relationship_label_list, node_of_interest_position)
			for ID in names2counts.keys():
				if names2counts[ID] / float(len(disease_phenotypes_set)) >= threshold:  # if it's below this threshold, no way the Jaccard index will be large enough
					other_disease_IDs_to_intersection_counts[ID] = names2counts[ID]

		if not other_disease_IDs_to_intersection_counts:
			error_code = "NoDiseasesFound"
			error_message = "No diseases were found with similarity crossing the threshold of %f." % threshold
			parent = RU.get_one_hop_target(disease_label, disease_ID, disease_label, "is_parent_of").pop()
			if parent:
				error_message += "\n Note that %s is a parent disease to %s, so you might try that instead." % (RU.get_node_property(parent, 'description'), disease_description)
			if not use_json:
				print(error_message)
				return 1
			else:
				response.add_error_message(error_code, error_message)
				response.print()
				return 1

		#print("Total number of other diseases %d" % len(list(other_disease_IDs_to_intersection_counts.keys())))
		# Now for each of the diseases in here, compute the actual Jaccard index
		disease_jaccard_tuples = []
		#i = 0
		for other_disease_ID in other_disease_IDs_to_intersection_counts.keys():
			#print(i)
			#i += 1
			#print(other_disease_ID)
			# get the phenotypes associated to the disease
			if other_disease_ID.split(":")[0] == "DOID":
				other_disease_label = "disont_disease"
			if other_disease_ID.split(":")[0] == "OMIM":
				other_disease_label = "omim_disease"
			other_disease_phenotypes = RU.get_one_hop_target(other_disease_label, other_disease_ID, "phenont_phenotype", "phenotype_assoc_with")

			# Look more steps beyond if we didn't get any targets
			if other_disease_phenotypes == []:
				for max_path_len in range(2, 5):
					other_disease_phenotypes = RU.get_node_names_of_type_connected_to_target(other_disease_label, other_disease_ID,
																					   "phenont_phenotype",
																					   max_path_len=max_path_len,
																					   direction="u")
					if other_disease_phenotypes:
						break

			# compute the Jaccard index
			if not other_disease_phenotypes:
				jaccard = 0
			else:
				other_disease_phenotypes_set = set(other_disease_phenotypes)
				jaccard = other_disease_IDs_to_intersection_counts[other_disease_ID] / float(
					len(list(disease_phenotypes_set.union(other_disease_phenotypes_set))))
				#print("jaccard %f" % jaccard)
			if jaccard > threshold:
				disease_jaccard_tuples.append((other_disease_ID, jaccard))

		# Format the results.
		# Maybe nothing passed the threshold
		if not disease_jaccard_tuples:
			error_code = "NoDiseasesFound"
			error_message = "No diseases were found with similarity crossing the threshold of %f." % threshold
			parent = RU.get_one_hop_target(disease_label, disease_ID, disease_label, "is_parent_of")
			if parent:
				error_message += "\n Note that %s is a parent disease to %s, so you might try that instead." % (RU.get_node_property(parent, 'description'), disease_description)
			if not use_json:
				print(error_message)
				return 1
			else:
				response.add_error_message(error_code, error_message)
				return 1

		# Otherwise there are results to return, first sort them largest to smallest
		disease_jaccard_tuples_sorted = [(x, y) for x, y in sorted(disease_jaccard_tuples, key=lambda pair: pair[1], reverse=True)]
		if not use_json:
			to_print = "The diseases similar to %s are: \n" % disease_description
			for other_disease_ID, jaccard in disease_jaccard_tuples_sorted:
				to_print += "%s\t%s\tJaccard %f\n" % (other_disease_ID, RU.get_node_property(other_disease_ID, 'description'), jaccard)
			print(to_print)
		else:
			for other_disease_ID, jaccard in disease_jaccard_tuples_sorted:
				to_print = "%s is similar to the disease %s with similarity value %f" % (disease_description, RU.get_node_property(other_disease_ID, 'decription'), jaccard)
				g = RU.get_node_as_graph(other_disease_ID)
				response.add_subgraph(g.nodes(data=True), g.edges(data=True), to_print, jaccard)
			response.print()

	def describe(self):
		output = "Answers questions of the form: 'What diseases have phenotypes similar to X?' where X is a disease." + "\n"
		# TODO: subsample disease nodes
		return output


# Tests
def testQ4_answer():
	Q = Q4()


def test_Q4_describe():
	Q = Q4()
	res = Q.describe()


def test_suite():
	testQ4_answer()
	test_Q4_describe()


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the type 'What diseases have phenotypes similar to X?'.",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-d', '--disease', type=str, help="Disease DOID (or other name of node in the KG)", default="DOID:8398")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
	parser.add_argument('--threshold', type=float, help='Jaccard index threshold (only report other diseases above this)', default=0.2)

	# Parse and check args
	args = parser.parse_args()
	disease_ID = args.disease
	use_json = args.json
	describe_flag = args.describe
	threshold = args.threshold

	# Initialize the question class
	Q = Q4()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		res = Q.answer(disease_ID, use_json=use_json, threshold=threshold)


if __name__ == "__main__":
	main()


def old_code():
	# one is parent of
	print("one")
	node_label_list = [disease_label, "phenont_phenotype"]
	relationship_label_list = ["is_parent_of", "phenotype_assoc_with", "phenotype_assoc_with"]
	node_of_interest_position = 1
	print(RU.count_nodes_of_type_on_path_of_type_to_label(disease_ID, disease_label,
														  target_label, node_label_list,
														  relationship_label_list,
														  node_of_interest_position, debug=True))
	names2counts, names2nodes = RU.count_nodes_of_type_on_path_of_type_to_label(disease_ID, disease_label,
																				target_label, node_label_list,
																				relationship_label_list,
																				node_of_interest_position)
	for ID in names2counts.keys():
		if names2counts[ID] / float(len(
				disease_phenotypes_set)) >= threshold:  # if it's below this threshold, no way the Jaccard index will be large enough
			other_disease_IDs_to_intersection_counts[ID] = names2counts[ID]

	# other is parent of
	print("other")
	node_label_list = ["phenont_phenotype", target_label]
	relationship_label_list = ["phenotype_assoc_with", "phenotype_assoc_with", "is_parent_of"]
	node_of_interest_position = 0
	names2counts, names2nodes = RU.count_nodes_of_type_on_path_of_type_to_label(disease_ID,
																				disease_label,
																				target_label,
																				node_label_list,
																				relationship_label_list,
																				node_of_interest_position)
	for ID in names2counts.keys():
		if names2counts[ID] / float(len(
				disease_phenotypes_set)) >= threshold:  # if it's below this threshold, no way the Jaccard index will be large enough
			other_disease_IDs_to_intersection_counts[ID] = names2counts[ID]

	# Both is parent of
	print("both")
	node_label_list = [disease_label, "phenont_phenotype", target_label]
	relationship_label_list = ["is_parent_of", "phenotype_assoc_with", "phenotype_assoc_with", "is_parent_of"]
	node_of_interest_position = 1
	names2counts, names2nodes = RU.count_nodes_of_type_on_path_of_type_to_label(disease_ID,
																				disease_label,
																				target_label,
																				node_label_list,
																				relationship_label_list,
																				node_of_interest_position)
	for ID in names2counts.keys():
		if names2counts[ID] / float(len(
				disease_phenotypes_set)) >= threshold:  # if it's below this threshold, no way the Jaccard index will be large enough
			other_disease_IDs_to_intersection_counts[ID] = names2counts[ID]