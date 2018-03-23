import os
import sys
import argparse
# PyCharm doesn't play well with relative imports + python console + terminal
try:
	from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import ReasoningUtilities as RU

# eg: what proteins does drug X target? One hop question
class Q4:

	def __init__(self):
		None

	def answer(self, source_name, target_label, relationship_type):
		"""
		Answer a question of the type "What proteins does drug X target" but is general:
		 what <node X type> does <node Y grounded> <relatioship Z> that can be answered in one hop in the KG (increasing the step size if necessary).
		:param query_terms: a triple consisting of a source node name (KG neo4j node name, the target label (KG neo4j
		"node label") and the relationship type (KG neo4j "Relationship type")
		:param source_name: KG neo4j node name (eg "carbetocin")
		:param target_label: KG node label (eg. "uniprot_protein")
		:param relationship_type: KG relationship type (eg. "targets")
		:return: list of dictionaries containing the nodes that are one hop (along relationship type) that connect source to target.
		"""
		# Get label/kind of node the source is
		source_label = RU.get_node_property(source_name, "label")
		# get the actual targets
		targets = RU.get_one_hop_target(source_label, source_name, target_label, relationship_type)
		# Look 2 steps beyone if we didn't get any targets
		if targets == []:
			for max_path_len in range(2, 5):
				print(max_path_len)
				targets = RU.get_node_names_of_type_connected_to_target(source_label, source_name, target_label, max_path_len=max_path_len, direction="u")
				if targets:
					break

		# Format the results. TODO: change this to a call to Eric's output formatter when he's written that
		results_list = list()
		for target in targets:
			results_list.append(
				{'type': 'node',
				 'name': target,
				 'desc': RU.get_node_property(target, "description", node_label=target_label),
				 'prob': 1})  # All these are known to be true
		return results_list

	def describe(self):
		output = "Answers questions of the form: 'What proteins does tranilast target?' and 'What genes are affected by " \
				 "Fanconi anemia?'" + "\n"
		output += "You can ask: 'What X does Y Z?' where X is one of the following: \n"
		for label in RU.get_node_labels():
			output = output + label + "\n"
		output += "\n The term Y is any of the nodes that are in our graph (currently " + str(RU.count_nodes()) + " nodes in total). \n"
		output += "\n The term Z is any relationship of the following kind: \n"
		for rel in RU.get_relationship_types():
			rel_split = rel.split("_")
			for term in rel_split:
				output += term + " "
			output += "\n"
		output += "Assumes that Z directly connects X and Y."
		return output


# Tests
def testQ4_answer():
	Q = Q4()
	res = Q.answer("carbetocin", "uniprot_protein", "targets")
	assert res == [{'desc': 'OXTR', 'name': 'P30559', 'type': 'node','prob': 1}]
	res = Q.answer("OMIM:263200", "uniprot_protein", "disease_affects")
	known_res = [{'desc': 'PKHD1', 'name': 'P08F94', 'type': 'node','prob': 1}, {'desc': 'DZIP1L', 'name': 'Q8IYY4', 'type': 'node','prob': 1}]
	for item in res:
		assert item in known_res
	for item in known_res:
		assert item in res
	res = Q.answer("OMIM:263200", "ncbigene_microrna", "gene_assoc_with")
	assert res == [{'desc': 'MIR1225', 'name': 'NCBIGene:100188847', 'type': 'node', 'prob': 1}]


def test_Q4_describe():
	Q = Q4()
	res = Q.describe()


def test_suite():
	testQ4_answer()
	test_Q4_describe()


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the type 'What proteins does X target?'.",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-s', '--source_name', type=str, help="Source node name.", default="carbetocin")
	parser.add_argument('-t', '--target_label', type=str, help="Target node label", default="uniprot_protein")
	parser.add_argument('-r', '--rel_type', type=str, help="Relationship type.", default="targets")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('-d', '--describe', action='store_true', help="Describe what kinds of questions this answers.", default=False)

	# Parse and check args
	args = parser.parse_args()
	source_name = args.source_name
	target_label = args.target_label
	relationship_type = args.rel_type
	use_json = args.json
	describe_flag = args.describe

	# Initialize the question class
	Q = Q4()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		res = Q.answer(source_name, target_label, relationship_type)
		print(res)


if __name__ == "__main__":
	main()
