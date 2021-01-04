# This script will populate Eric's standardized output object model with a given networkx neo4j instance of nodes/edges
from __future__ import print_function
import sys
def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
RTXConfiguration = RTXConfiguration()

from swagger_server.models.message import Message
from swagger_server.models.result import Result
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.node_binding import NodeBinding
from swagger_server.models.edge_binding import EdgeBinding
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
		self._results = []
		self._num_results = 0
		# Create the message object and fill it with attributes about the response
		self.message = Message()
		self.message.type = "translator_reasoner_message"
		self.message.tool_version = RTXConfiguration.version
		self.message.schema_version = "0.9.2"
		self.message.message_code = "OK"
		#self.message.code_description = "Placeholder for description"
		self.message.code_description = "%s results found" % self._num_results

		#### Create an empty master knowledge graph
		self.message.knowledge_graph = KnowledgeGraph()
		self.message.knowledge_graph.nodes = []
		self.message.knowledge_graph.edges = []

		#### Create an internal lookup dict of nodes and edges for maintaining the master knowledge graph
		self._node_ids = dict()
		self._edge_ids = dict()
		self._edge_counter = 0


	def __str__(self):
		return repr(self.message)

	def print(self):
		print(json.dumps(ast.literal_eval(repr(self.message)), sort_keys=True, indent=2))

	def add_error_message(self, code, message):
		"""
		Add an error response to the message
		:param code: error code
		:param message: error message
		:return: None (modifies message)
		"""
		self.message.message_code = code
		self.message.code_description = message

	def add_text(self, description, confidence=1):
		result1 = Result()
		result1.description = description
		result1.confidence = confidence
		self._results.append(result1)
		self.message.results = self._results
		# Increment the number of results
		self._num_results += 1
		if self._num_results == 1:
			self.message.code_description = "%s result found" % self._num_results
		else:
			self.message.code_description = "%s results found" % self._num_results


	def add_subgraph(self, nodes, edges, description, confidence, return_result=False, suppress_bindings=False):
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
		edge_ids = dict()
		for u, v, data in edges:
			edge_keys.append((u, v))
			edge_types[(u, v)] = data['type']
			edge_source_db[(u, v)] = data['properties']['provided_by']
			edge_source_iri[(u, v)] = node_uuids2iri[data['properties']['source_node_uuid']]
			edge_target_iri[(u, v)] = node_uuids2iri[data['properties']['target_node_uuid']]
			edge_source_curie[(u,v)] = node_uuids2curie[data['properties']['source_node_uuid']]
			edge_target_curie[(u, v)] = node_uuids2curie[data['properties']['target_node_uuid']]
			edge_ids[(u, v)] = data['properties']['provided_by'] # FIXME

		# For each node, populate the relevant information
		node_objects = []
		node_iris_to_node_object = dict()
		for node_key in node_keys:
			node = Node()
			node.id = node_curies[node_key]
			node.type = [ node_labels[node_key] ]
			node.name = node_names[node_key]
			node.uri = node_iris[node_key]
			node.accession = node_accessions[node_key]
			node.description = node_descriptions[node_key]
			node_objects.append(node)
			node_iris_to_node_object[node_iris[node_key]] = node

			#### Add this node to the master knowledge graph
			if node.id not in self._node_ids:
				self.message.knowledge_graph.nodes.append(node)
				self._node_ids[node.id] = node.type[0]			# Just take the first of potentially several FIXME

		#### Create the bindings lists
		node_bindings = list()
		edge_bindings = list()

		# for each edge, create an edge between them
		edge_objects = []
		for u, v in edge_keys:
			edge = Edge()
			#edge.id is set below when building the bindings
			edge.type = edge_types[(u, v)]
			edge.source_id = node_iris_to_node_object[edge_source_iri[(u, v)]].id
			edge.target_id = node_iris_to_node_object[edge_target_iri[(u, v)]].id
			edge_objects.append(edge)
			#edge.attribute_list
			#edge.confidence
			#edge.evidence_type
			edge.is_defined_by = "RTX"
			edge.provided_by = edge_source_db[(u, v)]
			#edge.publications
			#edge.qualifiers
			#edge.relation
			#edge.source_id
			#edge.target_id
			#edge.type

			#### Add this edge to the master knowledge graph
			edge_str = "%s -%s- %s" % (edge.source_id,edge.type,edge.target_id)
			if edge_str not in self._edge_ids:
				self.message.knowledge_graph.edges.append(edge)
				edge.id = "%d" % self._edge_counter
				self._edge_ids[edge_str] = edge.id
				self._edge_counter += 1
			else:
				edge.id = self._edge_ids[edge_str]

			#### Try to figure out how the source fits into the query_graph for the bindings
			source_type = self._node_ids[edge.source_id]
			if edge.source_id in self._type_map:
				source_knowledge_map_key = self._type_map[edge.source_id]
			else:
				source_knowledge_map_key = self._type_map[source_type]
			if not source_knowledge_map_key:
				eprint("Expected to find '%s' in the response._type_map, but did not" % source_type)
				raise Exception("Expected to find '%s' in the response._type_map, but did not" % source_type)

			node_bindings.append(NodeBinding(qg_id=source_knowledge_map_key, kg_id=edge.source_id))
