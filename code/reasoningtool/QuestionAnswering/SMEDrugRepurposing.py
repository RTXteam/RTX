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

import CustomExceptions


class SMEDrugRepurposing:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=20):

		# Initialize the response class
		response = FormatOutput.FormatResponse(6)

		# get the description of the disease
		disease_description = RU.get_node_property(disease_id, 'name')

		# What are the defining symptoms of the disease?
		# get subgraph of all all the symptom nodes connecting to the disease
		try:
			g = RU.return_subgraph_paths_of_type(disease_id, "disease", None, "phenotypic_feature", ["has_phenotype"],
												 directed=False)
		except CustomExceptions.EmptyCypherError:
			error_code = "EmptyGraph"
			error_message = "Sorry, but there are no phenotypes associated to %s" % disease_description
			response.add_error_message(error_code, error_message)
			response.print()
			return 1

		# decorate with cohd data
		RU.weight_graph_with_cohd_frequency(g, normalized=True)  # TODO: check if normalized on returns better results

		# sort the phenotypes by frequency
		names = nx.get_node_attributes(g, 'id')
		labels = nx.get_node_attributes(g, 'labels')

		# get the node corresponding to the disease
		disease_node = None
		for node in names.keys():
			if names[node] == disease_id:
				disease_node = node

		# get all the nodes and the frequencies in one place
		symptom_node_freqs = []
		for node in names.keys():
			if "phenotypic_feature" == list(set(labels[node]) - {"Base"}).pop():
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
				symptom_node_freqs.append((node, freq))



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
