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

import CustomExceptions


class CommonSymptomsSolution:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=20, rev=True, normalize=False):
		"""
		"""

		# Initialize the response class
		response = FormatOutput.FormatResponse(6)

		# get the description
		disease_description = RU.get_node_property(disease_id, 'name')

		# get subgraph of all all the symptom nodes connecting to the disease
		try:
			g = RU.return_subgraph_paths_of_type(disease_id, "disease", None, "phenotypic_feature", ["has_phenotype"], directed=False)
		except CustomExceptions.EmptyCypherError:
			error_code = "EmptyGraph"
			error_message = "Sorry, but there are no phenotypes associated to %s" % disease_description
			response.add_error_message(error_code, error_message)
			response.print()
			return 1

		# decorate with cohd data
		RU.weight_graph_with_cohd_frequency(g, normalized=normalize)  # TODO: check if normalized on returns better results

		# sort the phenotypes by frequency
		names = nx.get_node_attributes(g, 'names')
		labels = nx.get_node_attributes(g, 'labels')
		descriptions = nx.get_node_attributes(g, 'description')

		# get the node corresponding to the disease
		disease_node = None
		for node in names.keys():
			if names[node] == disease_id:
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
				node_freq_tuples.append((node, freq))

		# sort the node freqs
		node_freq_tuples_sorted = sorted(node_freq_tuples, key=lambda x: x[1], reverse=rev)

		# reduce to top n
		node_freq_tuples_sorted_top_n = node_freq_tuples_sorted
		if len(node_freq_tuples_sorted_top_n) > num_show:
			node_freq_tuples_sorted_top_n = node_freq_tuples_sorted_top_n[0:num_show]

		# good nodes
		good_nodes = set([tup[0] for tup in node_freq_tuples_sorted_top_n])
		good_nodes.add(disease_node)

		# all nodes
		all_nodes = set([tup[0] for tup in node_freq_tuples_sorted])

		# remove the other nodes from the graph
		g.remove_nodes_from(all_nodes-good_nodes)

		# return the results
		if not use_json:
			if rev:
				to_print = "The most common phenotypes "
			else:
				to_print = "The least common phenotypes "
			to_print += "associated with %s, according to the Columbia Open Health Data, are:\n" % disease_description
			for node, freq in node_freq_tuples_sorted_top_n:
				to_print += "phenotype: %s\t frequency %f \n" % (descriptions[node], freq)
			print(to_print)
		else:
			for node, freq in node_freq_tuples_sorted_top_n:
				to_print = "According to the Columbia Open Health Data, %s has the phenotype %s with frequency %f." % (disease_description, descriptions[node], freq)
				sub_g = nx.subgraph(g, [disease_node, node])
				# add it to the response
				response.add_subgraph(sub_g.nodes(data=True), sub_g.edges(data=True), to_print, freq)
			response.print()

	@staticmethod
	def describe():
		output = "Answers questions of the form: 'What are the most/least common symptoms of X?' where X is a disease." + "\n"
		# TODO: subsample disease nodes
		return output


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the type 'What are the most common symptoms of disease X?",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-d', '--disease', type=str, help="Disease ID/name", default="DOID:8398")
	parser.add_argument('-r', '--rare', action='store_true', help="Include if you want the least common diseases, don't include if you want the most common")
	parser.add_argument('-n', '--normalize', action='store_true', help="Use if you want to normalize so all probabilities sum to 1 (instead of using the raw numbers from COHD).")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
	parser.add_argument('--num_show', type=int, help='Maximum number of results to return', default=20)

	# Parse and check args
	args = parser.parse_args()
	disease = args.disease
	is_rare = args.rare
	normalize = args.normalize
	use_json = args.json
	describe_flag = args.describe
	num_show = args.num_show


	# Initialize the question class
	Q = CommonSymptomsSolution()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		Q.answer(disease, use_json=use_json, num_show=num_show, rev=not(is_rare), normalize=normalize)


if __name__ == "__main__":
	main()
