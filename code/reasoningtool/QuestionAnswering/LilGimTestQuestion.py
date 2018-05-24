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
import QueryLilGIM
import CustomExceptions
import ast

class LilGim:

	def __init__(self):
		None

	@staticmethod
	def answer(tissue_id, protein_list, use_json=False, num_show=20, rev=True):

		# Initialize the response class
		response = FormatOutput.FormatResponse(6)

		# Make sure everything exists in the graph
		if not RU.node_exists_with_property(tissue_id, "id"):
			tissue_id = RU.get_node_property(tissue_id, "id", node_label="anatomical_entity")

		for i in range(len(protein_list)):
			id = protein_list[i]
			if not RU.node_exists_with_property(id, "id"):
				protein_list[i] = RU.get_node_property(id, "id", node_label="protein")

		# Initialize the QueryLilGim class
		q = QueryLilGIM.QueryLilGIM()

		# get the description
		tissue_description = RU.get_node_property(tissue_id, 'name', node_label="anatomical_entity")

		# Get the correlated proteins
		try:
			correlated_proteins_dict = q.query_neighbor_genes_for_gene_set_in_a_given_anatomy(tissue_id, tuple(protein_list))
		except:
			error_message = "Lil'GIM is experiencing a problem."
			error_code = "LilGIMerror"
			response.add_error_message(error_code, error_message)
			response.print()
			return 1

		# as a list of tuples
		correlated_proteins_tupes = []
		for k, v in correlated_proteins_dict.items():
			correlated_proteins_tupes.append((k, v))

		# sort by freq
		correlated_proteins_tupes_sorted = sorted(correlated_proteins_tupes, key=lambda x: x[1], reverse=rev)
		correlated_proteins_tupes_sorted = correlated_proteins_tupes_sorted[0:num_show]


		# return the results
		if not use_json:
			try:
				protein_descriptions = RU.get_node_property(protein_list[0], "name", node_label="protein", name_type="id")
			except:
				protein_descriptions = protein_list[0]
			for id in protein_list[1:-1]:
				protein_descriptions += ", "
				try:
					protein_descriptions += RU.get_node_property(id, "name", node_label="protein", name_type="id")
				except:
					protein_descriptions += id
			if len(protein_list) > 1:
				try:
					protein_descriptions += ", and %s" % RU.get_node_property(protein_list[-1], "name", node_label="protein", name_type="id")
				except:
					protein_descriptions += ", and %s" % protein_list[-1]
			if rev:
				to_print = "In the tissue: %s, the proteins that correlate most with %s" % (tissue_description, protein_descriptions)
			else:
				to_print = "In the tissue: %s, the proteins that correlate least with %s" % (tissue_description, protein_descriptions)
			to_print += " according to Lil'GIM, are:\n"
			for id, val in correlated_proteins_tupes_sorted:
				try:
					to_print += "protein: %s\t correlation %f\n" % (RU.get_node_property(id, "name", node_label="protein", name_type="id"), val)
				except:
					to_print += "protein: %s\t correlation %f\n" % (id, val)
			print(to_print)
		else:
			#  otherwise, you want a JSON output
			# TODO: blocking on issue #201
			full_g = RU.get_graph_from_nodes([id for id, val in correlated_proteins_tupes], node_property_label="id")
			id2node = dict()
			for node in full_g.nodes(data=True):
				id2node[node['properties']['id']] = node
			for id, corr in correlated_proteins_tupes_sorted:
				to_print = "In the tissue: %s, the protein %s has correlation %f with the given list of proteins." %(tissue_description, RU.get_node_property(id, "name", node_label="protein"), corr)
				response.add_subgraph([id2node[id]], [], to_print, corr)
			response.print()

	@staticmethod
	def describe():
		output = "Answers questions of the form: 'What proteins correlate with [$protein1, $protein2,...,$proteinK?] in blood?'" + "\n"
		# TODO: subsample disease nodes
		return output


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the form: 'What proteins correlate with [$protein1, $protein2,...,$proteinK?] in blood?'",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-t', '--tissue', type=str, help="Tissue id/name", default="UBERON:0002384")
	parser.add_argument('-r', '--reverse', action='store_true', help="Include flag if you want the least correlations.")
	parser.add_argument('-p', '--proteins', type=str, help="List of proteins.", default="['UniProtKB:P12004']")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
	parser.add_argument('--num_show', type=int, help='Maximum number of results to return', default=20)

	# Parse and check args
	args = parser.parse_args()
	tissue_id = args.tissue
	is_reverse = args.reverse
	proteins = args.proteins
	use_json = args.json
	describe_flag = args.describe
	num_show = args.num_show

	# Convert the string to an actual list
	print(proteins)
	#proteins = proteins.replace(",", "','").replace("[", "['").replace("]", "']")
	protein_list = ast.literal_eval(proteins)

	# Initialize the question class
	Q = LilGim()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		Q.answer(tissue_id, protein_list, use_json=use_json, num_show=num_show, rev=not(is_reverse))

if __name__ == "__main__":
	main()