#			if source_knowledge_map_key not in node_bindings:
#				node_bindings[source_knowledge_map_key] = list()
#				node_bindings_dict[source_knowledge_map_key] = dict()
#			if edge.source_id not in node_bindings_dict[source_knowledge_map_key]:
#				node_bindings[source_knowledge_map_key].append(edge.source_id)
#				node_bindings_dict[source_knowledge_map_key][edge.source_id] = 1

			#### Try to figure out how the target fits into the query_graph for the knowledge map
			target_type = self._node_ids[edge.target_id]
			if edge.target_id in self._type_map:
				target_knowledge_map_key = self._type_map[edge.target_id]
			else:
				target_knowledge_map_key = self._type_map[target_type]
			if not target_knowledge_map_key:
				eprint("ERROR: Expected to find '%s' in the response._type_map, but did not" % target_type)
				raise Exception("Expected to find '%s' in the response._type_map, but did not" % target_type)

			node_bindings.append(NodeBinding(qg_id=target_knowledge_map_key, kg_id=edge.target_id))
#			if target_knowledge_map_key not in node_bindings:
#				node_bindings[target_knowledge_map_key] = list()
#				node_bindings_dict[target_knowledge_map_key] = dict()
#			if edge.target_id not in node_bindings_dict[target_knowledge_map_key]:
#				node_bindings[target_knowledge_map_key].append(edge.target_id)
#				node_bindings_dict[target_knowledge_map_key][edge.target_id] = 1

			#### Try to figure out how the edge fits into the query_graph for the knowledge map
			source_target_key = "e"+source_knowledge_map_key+"-"+target_knowledge_map_key
			target_source_key = "e"+target_knowledge_map_key+"-"+source_knowledge_map_key
			if edge.type in self._type_map:
				knowledge_map_key = self._type_map[edge.type]
			elif source_target_key in self._type_map:
				knowledge_map_key = source_target_key
			elif target_source_key in self._type_map:
				knowledge_map_key = target_source_key
			else:
				eprint("ERROR: Expected to find '%s' or '%s' or '%s' in the response._type_map, but did not" % (edge.type,source_target_key,target_source_key))
				knowledge_map_key = "ERROR"

			edge_bindings.append(EdgeBinding(qg_id=knowledge_map_key, kg_id=edge.id))
