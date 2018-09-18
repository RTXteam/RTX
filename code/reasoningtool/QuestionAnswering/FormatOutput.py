# This script will populate Eric's standardized output object model with a given networkx neo4j instance of nodes/edges

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
RTXConfiguration = RTXConfiguration()

from swagger_server.models.response import Response
from swagger_server.models.result import Result
from swagger_server.models.result_graph import ResultGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
import datetime
import math
import json
import ast

import ReasoningUtilities as RU

class FormatResponse:
	"""
	Class to format a neo4j networkx subgraph into the standardized output
	"""
	def __init__(self, question_number):
		"""
		Initialize the class
		:param question_number: which question number this is
		"""
		self._question_number = question_number
		self._now = datetime.datetime.now()
		self._result_list = []
		self._num_results = 0
		# Create the response object and fill it with attributes about the response
		self.response = Response()
		self.response.type = "medical_translator_query_result"
		self.response.tool_version = RTXConfiguration.version
		self.response.schema_version = "0.5"
		self.response.response_code = "OK"
		if self._num_results == 1:
			self.response.message = "%s result found" % self._num_results
		else:
			self.response.message = "%s results found" % self._num_results


	def __str__(self):
		return repr(self.response)

	def print(self):
		print(json.dumps(ast.literal_eval(repr(self.response)), sort_keys=True, indent=2))

	def add_error_message(self, code, message):
		"""
		Add an error message to the response
		:param code: error code
		:param message: error message
		:return: None (modifies response)
		"""
		response = self.response
		response.response_code = code
		response.message = message

	def add_text(self, plain_text, confidence=1):
		result1 = Result()
		result1.text = plain_text
		result1.confidence = confidence
		self._result_list.append(result1)
		self.response.result_list = self._result_list
		# Increment the number of results
		self._num_results += 1
		if self._num_results == 1:
			self.response.message = "%s result found" % self._num_results
		else:
			self.response.message = "%s results found" % self._num_results

	def add_subgraph(self, nodes, edges, plain_text, confidence, return_result=False):
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
		node_accessions = dict()
		node_iris = dict()
		node_uuids2iri = dict()
		node_curies = dict()
		node_uuids2curie = dict()
		for u, data in nodes:
			node_keys.append(u)
			if 'description' in data['properties']:
				node_descriptions[u] = data['properties']['description']
			else:
				node_descriptions[u] = "None"
			node_names[u] = data['properties']['name']
			node_labels[u] = list(set(data['labels']).difference({'Base'}))[0]
			node_uuids[u] = data['properties']['UUID']
			node_accessions[u] = data['properties']['accession']
			node_iris[u] = data['properties']['uri']
			node_uuids2iri[data['properties']['UUID']] = data['properties']['uri']
			curie_id = data['properties']['id']
			if curie_id.split(':')[0].upper() == "CHEMBL":
				curie_id = "CHEMBL:CHEMBL" + curie_id.split(':')[1]
			node_uuids2curie[data['properties']['UUID']] = curie_id
			node_curies[u] = curie_id  # These are the actual CURIE IDS eg UBERON:00000941 (uri is the web address)

		edge_keys = []
		edge_types = dict()
		edge_source_db = dict()
		edge_source_iri = dict()
		edge_target_iri = dict()
		edge_source_curie = dict()
		edge_target_curie = dict()
		for u, v, data in edges:
			edge_keys.append((u, v))
			edge_types[(u, v)] = data['type']
			edge_source_db[(u, v)] = data['properties']['provided_by']
			edge_source_iri[(u, v)] = node_uuids2iri[data['properties']['source_node_uuid']]
			edge_target_iri[(u, v)] = node_uuids2iri[data['properties']['target_node_uuid']]
			edge_source_curie[(u,v)] = node_uuids2curie[data['properties']['source_node_uuid']]
			edge_target_curie[(u, v)] = node_uuids2curie[data['properties']['target_node_uuid']]

		# For each node, populate the relevant information
		node_objects = []
		node_iris_to_node_object = dict()
		for node_key in node_keys:
			node = Node()
			node.id = node_curies[node_key]
			node.type = node_labels[node_key]
			node.name = node_names[node_key]
			node.uri = node_iris[node_key]
			node.accession = node_accessions[node_key]
			node.description = node_descriptions[node_key]
			node_objects.append(node)
			node_iris_to_node_object[node_iris[node_key]] = node

		# for each edge, create an edge between them
		edge_objects = []
		for u, v in edge_keys:
			edge = Edge()
			edge.type = edge_types[(u, v)]
			edge.source_id = node_iris_to_node_object[edge_source_iri[(u, v)]].id
			edge.target_id = node_iris_to_node_object[edge_target_iri[(u, v)]].id
			#edge.origin_list = []
			#edge.origin_list.append(edge_source_db[(u, v)])  # TODO: check with eric if this really should be a list and if it should contain the source DB('s)
			edge_objects.append(edge)
			#edge.attribute_list
			#edge.confidence
			#edge.evidence_type
			edge.is_defined_by = "RTX"
			#edge.provided_by = node_iris_to_node_object[edge_source_iri[(u, v)]].uri
			edge.provided_by = edge_source_db[(u, v)]
			#edge.publications
			#edge.qualifiers
			#edge.relation
			#edge.source_id
			#edge.target_id
			#edge.type

		# Create the result (potential answer)
		result1 = Result()
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
		if self._num_results == 1:
			self.response.message = "%s result found" % self._num_results
		else:
			self.response.message = "%s results found" % self._num_results
		if return_result:
			return result1
		else:
			pass

	def add_neighborhood_graph(self, nodes, edges, confidence=None):
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
		node_accessions = dict()
		node_iris = dict()
		node_uuids2iri = dict()
		node_curies = dict()
		node_uuids2curie = dict()
		for u, data in nodes:
			node_keys.append(u)
			node_descriptions[u] = data['properties']['description']
			node_names[u] = data['properties']['name']
			node_labels[u] = list(set(data['labels']).difference({'Base'}))[0]
			node_uuids[u] = data['properties']['UUID']
			node_accessions[u] = data['properties']['accession']
			node_iris[u] = data['properties']['uri']
			node_uuids2iri[data['properties']['UUID']] = data['properties']['uri']
			curie_id = data['properties']['id']
			if curie_id.split(':')[0].upper() == "CHEMBL":
				curie_id = "CHEMBL:CHEMBL" + curie_id.split(':')[1]
			node_uuids2curie[data['properties']['UUID']] = curie_id
			node_curies[u] = curie_id  # These are the actual CURIE IDS eg UBERON:00000941 (uri is the web address)

		edge_keys = []
		edge_types = dict()
		edge_source_db = dict()
		edge_source_iri = dict()
		edge_target_iri = dict()
		edge_source_curie = dict()
		edge_target_curie = dict()
		for u, v, data in edges:
			edge_keys.append((u, v))
			edge_types[(u, v)] = data['type']
			edge_source_db[(u, v)] = data['properties']['provided_by']
			edge_source_iri[(u, v)] = node_uuids2iri[data['properties']['source_node_uuid']]
			edge_target_iri[(u, v)] = node_uuids2iri[data['properties']['target_node_uuid']]
			edge_source_curie[(u,v)] = node_uuids2curie[data['properties']['source_node_uuid']]
			edge_target_curie[(u, v)] = node_uuids2curie[data['properties']['target_node_uuid']]

		# For each node, populate the relevant information
		node_objects = []
		node_iris_to_node_object = dict()
		for node_key in node_keys:
			node = Node()
			node.id = node_curies[node_key]
			node.type = node_labels[node_key]
			node.name = node_names[node_key]
			node.uri = node_iris[node_key]
			node.accession = node_accessions[node_key]
			node.description = node_descriptions[node_key]
			node_objects.append(node)
			node_iris_to_node_object[node_iris[node_key]] = node

		# for each edge, create an edge between them
		edge_objects = []
		for u, v in edge_keys:
			edge = Edge()
			edge.type = edge_types[(u, v)]
			edge.source_id = node_iris_to_node_object[edge_source_iri[(u, v)]].id
			edge.target_id = node_iris_to_node_object[edge_target_iri[(u, v)]].id
			#edge.origin_list = []
			#edge.origin_list.append(edge_source_db[(u, v)])  # TODO: check with eric if this really should be a list and if it should contain the source DB('s)
			edge.provided_by = edge_source_db[(u, v)]
			edge_objects.append(edge)

		# Create the result (potential answer)
		result1 = Result()
		text = "This is a subgraph extracted from the full RTX knowledge graph, including nodes and edges relevant to the query." \
			   " This is not an answer to the query per se, but rather an opportunity to examine a small region of the RTX knowledge graph for further study. " \
			   "Formal answers to the query are below."
		result1.text = text
		result1.confidence = confidence
		result1.result_type = "neighborhood graph"

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
		#self._num_results += 1
		#if self._num_results == 1:
		#	self.response.message = "%s result found" % self._num_results
		#else:
		#	self.response.message = "%s results found" % self._num_results

if __name__ == '__main__':
	test = FormatResponse(2)
	g = RU.return_subgraph_through_node_labels("CHEMBL154", 'chemical_substance', 'DOID:8398', 'disease',
											   ['protein', 'anatomical_entity', 'phenotypic_feature'],
											   directed=False)
	test.add_neighborhood_graph(g.nodes(data=True), g.edges(data=True), confidence=.95)
	test.add_neighborhood_graph(g.nodes(data=True), g.edges(data=True), confidence=.00)
	print(test)

