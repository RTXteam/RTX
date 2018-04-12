# This is an attempt to write a class that will allow flexible query of "return me X that have Y in common with Z" where
# similarity is measured in terms of Jaccard index

# This script will try to return diseases based on gene similarity

import os
import sys
# PyCharm doesn't play well with relative imports + python console + terminal
try:
	from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import ReasoningUtilities as RU


class SimilarNodesInCommon:

	def __init__(self):
		None

	@staticmethod
	def get_similar_nodes_in_common(input_node_ID, input_node_label, association_node_label, input_association_relationship,
				target_association_relationship, target_node_label, threshold=0.2):
		"""
		This function returns the nodes that are associated with an input node based on Jaccard index similarity of
		shared intermediate nodes
		:param input_node_ID: input node ID (in KG)
		:param input_node_label: label of the input node
		:param association_node_label: what kind of node you want to calculate the Jaccard index with
		:param input_association_relationship: how the input node is connected to the association nodes
		:param target_association_relationship: how the target node is connected to the association node
		:param target_node_label: what kind of target nodes to return
		:param threshold: threshold to compute the Jaccard index
		:return: a list of tuples, an error_code, and an error_message. tuple[0] is a target node with tuple[1] jaccard index based on association nodes
		"""
		# get the description
		input_node_description = RU.get_node_property(input_node_ID, 'description')

		# get the nodes associated to the input node
		input_node_associated_nodes = RU.get_one_hop_target(input_node_label, input_node_ID, association_node_label,
															input_association_relationship)

		# Look more steps beyond if we didn't get any directly_interacts_with
		if input_node_associated_nodes == []:
			for max_path_len in range(2, 5):
				input_node_associated_nodes = RU.get_node_names_of_type_connected_to_target(input_node_label, input_node_ID,
																			association_node_label,
																			max_path_len=max_path_len,
																			direction="u")
				if input_node_associated_nodes:
					break

		# Make sure you actually picked up at least one associated node
		if not input_node_associated_nodes:
			error_code = "NoNodesFound"
			error_message = "No %s found for %s." % (association_node_label, input_node_description)
			return [], error_code, error_message

		input_node_associated_nodes_set = set(input_node_associated_nodes)

		# get all the other disease that connect and get the association nodes in common
		# direct connection
		node_label_list = [association_node_label]
		relationship_label_list = [input_association_relationship, target_association_relationship]
		node_of_interest_position = 0
		other_node_IDs_to_intersection_counts = dict()
		if target_node_label == "disease" or target_node_label == "disease":
			target_labels = ["disease", "disease"]
		else:
			target_labels = [target_node_label]
		for target_label in target_labels:
			names2counts, names2nodes = RU.count_nodes_of_type_on_path_of_type_to_label(input_node_ID, input_node_label,
																						target_label, node_label_list,
																						relationship_label_list,
																						node_of_interest_position)
			for ID in names2counts.keys():
				if names2counts[ID] / float(len(
						input_node_associated_nodes_set)) >= threshold:  # if it's below this threshold, no way the Jaccard index will be large enough
					other_node_IDs_to_intersection_counts[ID] = names2counts[ID]

		# check if any other associated nodes passed the threshold
		if not other_node_IDs_to_intersection_counts:
			error_code = "NoNodesFound"
			error_message = "No %s were found with similarity crossing the threshold of %f." % (target_node_label, threshold)
			parent = RU.get_one_hop_target(input_node_label, input_node_ID, input_node_label, "subset_of", direction="r")
			if parent:
				parent = parent.pop()
				error_message += "\n Note that %s is a parent of %s, so you might try that instead." % (
				RU.get_node_property(parent, 'description'), input_node_description)
			return [], error_code, error_message

		# Now for each of the nodes connecting to source, count number of association nodes
		node_label_list = [association_node_label]
		relationship_label_list = [input_association_relationship, target_association_relationship]
		node_of_interest_position = 0
		other_node_counts = dict()
		for target_label in target_labels:
			temp_other_counts = RU.count_nodes_of_type_for_nodes_that_connect_to_label(input_node_ID, input_node_label,
																					   target_label, node_label_list,
																					   relationship_label_list,
																					   node_of_interest_position)
			# add it to the dictionary
			for key in temp_other_counts.keys():
				other_node_counts[key] = temp_other_counts[key]

		# then compute the jaccard index
		node_jaccard_tuples = []
		for other_node_ID in other_node_counts.keys():
			jaccard = 0
			if other_node_ID in other_node_IDs_to_intersection_counts:
				union_card = len(input_node_associated_nodes) + other_node_counts[other_node_ID] - \
							other_node_IDs_to_intersection_counts[other_node_ID]
				jaccard = other_node_IDs_to_intersection_counts[other_node_ID] / float(union_card)
			if jaccard > threshold:
				node_jaccard_tuples.append((other_node_ID, jaccard))

		# Format the results.
		# Maybe nothing passed the threshold
		if not node_jaccard_tuples:
			error_code = "NoNodesFound"
			error_message = "No %s's were found with similarity crossing the threshold of %f." % (target_node_label, threshold)
			parent = RU.get_one_hop_target(input_node_label, input_node_ID, input_node_label, "subset_of", direction="r")
			if parent:
				parent = parent.pop()
				error_message += "\n Note that %s is a parent of %s, so you might try that instead." % (RU.get_node_property(parent, 'description'), input_node_description)
			return [], error_code, error_message

		# Otherwise there are results to return, first sort them largest to smallest
		node_jaccard_tuples_sorted = [(x, y) for x, y in
										sorted(node_jaccard_tuples, key=lambda pair: pair[1], reverse=True)]

		return node_jaccard_tuples_sorted, None, None

	@staticmethod
	def get_similar_nodes_in_common_parameters(node_ID, target_node_label, association_node_label):
		"""
		This function will get the parameters for get_similar_nodes_in_common based on target node, target label, and association label
		:param node_ID: source node ID (name in KG)
		:param target_label: the node types that you want returned
		:param association_node_label: the association node (node in common between source and target) type
		:return: dict, error_code, error_message (dict keys input_node_ID, input_node_label, association_node_label, input_association_relationship,
				target_association_relationship, target_node_label)
		"""
		# Check if node exists
		if not RU.node_exists_with_property(node_ID, 'name'):
			error_message = "Sorry, the disease %s is not yet in our knowledge graph." % node_ID
			error_code = "DiseaseNotFound"
			return dict(), error_code, error_message

		# Get label/kind of node the source is
		input_node_label = RU.get_node_property(node_ID, "label")
		input_node_ID = node_ID

		# Get relationship between source and association label
		rels = RU.get_relationship_types_between(input_node_ID, input_node_label, "", association_node_label, max_path_len=1)
		# TODO: there could be multiple relationship types, for now, let's just pop one
		if not rels:
			error_code = "NoRelationship"
			error_message = "Sorry, the %s %s is not connected to any %s." % (input_node_label, input_node_ID, association_node_label)
			parent = RU.get_one_hop_target(input_node_label, input_node_ID, input_node_label, "subset_of", direction="r")
			if parent:
				parent = parent.pop()
				error_message += "\n Note that %s is a parent of %s, so you might try that instead." % (
				RU.get_node_property(parent, 'description'), RU.get_node_property(input_node_ID, 'description'))
			return dict(), error_code, error_message
		input_association_relationship = rels.pop()

		# Get relationship between target and association label
		rels = RU.get_relationship_types_between("", target_node_label, "", association_node_label, max_path_len=1)
		if not rels:
			error_code = "NoRelationship"
			error_message = "Sorry, no %s is not connected to any %s." % (target_node_label, association_node_label)
			return dict(), error_code, error_message
		target_association_relationship = rels.pop()

		# populate the arguments
		arguments = dict(input_node_ID=input_node_ID,
						input_node_label=input_node_label,
						association_node_label=association_node_label,
						input_association_relationship=input_association_relationship,
						target_association_relationship=target_association_relationship,
						target_node_label=target_node_label)
		return arguments, None, None

	def get_similar_nodes_in_common_source_target_association(self, node_ID, target_node_label, association_node_label, threshold):
		"""
		Based on a triplet, get the similar nodes
		:param node_ID: source node name
		:param target_node_label: target node label
		:param association_node_label: the node type in common between source and target you want to do the Jaccard index on
		:param threshold: minimum Jaccard index to include
		:return: list of tuples, error_code, error_message. tup[0] == node name, tup[1] == jaccard index
		"""
		arguments, error_code, error_message = self.get_similar_nodes_in_common_parameters(node_ID, target_node_label, association_node_label)
		if error_code is not None or error_message is not None:
			return [], error_code, error_message
		else:
			return self.get_similar_nodes_in_common(**arguments, threshold=threshold)