#			if knowledge_map_key not in edge_bindings:
#				edge_bindings[knowledge_map_key] = list()
#				edge_bindings_dict[knowledge_map_key] = dict()
#			if edge.id not in edge_bindings_dict[knowledge_map_key]:
#				edge_bindings[knowledge_map_key].append(edge.id)
#				edge_bindings_dict[knowledge_map_key][edge.id] = 1

		# Create the result (potential answer)
		result1 = Result()
		result1.reasoner_id = "RTX"
		result1.description = description
		result1.confidence = confidence
		if suppress_bindings is False:
			result1.node_bindings = node_bindings
			result1.edge_bindings = edge_bindings

		# Create a KnowledgeGraph object and put the list of nodes and edges into it
		#### This is still legal, then is redundant with the knowledge map, so leave it out maybe
		knowledge_graph = KnowledgeGraph()
		knowledge_graph.nodes = node_objects
		knowledge_graph.edges = edge_objects
		if suppress_bindings is True:
			result1.result_graph = knowledge_graph

		# Put the first result (potential answer) into the message
		self._results.append(result1)
		self.message.results = self._results

		# Increment the number of results
		self._num_results += 1
		if self._num_results == 1:
			self.message.code_description = "%s result found" % self._num_results
		else:
			self.message.code_description = "%s results found" % self._num_results

		#### Finish and return the result if requested
		if return_result:
			return result1
		else:
			pass


	def add_split_results(self, knowledge_graph, result_bindings):
		"""
		Populate the object model with the resulting raw knowledge_graph and result_bindings (initially from QueryGraphReasoner)
		:param nodes: knowledge_graph in native RTX KG dump
		:param edges: result_bindings in a native format from QueryGraphReasoner
		:return: none
		"""

		#### Add the knowledge_graph nodes
		regular_node_attributes = [ "id", "uri", "name", "description", "symbol" ] 
		for input_node in knowledge_graph["nodes"]:
			node = Node()
			for attribute in regular_node_attributes:
				if attribute in input_node:
					setattr(node,attribute,input_node[attribute])
			node.type = [ input_node["category"] ]
			#node.node_attributes = FIXME
			self.message.knowledge_graph.nodes.append(node)

		#### Add the knowledge_graph edges
		regular_edge_attributes = [ "id", "type", "relation", "source_id", "target_id",
			"is_defined_by", "defined_datetime", "provided_by", "weight", "evidence_type", "qualifiers", "negated", "", "" ] 
		for input_edge in knowledge_graph["edges"]:
			edge = Edge()
			for attribute in regular_edge_attributes:
				if attribute in input_edge:
					setattr(edge,attribute,input_edge[attribute])
			if "probability" in input_edge: edge.confidence = input_edge["probability"]
			# missing edge properties: defined_datetime, weight, publications, evidence_type, qualifiers, negated
			# extra edge properties: predicate, 
			#edge.edge_attributes = FIXME
			#edge.publications = FIXME
			self.message.knowledge_graph.edges.append(edge)

		#### Add each result
		self.message.results = []
		for input_result in result_bindings:
			result = Result()
			result.description = "No description available"
			result.essence = "?"
			#result.essence_type = "?"
			#result.row_data = "?"
			#result.score = 0
			#result.score_name = "?"
			#result.score_direction = "?"
			result.confidence = 1.0
			result.result_type = "individual query answer"
			result.reasoner_id = "RTX"
			result.result_graph = None
			result.node_bindings = input_result["nodes"]
