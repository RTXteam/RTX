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
	from QueryCOHD import QueryCOHD


class CommonSymptomsSolution:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=20):
		"""
		"""

		# Initialize the response class
		response = FormatOutput.FormatResponse(6)

		# get the description
		disease_description = RU.get_node_property(disease_id, 'description')

		# get subgraph of all all the symptom nodes connecting to the disease
		g = RU.return_subgraph_paths_of_type(disease_id,"disease",None,"phenotypic_feature",["has_phenotype"], directed=False)

		# decorate with cohd data
		RU.weight_graph_with_cohd_frequency(g, normalized=False)  # TODO: check if normalized on returns better results

		# sort the phenotypes by frequency
		top_n_nodes = []
		names = nx.get_node_attributes(g, 'names')
		descriptions = nx.get_node_attributes(g, 'description')
		labels = nx.get_node_attributes(g, 'labels')

		# get the node corresponding to the disease
		disease_node = None
		for node in names.keys():
			if "disease" == list(set(labels[node]) - {"Base"}).pop():
				disease_node = node

		# get all the nodes and the frequencies in one place
		node_freq_tuples = []
		for node in names.keys():
			if "phenotypic_feature" == list(set(labels[node])-{"Base"}).pop():
				# get the corresponding edge frequency (try both directions)
				edge_data = g.get_edge_data(disease_node, node)
				if "cohd_freq" in edge_data and isinstance(edge_data["cohd_freq"], float):
					freq = edge_data["cohd_freq"]
				else:
					edge_data = g.get_edge_data(node, disease_node)
					if "cohd_freq" in edge_data and isinstance(edge_data["cohd_freq"], float):
						freq = edge_data["cohd_freq"]
					else:
						freq = 0
				node_freq_tuples.append((node,freq))

		# sort the node freqs
		node_freq_tuples_sorted = sorted(node_freq_tuples, key=lambda x: x[1], reverse=True)

		# reduce to top 100
		node_freq_tuples_sorted_top_n = node_freq_tuples_sorted
		if len(node_freq_tuples_sorted_top_n) > num_show:
			node_freq_tuples_sorted_top_n = node_freq_tuples_sorted_top_n[0:num_show]

		# good nodes
		good_nodes = set([tup[0] for tup in node_freq_tuples_sorted_top_n])

		# all nodes
		all_nodes = set([tup[0] for tup in node_freq_tuples_sorted])

		# remove the other nodes from the graph
		g.remove_nodes_from(all_nodes-good_nodes)

		######################################################################
		# Stopped here 5/2/18
		# check for an error
		if error_code is not None or error_message is not None:
			if not use_json:
				print(error_message)
				return
			else:
				response.add_error_message(error_code, error_message)
				response.print()
				return

		# Otherwise return the results
		if not use_json:
			to_print = "The %s's involving similar %s's as %s are: \n" % (target_node_type, association_node_type, source_node_description)
			for other_disease_ID, jaccard in node_jaccard_tuples_sorted:
				to_print += "%s\t%s\tJaccard %f\n" % (other_disease_ID, RU.get_node_property(other_disease_ID, 'description'), jaccard)
			print(to_print)
		else:
			node_jaccard_ID_sorted = [id for id, jac in node_jaccard_tuples_sorted]

			# print(RU.return_subgraph_through_node_labels(source_node_ID, source_node_label, node_jaccard_ID_sorted, target_node_type,
			#										[association_node_type], with_rel=[], directed=True, debug=True))

			# get the entire subgraph
			g = RU.return_subgraph_through_node_labels(source_node_ID, source_node_label, node_jaccard_ID_sorted,
													target_node_type,
													[association_node_type], with_rel=[], directed=False,
													debug=False)

			# extract the source_node_number
			for node, data in g.nodes(data=True):
				if data['properties']['name'] == source_node_ID:
					source_node_number = node
					break

			# Get all the target numbers
			target_id2numbers = dict()
			node_jaccard_ID_sorted_set = set(node_jaccard_ID_sorted)
			for node, data in g.nodes(data=True):
				if data['properties']['name'] in node_jaccard_ID_sorted_set:
					target_id2numbers[data['properties']['name']] = node

			for other_disease_ID, jaccard in node_jaccard_tuples_sorted:
				to_print = "The %s %s involves similar %s's as %s with similarity value %f" % (
					target_node_type, RU.get_node_property(other_disease_ID, 'description'), association_node_type,
					source_node_description, jaccard)

				# get all the shortest paths between source and target
				all_paths = nx.all_shortest_paths(g, source_node_number, target_id2numbers[other_disease_ID])

				# get all the nodes on these paths
				try:
					rel_nodes = set()
					for path in all_paths:
						for node in path:
							rel_nodes.add(node)

					if rel_nodes:
						# extract the relevant subgraph
						sub_g = nx.subgraph(g, rel_nodes)

						# add it to the response
						response.add_subgraph(sub_g.nodes(data=True), sub_g.edges(data=True), to_print, jaccard)
				except:
					pass
			response.print()

	@staticmethod
	def describe():
		output = "Answers questions of the form: 'What diseases involve similar genes to disease X?' where X is a disease." + "\n"
		# TODO: subsample disease nodes
		return output


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the type 'What X involve similar Y as Z?'.",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-s', '--source', type=str, help="source node name (or other name of node in the KG)", default="DOID:8398")
	parser.add_argument('-t', '--target', type=str, help="target node type", default="disease")
	parser.add_argument('-a', '--association', type=str, help="association node type", default="phenotypic_feature")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
	parser.add_argument('--threshold', type=float, help='Jaccard index threshold (only report other diseases above this)', default=0.2)
	parser.add_argument('-n', '--num_res', type=int, help='Maximum number of results to return', default=20)

	# Parse and check args
	args = parser.parse_args()
	source_node_ID = args.source
	use_json = args.json
	describe_flag = args.describe
	threshold = args.threshold
	target_node_type = args.target
	association_node_type = args.association
	n = args.num_res

	# Initialize the question class
	Q = SimilarityQuestionSolution()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		Q.answer(source_node_ID, target_node_type, association_node_type, use_json=use_json, threshold=threshold, n=n)


if __name__ == "__main__":
	main()
