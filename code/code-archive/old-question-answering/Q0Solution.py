#!/usr/bin/python3
from __future__ import print_function
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

import FormatOutput
import CustomExceptions

#### Import the Translator API classes
from swagger_server.models.message import Message
from swagger_server.models.result import Result
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.node_attribute import NodeAttribute
from swagger_server.models.node_binding import NodeBinding
from swagger_server.models.edge_binding import EdgeBinding

from KGNodeIndex import KGNodeIndex


#### Q0: "What is X?". Query the knowledge graph to get information about a node
class Q0:

	def __init__(self):
		None

	def answer(self, entity, use_json=False):
		"""
		Answer a question of the type "What is X" but is general:
		:param entity: KG neo4j node name (eg "carbetocin")
		:param use_json: If the answer should be in Translator standardized API output format
		:return: a description and type of the node
		"""

		#### See if this entity is in the KG via the index
		eprint("Looking up '%s' in KgNodeIndex" % entity)
		kgNodeIndex = KGNodeIndex()
		curies = kgNodeIndex.get_curies(entity)

		#### If not in the KG, then return no information
		if not curies:
			if not use_json:
				return None
			else:
				error_code = "TermNotFound"
				error_message = "This concept is not in our knowledge graph"
				response = FormatOutput.FormatResponse(0)
				response.add_error_message(error_code, error_message)
				return response.message

		# Get label/kind of node the source is
		eprint("Getting properties for '%s'" % curies[0])
		properties = RU.get_node_properties(curies[0])
		eprint("Properties are:")
		eprint(properties)

		#### By default, return the results just as a plain simple list of data structures
		if not use_json:
			return properties

		#### Or, if requested, format the output as the standardized API output format
		else:
			#### Create a stub Message object
			response = FormatOutput.FormatResponse(0)
			response.message.table_column_names = [ "id", "type", "name", "description", "uri" ]
			response.message.code_description = None

			#### Create a Node object and fill it
			node1 = Node()
			node1.id = properties["id"]
			node1.uri = properties["uri"]
			node1.type = [ properties["category"] ]
			node1.name = properties["name"]
			node1.description = properties["description"]

			#### Create the first result (potential answer)
			result1 = Result()
			result1.id = "http://arax.ncats.io/api/v1/result/0000"
			result1.description = "The term %s is in our knowledge graph and is defined as %s" % ( properties["name"],properties["description"] )
			result1.confidence = 1.0
			result1.essence = properties["name"]
			result1.essence_type = properties["category"]
			node_types = ",".join(node1.type)
			result1.row_data = [ node1.id, node_types, node1.name, node1.description, node1.uri ]

			#### Create a KnowledgeGraph object and put the list of nodes and edges into it
			result_graph = KnowledgeGraph()
			result_graph.nodes = [ node1 ]
			result_graph.edges = []

			#### Put the ResultGraph into the first result (potential answer)
			result1.result_graph = result_graph

			#### Put the first result (potential answer) into the message
			results = [ result1 ]
			response.message.results = results

			#### Also put the union of all result_graph components into the top Message KnowledgeGraph
			#### Normally the knowledge_graph will be much more complex than this, but take a shortcut for this single-node result
			response.message.knowledge_graph = result_graph

			#### Also manufacture a query_graph post hoc
			qnode1 = QNode()
			qnode1.id = "n00"
			qnode1.curie = properties["id"]
			qnode1.type = None
			query_graph = QueryGraph()
			query_graph.nodes = [ qnode1 ]
			query_graph.edges = []
			response.message.query_graph = query_graph

			#### Create the corresponding knowledge_map
			node_binding = NodeBinding(qg_id="n00", kg_id=properties["id"])
			result1.node_bindings = [ node_binding ]
			result1.edge_bindings = []

			#eprint(response.message)
			return response.message

	def describe(self):
		output = "Answers questions of the form: 'What is X?', where X is a node in the knowledge graph\n"
		return output


# Tests
def testQ0_answer():
	q = Q0()
	result = q.answer("carbetocin")
	assert result["id"] == "KEGG:C18365" and result["category"] == "metabolite"
	result = q.answer("DOID:9281")
	assert result["id"] == "DOID:9281" and result["category"] == "disease"
	result = q.answer("lovastatin")
	assert result["id"] == "CHEMBL.COMPOUND:CHEMBL503" and result["category"] == "chemical_substance"
	result = q.answer("blobfoodle")
	assert result == None


def test_suite():
	q = Q0()
	q.describe()
	testQ0_answer()
	return True


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the type 'What is X?'.",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-n', '--name', type=str, help="Entity name", default="malaria")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in Translator standard format (to stdout)', default=False)
	parser.add_argument('-d', '--describe', action='store_true', help="Describe what kinds of questions this answers.", default=False)
	parser.add_argument('-t', '--test', action='store_true', help="Run tests", default=False)

	# Parse and check args
	args = parser.parse_args()
	name = args.name
	use_json = args.json

	# Initialize the question class
	q = Q0()

	if args.describe:
		result = q.describe()
		print(result)
	if args.test:
		result = test_suite()
		print(result)
	else:
		result = q.answer(name, use_json=use_json)
		if use_json:
			result.print()
		else:
			print(result)


if __name__ == "__main__":
	main()
