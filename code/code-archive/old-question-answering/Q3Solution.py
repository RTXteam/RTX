import sys
def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
import os
import argparse
# PyCharm doesn't play well with relative imports + python console + terminal
try:
	from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import ReasoningUtilities as RU

#### Import some Translator API classes
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge

import FormatOutput
import CustomExceptions

# eg: what proteins does drug X target? One hop question
class Q3:

	def __init__(self):
		None

	def answer(self, source_name, target_label, relationship_type, use_json=False, directed=False):
		"""
		Answer a question of the type "What proteins does drug X target" but is general:
		 what <node X type> does <node Y grounded> <relatioship Z> that can be answered in one hop in the KG (increasing the step size if necessary).
		:param query_terms: a triple consisting of a source node name (KG neo4j node name, the target label (KG neo4j
		"node label") and the relationship type (KG neo4j "Relationship type")
		:param source_name: KG neo4j node name (eg "carbetocin")
		:param target_label: KG node label (eg. "protein")
		:param relationship_type: KG relationship type (eg. "physically_interacts_with")
		:param use_json: If the answer should be in Eric's Json standardized API output format
		:return: list of dictionaries containing the nodes that are one hop (along relationship type) that connect source to target.
		"""
		# Get label/kind of node the source is
		source_label = RU.get_node_property(source_name, "label")

		# Get the subgraph (all targets along relationship)
		has_intermediate_node = False
		try:
			g = RU.return_subgraph_paths_of_type(source_name, source_label, None, target_label, [relationship_type], directed=directed)
		except CustomExceptions.EmptyCypherError:
			try:
				has_intermediate_node = True
				g = RU.return_subgraph_paths_of_type(source_name, source_label, None, target_label, ['subclass_of', relationship_type], directed=directed)
			except CustomExceptions.EmptyCypherError:
				error_message = "No path between %s and %s via relationship %s" % (source_name, target_label, relationship_type)
				error_code = "NoPathsFound"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				return response

		# extract the source_node_number
		for node, data in g.nodes(data=True):
			if data['properties']['id'] == source_name:
				source_node_number = node
				break

		# Get all the target numbers
		target_numbers = []
		for node, data in g.nodes(data=True):
			if data['properties']['id'] != source_name:
				target_numbers.append(node)

		# if there's an intermediate node, get the name
		if has_intermediate_node:
			neighbors = list(g.neighbors(source_node_number))
			if len(neighbors) > 1:
				error_message = "More than one intermediate node"
				error_code = "AmbiguousPath"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				return response
			else:
				intermediate_node = neighbors.pop()

		#### If use_json not specified, then return results as a fairly plain list
		if not use_json:
			results_list = list()
			for target_number in target_numbers:
				data = g.nodes[target_number]
				results_list.append(
					{'type': list(set(data['labels'])-{'Base'}).pop(),
					 'name': data['properties']['name'],
					 'desc': data['properties']['name'],
					 'prob': 1})  # All these are known to be true
			return results_list

		#### Else if use_json requested, return the results in the Translator standard API JSON format
		else:
			response = FormatOutput.FormatResponse(3)  # it's a Q3 question
			response.message.table_column_names = ["source name", "source ID", "target name", "target ID"]
			source_description = g.nodes[source_node_number]['properties']['name']

			#### Create the QueryGraph for this type of question
			query_graph = QueryGraph()
			source_node = QNode()
			source_node.id = "n00"
			source_node.curie = g.nodes[source_node_number]['properties']['id']
			source_node.type = g.nodes[source_node_number]['properties']['category']
			target_node = QNode()
			target_node.id = "n01"
			target_node.type = target_label
			query_graph.nodes = [ source_node,target_node ]
			edge1 = QEdge()
			edge1.id = "e00"
			edge1.source_id = "n00"
			edge1.target_id = "n01"
			edge1.type = relationship_type
			query_graph.edges = [ edge1 ]
			response.message.query_graph = query_graph

			#### Create a mapping dict with the source curie and the target type. This dict is used for reverse lookups by type
			#### for mapping to the QueryGraph.
			response._type_map = dict()
			response._type_map[source_node.curie] = source_node.id
			response._type_map[target_node.type] = target_node.id
			response._type_map[edge1.type] = edge1.id

			#### Loop over all the returned targets and put them into the response structure
			for target_number in target_numbers:
				target_description = g.nodes[target_number]['properties']['name']
				if not has_intermediate_node:
					subgraph = g.subgraph([source_node_number, target_number])
				else:
					subgraph = g.subgraph([source_node_number, intermediate_node, target_number])
				res = response.add_subgraph(subgraph.nodes(data=True), subgraph.edges(data=True),
									"%s and %s are connected by the relationship %s" % (
									source_description, target_description,	relationship_type), 1, return_result=True)
				res.essence = "%s" % target_description  # populate with essence of question result
				res.essence_type = g.nodes[target_number]['properties']['category']  # populate with the type of the essence of question result
				row_data = []  # initialize the row data
				row_data.append("%s" % source_description)
				row_data.append("%s" % g.nodes[source_node_number]['properties']['id'])
				row_data.append("%s" % target_description)
				row_data.append("%s" % g.nodes[target_number]['properties']['id'])
				res.row_data = row_data
			return response


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
def testQ3_answer():
	Q = Q3()
	res = Q.answer("carbetocin", "protein", "physically_interacts_with")
	assert res == [{'desc': 'OXTR', 'name': 'P30559', 'type': 'node','prob': 1}]
	res = Q.answer("OMIM:263200", "protein", "affects")
	known_res = [{'desc': 'PKHD1', 'name': 'P08F94', 'type': 'node','prob': 1}, {'desc': 'DZIP1L', 'name': 'Q8IYY4', 'type': 'node','prob': 1}]
	for item in res:
		assert item in known_res
	for item in known_res:
		assert item in res
	res = Q.answer("OMIM:263200", "microRNA", "gene_associated_with_condition")
	assert res == [{'desc': 'MIR1225', 'name': 'NCBIGene:100188847', 'type': 'node', 'prob': 1}]


def test_Q3_describe():
	Q = Q3()
	res = Q.describe()


def test_suite():
	testQ3_answer()
	test_Q3_describe()


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the type 'What proteins does X target?'.",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-s', '--source_name', type=str, help="Source node name.", default="CHEMBL.COMPOUND:CHEMBL521")
	parser.add_argument('-t', '--target_label', type=str, help="Target node label", default="protein")
	parser.add_argument('-r', '--rel_type', type=str, help="Relationship type.", default="physically_interacts_with")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('-d', '--describe', action='store_true', help="Describe what kinds of questions this answers.", default=False)
	parser.add_argument('--directed', action='store_true', help="Treat the relationship as directed", default=False)

	# Parse and check args
	args = parser.parse_args()
	source_name = args.source_name
	target_label = args.target_label
	relationship_type = args.rel_type
	use_json = args.json
	describe_flag = args.describe
	directed = args.directed

	# Initialize the question class
	Q = Q3()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		res = Q.answer(source_name, target_label, relationship_type, use_json, directed=directed)
		if use_json:
			res.print()
		else:
			print(res)


if __name__ == "__main__":
	main()