#			#### Convert each binding value to a list because the viewer requires it
#			for binding in result.node_bindings:
#				result.node_bindings[binding] = [ result.node_bindings[binding] ]
			result.edge_bindings = input_result["edges"]
			self.message.results.append(result)

		#### Set the code_description
		n_results = len(result_bindings)
		plural = "s"
		if n_results == 1: plural = ""
		self.message.code_description = f"{n_results} result{plural} found"

		#### Complete normally
		return()


	def infer_result_information(self):
		"""
		Populate the individual results with some inferences based on a query_graph and bindings
		:return: none
		"""

		#### Get the number of nodes that we have
		if self.message.query_graph is None: return()
		if self.message.query_graph["nodes"] is None: return()
		n_nodes = len(self.message.query_graph["nodes"])
		if n_nodes == 0: return()

		#### Loop over the query_graph nodes trying to learn about the query
		essence_node = None
		for node in self.message.query_graph["nodes"]:
			if "curie" in node and node["curie"] is not None:
			  if essence_node is None: essence_node = node["id"]
			else:
			  essence_node = node["id"]

		#print(f"n_nodes={n_nodes}")
		#print(f"essence_node={essence_node}")

		#### Loop over the results, updating with some useful information
		if self.message.results is None: return()
		n_results = len(self.message.results)
		if n_results == 0: return()

		# Convert knowledge graph nodes to dictionary format for faster processing below
		kg_nodes_dict = dict()
		for node in self.message.knowledge_graph.nodes:
			kg_nodes_dict[node.id] = node

		for result in self.message.results:
			essence_node_curie = None
			essence_node_name = "?"
			essence_node_type = "?"

			#### Look for the essence_node in the result
			if result.node_bindings is not None:
				if essence_node in result.node_bindings:
					essence_node_curie = result.node_bindings[essence_node]
					if isinstance(essence_node_curie,list):
						essence_node_curie = essence_node_curie[0]                  ## FIXME. Just taking element 0 isn't very good

					# print(f"looking for {essence_node_curie}")
					matching_node_in_kg = kg_nodes_dict.get(essence_node_curie)
					if matching_node_in_kg:
						essence_node_name = matching_node_in_kg.name
						essence_node_type = matching_node_in_kg.type
						if isinstance(essence_node_type, list):
							essence_node_type = essence_node_type[0]  ## FIXME. Just taking element 0 isn't very good
						result.essence = essence_node_name
						result.essence_type = essence_node_type

			#### Reorganize the 0.9.1 formatted node bindings to 0.9.2 formatted bindings
			if result.node_bindings is not None:
				new_bindings = []
				for qg_id, kg_id in result.node_bindings.items():
					new_bindings.append( { "qg_id": qg_id, "kg_id": kg_id } )
				result.node_bindings = new_bindings

			#### Reorganize the 0.9.1 formatted edge bindings to 0.9.2 formatted bindings
			if result.edge_bindings is not None:
				new_bindings = []
				for qg_id, kg_id in result.edge_bindings.items():
					new_bindings.append( { "qg_id": qg_id, "kg_id": kg_id } )
				result.edge_bindings = new_bindings


		return()


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
			edge_source_curie[(u, v)] = node_uuids2curie[data['properties']['source_node_uuid']]
			edge_target_curie[(u, v)] = node_uuids2curie[data['properties']['target_node_uuid']]

		# For each node, populate the relevant information
		node_objects = []
		node_iris_to_node_object = dict()
		for node_key in node_keys:
			node = Node()
			node.id = node_curies[node_key]
			node.type = [ node_labels[node_key] ]
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
			edge.is_defined_by = "RTX"
			edge_objects.append(edge)

		# Create the result (potential answer)
		result1 = Result()
		description = "This is a subgraph extracted from the full RTX knowledge graph, including nodes and edges relevant to the query." \
			   " This is not an answer to the query per se, but rather an opportunity to examine a small region of the RTX knowledge graph for further study. " \
			   "Formal answers to the query are below."
		result1.description = description
		result1.confidence = confidence
		result1.result_type = "neighborhood graph"

		# Create a KnowledgeGraph object and put the list of nodes and edges into it
		knowledge_graph = KnowledgeGraph()
		knowledge_graph.nodes = node_objects
		knowledge_graph.edges = edge_objects

		# Put the KnowledgeGraph into the first result (potential answer)
		result1.knowledge_graph = knowledge_graph

		# Put the first result (potential answer) into the message
		self._results.append(result1)
		self.message.results = self._results
		# Increment the number of results
		#self._num_results += 1
		#if self._num_results == 1:
		#	self.message.code_description = "%s result found" % self._num_results
		#else:
		#	self.message.code_description = "%s results found" % self._num_results


if __name__ == '__main__':
	test = FormatResponse(2)
	g = RU.return_subgraph_through_node_labels("CHEMBL154", 'chemical_substance', 'DOID:8398', 'disease',
											   ['protein', 'anatomical_entity', 'phenotypic_feature'],
											   directed=False)
	test.add_neighborhood_graph(g.nodes(data=True), g.edges(data=True), confidence=.95)
	test.add_neighborhood_graph(g.nodes(data=True), g.edges(data=True), confidence=.00)
	print(test)

