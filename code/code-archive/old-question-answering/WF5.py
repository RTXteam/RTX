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
import CustomExceptions

# eg: what proteins does drug X target? One hop question
class WF5:

	def __init__(self):
		None

	def answer(self, source_name, target_label, relationship_list, use_json=False, directed=False):
		"""
		Find paths of the type:
		(n:chemical_substance{id:"CHEMBL.COMPOUND:CHEMBL714"})-[:physically_interacts_with]-(:protein)-[:has_phenotype]-(m:phenotypic_feature)
		"""
		# Get label/kind of node the source is
		source_label = RU.get_node_property(source_name, "label")

		# Get the subgraph (all targets along relationship)
		has_intermediate_node = False
		try:
			g = RU.return_subgraph_paths_of_type(source_name, source_label, None, target_label, relationship_list, directed=directed)
		except CustomExceptions.EmptyCypherError:
			error_message = "No path between %s and %s via relationships %s" % (source_name, target_label, ','.join(relationship_list))
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


		# Format the results.
		if not use_json:
			results_list = list()
			for target_number in target_numbers:
				data = g.node[target_number]
				results_list.append(
					{'type': list(set(data['labels'])-{'Base'}).pop(),
					 'name': data['properties']['name'],
					 'desc': data['properties']['name'],
					 'prob': 1})  # All these are known to be true
			return results_list
		else:  # You want the standardized API output format
			response = FormatOutput.FormatResponse(3)  # it's a Q3 question
			response.response.table_column_names = ["source name", "source ID", "target name", "target ID"]
			source_description = g.node[source_node_number]['properties']['name']
			for target_number in target_numbers:
				target_description = g.node[target_number]['properties']['name']
				if not has_intermediate_node:
					subgraph = g.subgraph([source_node_number, target_number])
				else:
					subgraph = g.subgraph([source_node_number, intermediate_node, target_number])
				res = response.add_subgraph(subgraph.nodes(data=True), subgraph.edges(data=True),
									"%s and %s are connected by the relationships %s" % (
									source_description, target_description,	','.join(relationship_list)), 1, return_result=True)
				res.essence = "%s" % target_description  # populate with essence of question result
				row_data = []  # initialize the row data
				row_data.append("%s" % source_description)
				row_data.append("%s" % g.node[source_node_number]['properties']['id'])
				row_data.append("%s" % target_description)
				row_data.append("%s" % g.node[target_number]['properties']['id'])
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



def main():
	parser = argparse.ArgumentParser(description="Answers questions of the type 'What proteins does X target?'.",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-s', '--source_name', type=str, help="Source node name.", default="CHEMBL.COMPOUND:CHEMBL714")
	parser.add_argument('-t', '--target_label', type=str, help="Target node label", default="phenotypic_feature")
	parser.add_argument('-r', '--rel_type_list', type=str, help="Relationship type.", default="physically_interacts_with,has_phenotype")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('-d', '--describe', action='store_true', help="Describe what kinds of questions this answers.", default=False)
	parser.add_argument('--directed', action='store_true', help="Treat the relationship as directed", default=False)

	# Parse and check args
	args = parser.parse_args()
	source_name = args.source_name
	target_label = args.target_label
	relationship_list = args.rel_type_list.split(',')
	use_json = args.json
	describe_flag = args.describe
	directed = args.directed

	# Initialize the question class
	Q = WF5()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		res = Q.answer(source_name, target_label, relationship_list, use_json, directed=directed)
		if use_json:
			res.print()
		else:
			#print(res)
			for item in res:
				print(item['desc'])


if __name__ == "__main__":
	main()