def main():
	Q = SimilarNodesInCommon()
	test_case = 3

	if test_case == 1:
		# Other diseases similar based on phenotypes
		input_node_ID = "DOID:8398"
		input_node_label = "disease"
		association_node_label = "phenotypic_feature"
		input_association_relationship = "has_phenotype"
		target_association_relationship = "has_phenotype"
		target_node_label = "disease"
		threshold = 0.2
		res, error_code, error_message = Q.get_similar_nodes_in_common(input_node_ID, input_node_label, association_node_label, input_association_relationship,
					target_association_relationship, target_node_label, threshold=threshold)
		print(res)
	elif test_case == 2:
		# Other diseases similar based on shared genes
		input_node_ID = "DOID:8398"
		input_node_label = "disease"
		association_node_label = "protein"
		input_association_relationship = "associated_with_condition"
		target_association_relationship = "associated_with_condition"
		target_node_label = "disease"
		threshold = 0.05
		res, error_code, error_message = Q.get_similar_nodes_in_common(input_node_ID, input_node_label, association_node_label,
											input_association_relationship,
											target_association_relationship, target_node_label, threshold=threshold)
		print(res)
	elif test_case == 3:
		# drugs based on shared proteins
		input_node_ID = "DOID:8398"
		input_node_label = "disease"
		association_node_label = "protein"
		input_association_relationship = "associated_with_condition"
		target_association_relationship = "directly_interacts_with"
		target_node_label = "chemical_substance"
		threshold = 0.05
		res, error_code, error_message = Q.get_similar_nodes_in_common(input_node_ID, input_node_label, association_node_label,
											input_association_relationship,
											target_association_relationship, target_node_label, threshold=threshold)
		print(res)


if __name__ == "__main__":
	main()

