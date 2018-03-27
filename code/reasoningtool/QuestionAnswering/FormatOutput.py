# This script will populate Eric's standardized output object model with a given networkx neo4j instance of nodes/edges

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")

from swagger_server.models.response import Response
from swagger_server.models.result import Result
from swagger_server.models.result_graph import ResultGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
import datetime
import math

import ReasoningUtilities as RU

class FormatResponse:
	"""
	Class to format a neo4j networkx subgraph into the standardized output
	"""
	def __init__(self, question_number):
		self._question_number = question_number
		self._now = datetime.datetime.now()
		self._result_list = []
		self._num_results = 0
		# Create the response object and fill it with attributes about the response
		self.response = Response()
		self.response.context = "http://translator.ncats.io"
		self.response.id = "http://rtx.ncats.io/api/v1/response/1234"  # TODO: Eric to figure out how to populate
		self.response.type = "medical_translator_query_result"
		self.response.tool_version = "RTX 0.4"
		self.response.schema_version = "0.5"
		self.response.datetime = self._now.strftime("%Y-%m-%d %H:%M:%S")
		self.response.original_question_text = "ERIC FILL THIS IN FROM QuestionTranslator.py"  # TODO
		self.response.restated_question_text = "ERIC FILL THIS IN FROM QuestionTranslator.py"  # TODO
		self.response.result_code = "OK"  # TODO: from QuestionTranslator.py
		self.response.message = "%s result found" % self._num_results  # TODO: figure out how to populate this

	def __str__(self):
		return repr(self.response)

	def add_subgraph(self, nodes, edges, plain_text, confidence):
		"""
		Populate the object model using networkx neo4j subgraph
		:param nodes: nodes in the subgraph (g.nodes(data=True))
		:param edges: edges in the subgraph (g.edges(data=True))
		:return: none
		"""

		# Get the relevant info from the nodes and edges
		node_keys = []
		node_descriptions = dict()
		node_names = dict()
		node_labels = dict()
		node_uuids = dict()
		for u, data in nodes:
			node_keys.append(u)
			node_descriptions[u] = data['description']
			node_names[u] = data['names']
			node_labels[u] = list(set(data['labels']).difference({'Base'}))[0]
			node_uuids[u] = data['properties']['UUID']

		edge_keys = []
		edge_types = dict()
		edge_source_db = dict()
		edge_source_uuid = dict()
		edge_target_uuid = dict()
		for u, v, data in edges:
			edge_keys.append((u, v))
			edge_types[(u, v)] = data['type']
			edge_source_db[(u, v)] = data['properties']['sourcedb']
			edge_source_uuid[(u, v)] = data['properties']['source_node_uuid']
			edge_target_uuid[(u, v)] = data['properties']['target_node_uuid']

		# For each node, populate the relevant information
		node_objects = []
		node_uuid_to_node_object = dict()
		for node_key in node_keys:
			node = Node()
			node.id = node_uuids[node_key]
			node.type = node_labels[node_key]
			node.name = node_descriptions[node_key]
			node.accession = node_names[node_key]
			node.description = "None (yet)"  # TODO: where to get the common name descriptions? UMLS perhaps?
			node_objects.append(node)
			node_uuid_to_node_object[node_uuids[node_key]] = node

		# for each edge, create an edge between them
		edge_objects = []
		for u, v in edge_keys:
			edge = Edge()
			edge.type = edge_types[(u, v)]
			edge.source_id = node_uuid_to_node_object[edge_source_uuid[(u, v)]].id
			edge.target_id = node_uuid_to_node_object[edge_target_uuid[(u, v)]].id
			edge_objects.append(edge)

		# Create the result (potential answer)
		result1 = Result()
		result1.id = "http://rtx.ncats.io/api/v1/response/1234/result/2345"  # TODO: eric to change this
		result1.text = plain_text
		result1.confidence = confidence

		# Create a ResultGraph object and put the list of nodes and edges into it
		result_graph = ResultGraph()
		result_graph.node_list = node_objects
		result_graph.edge_list = edge_objects

		# Put the ResultGraph into the first result (potential answer)
		result1.result_graph = result_graph

		# Put the first result (potential answer) into the response
		self._result_list.append(result1)
		self.response.result_list = self._result_list
		# Increment the number of results
		self._num_results += 1
		self.response.message = "%s result found" % self._num_results

if __name__ == '__main__':
	test = FormatResponse(2)
	g = RU.return_subgraph_through_node_labels("zopiclone", 'pharos_drug', 'DOID:0050433', 'disont_disease',
											   ['uniprot_protein', 'anatont_anatomy', 'phenont_phenotype'],
											   directed=False)
	test.add_subgraph(g.nodes(data=True), g.edges(data=True), "This is a test", 0.95)
	test.add_subgraph(g.nodes(data=True), g.edges(data=True), "This is a SECOND test", 0.00)
	print(test)

