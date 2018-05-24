# This script will contain a bunch of utilities that help with graph/path extraction
# Should subsume Q1Utils and Q2Utils
import networkx as nx
from numpy import linalg as LA
import numpy as np
np.warnings.filterwarnings('ignore')
import cypher
import os
import sys
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
from collections import Counter
import requests_cache
from itertools import islice
import itertools
import functools
import CustomExceptions
try:
	from QueryCOHD import QueryCOHD
except ImportError:
	sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'kg-construction'))
	from QueryCOHD import QueryCOHD
# Import stuff from one level up
try:
	import QueryNCBIeUtils
except ImportError:
	sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../kg-construction')))  # Go up one level and look for it
	import QueryNCBIeUtils

import math
import MarkovLearning
try:
	import QueryEBIOLS
except ImportError:
	sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../kg-construction')))  # Go up one level and look for it
	import QueryEBIOLS

try:
	from NormGoogleDistance import NormGoogleDistance
except ImportError:
	sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../kg-construction')))  # Go up one level and look for it
	from NormGoogleDistance import NormGoogleDistance

QueryEBIOLS = QueryEBIOLS.QueryEBIOLS()
QueryNCBIeUtils = QueryNCBIeUtils.QueryNCBIeUtils()


requests_cache.install_cache('orangeboard')

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
RTXConfiguration = RTXConfiguration()

# Connection information for the neo4j server, populated with orangeboard
driver = GraphDatabase.driver(RTXConfiguration.bolt, auth=basic_auth("neo4j", "precisionmedicine"))
session = driver.session()

# Connection information for the ipython-cypher package
connection = "http://neo4j:precisionmedicine@" + RTXConfiguration.database
DEFAULT_CONFIGURABLE = {
	"auto_limit": 0,
	"style": 'DEFAULT',
	"short_errors": True,
	"data_contents": True,
	"display_limit": 0,
	"auto_pandas": False,
	"auto_html": False,
	"auto_networkx": False,
	"rest": False,
	"feedback": False,  # turn off verbosity in ipython-cypher
	"uri": connection,
}
DefaultConfigurable = namedtuple(
	"DefaultConfigurable",
	", ".join([k for k in DEFAULT_CONFIGURABLE.keys()])
)
defaults = DefaultConfigurable(**DEFAULT_CONFIGURABLE)


def node_exists_with_property(term, property_name, node_label="",session=session):
	"""
	Check if the neo4j has a node with the given name as a given property
	:param term: term to check (eg. 'naproxen')
	:param property_name: relevant node property (eg. 'description' or 'name')
	:param session: neo4j instance
	:return: Boolean
	"""
	if node_label == "":
		query = "match (n) where n.%s='%s' return n" % (property_name, term)
	else:
		query = "match (n:%s{%s:'%s'}) return n" % (node_label, property_name, term)
	res = session.run(query)
	res = [i for i in res]
	if not res:
		return False
	else:
		return True


def count_nodes():
	"""
	Count the number of nodes
	:param sessions: neo4j bolt session
	:return: int
	"""
	query = "match (n) return count(n)"
	res = session.run(query)
	return res.single()["count(n)"]


def get_random_nodes(label, property="rtx_name", num=10, debug=False):
	query = "match (n:%s) with rand() as r, n as n return n.%s order by r limit %d" % (label, property, num)
	if debug:
		return query
	else:
		res = session.run(query)
		res = [i["n.%s" % property] for i in res]
		return res


def get_relationship_types():
	"""
	Get all the edge labels in the neo4j database
	:param sessions: neo4j bolt session
	:return: list of node labels
	"""
	query = "match ()-[r]-() return distinct type(r)"
	res = session.run(query)
	res = [i["type(r)"] for i in res]
	return res


def get_node_labels():
	"""
	Get all the node labels in the neo4j database
	:param sessions: neo4j bolt session
	:return: list of relationship types
	"""
	query = "match (n) return distinct labels(n)"
	res = session.run(query)
	labels = []
	for i in res:
		label = list(set(i["labels(n)"]).difference({"Base"}))  # get rid of the extra base label
		label = label.pop()  # this assumes only a single relationship type, but that's ok since that's how neo4j works
		labels.append(label)
	return labels


def get_rtx_name_from_property(property_value, property_name, label=None, debug=False):
	"""
	Get a node with property having value property_value
	:param property_value: string
	:param property_name: string (eg. name)
	:return: string
	"""
	if label:
		query = "match (n:%s{%s:'%s'}) return n.rtx_name" % (label, property_name, property_value)
	else:
		query = "match (n{%s:'%s'}) return n.rtx_name" % (property_name, property_value)
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]["n.rtx_name"]
	else:
		return None

def get_name_to_description_dict(session=session):
	"""
	Create a dictionary of all nodes, keys being the names, items being the descriptions
	:param session: neo4j session
	:return: dictionary of node names and descriptions
	"""
	query = "match (n) return properties(n) as n"
	name_to_descr = dict()
	res = session.run(query)
	for item in res:
		item_dict = item['n']
		name_to_descr[item_dict['rtx_name']] = item_dict['name']
	return name_to_descr


def get_node_property(name, node_property, node_label="", name_type="rtx_name", session=session, debug=False):
	"""
	Get a property of a node. This replaces node_to_description by making node_property="description"
	:param name: name of the node
	:param node_property: property you wish to get info on (such as "description")
	:param node_label: (optional) label (kind) of node (makes the operation slightly faster)
	:param session: neo4j session
	:param debug: just return the query
	:return: a string (the description of the node)
	"""
	if node_property != "label":
		if node_label == "":
			query = "match (n{%s:'%s'}) return n.%s" % (name_type, name, node_property)
		else:
			query = "match (n:%s{%s:'%s'}) return n.%s" % (node_label, name_type, name, node_property)
		if debug:
			return query
		res = session.run(query)
		res = [i for i in res]  # consume the query
		if res:
			return res[0]['n.%s' % node_property]
		else:
			raise Exception("No result returned, property doesn't exist? node: %s" % name)
	else:
		if node_label == "":
			query = "match (n{%s:'%s'}) return labels(n)" % (name_type, name)
		else:
			query = "match (n:%s{%s:'%s'}) return labels(n)" % (name_type, node_label, name)
		if debug:
			return query
		res = session.run(query)
		res = [i for i in res]  # consume the query
		if res:
			node_types = res[0]['labels(n)']
			node_type = list(set(node_types).difference({"Base"}))
			return node_type.pop()  # TODO: this assume only a single result is returned
		else:
			raise Exception("No result returned, property doesn't exist? node: %s" % name)


# Get node names in paths between two fixed endpoints
def get_node_names_of_type_connected_to_target(source_label, source_name, target_label, max_path_len=4, debug=False, verbose=False, direction="u", session=session, is_omim=False):
	"""
	This function finds all node names of a certain kind (label) within max_path_len steps of a given source node.
	This replaces 'get_omims_connecting_to_fixed_doid' by using the source_label=disease, target_label=disease.
	:param source_label: kind of source node (eg: disease)
	:param source_name: actual name of the source node (eg: DOID:14793)
	:param target_label: kind of target nodes to look for (eg: disease)
	:param max_path_len: Maximum path length to consider (default =4)
	:param debug: flag indicating if the query should also be returned
	:param direction: Which direction to look (u: undirected, f: source->target, r: source<-target
	:param session: neo4j server session
	:return: list of omim ID's
	"""
	if is_omim:
		query = "MATCH path=shortestPath((t:%s)-[*1..%d]-(s:%s))" \
				" WHERE s.rtx_name='%s' AND t<>s AND t.rtx_name=~'OMIM:.*' WITH distinct nodes(path)[0] as p RETURN p.rtx_name" % (
				target_label, max_path_len, source_label, source_name)
	elif direction == "r":
		query = "MATCH path=shortestPath((t:%s)-[*1..%d]->(s:%s))" \
				" WHERE s.rtx_name='%s' AND t<>s WITH distinct nodes(path)[0] as p RETURN p.rtx_name" % (target_label, max_path_len, source_label, source_name)
	elif direction == "f":
		query = "MATCH path=shortestPath((t:%s)<-[*1..%d]-(s:%s))" \
				" WHERE s.rtx_name='%s' AND t<>s WITH distinct nodes(path)[0] as p RETURN p.rtx_name" % (
				target_label, max_path_len, source_label, source_name)
	elif direction == "u":
		query = "MATCH path=shortestPath((t:%s)-[*1..%d]-(s:%s))" \
				" WHERE s.rtx_name='%s' AND t<>s WITH distinct nodes(path)[0] as p RETURN p.rtx_name" % (target_label, max_path_len, source_label, source_name)
	else:
		raise Exception("Sorry, the direction must be one of 'f', 'r', or 'u'")
	if debug:
		return query
	result = session.run(query)
	result_list = [i for i in result]
	names = [i['p.rtx_name'] for i in result_list]
	if verbose:
		print("Found %d nearby %s's" % (len(names), target_label))
	if debug:
		return names, query
	else:
		return names


def get_one_hop_target(source_label, source_name, target_label, edge_type, debug=False, verbose=False, direction="u", session=session):
	"""
	This function finds all target nodes connected in one hop to a source node (with a given edge type). EG: what proteins does drug X target?
	:param source_label: kind of source node (eg: disease)
	:param source_name: actual name of the source node (eg: DOID:14793)
	:param target_label: kind of target nodes to look for (eg: disease)
	:param edge_type: Type of edge to be interested in (eg: directly_interacts_with, affects)
	:param debug: flag indicating if the query should also be returned
	:param direction: Which direction to look (u: undirected, f: source->target, r: source<-target
	:param session: neo4j server session
	:return: list of omim ID's
	"""
	if direction == "r":
		query = "MATCH path=(s:%s{rtx_name:'%s'})<-[:%s]-(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.rtx_name" % (source_label, source_name, edge_type, target_label)
	elif direction == "f":
		query = "MATCH path=(s:%s{rtx_name:'%s'})-[:%s]->(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.rtx_name" % (
				source_label, source_name, edge_type, target_label)
	elif direction == "u":
		query = "MATCH path=(s:%s{rtx_name:'%s'})-[:%s]-(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.rtx_name" % (
				source_label, source_name, edge_type, target_label)
	else:
		raise Exception("Sorry, the direction must be one of 'f', 'r', or 'u'")
	result = session.run(query)
	result_list = [i for i in result]
	names = [i['p.rtx_name'] for i in result_list]
	if verbose:
		print("Found %d nearby %s's" % (len(names), target_label))
	if debug:
		return names, query
	else:
		return names

def get_relationship_types_between(source_name, source_label, target_name, target_label, max_path_len=4, session=session, debug=False):
	"""
	This function will return the relationship types between fixed source and target nodes
	:param source_name: source node name (eg: DOID:1234).
	This replaces get_rels_fixed_omim_to_fixed_doid().
	:param target_name: target node name (eg: skin rash)
	:param max_path_len: maximum path length to consider
	:param session: neo4j driver session
	:return: returns a list of tuples where tup[0] is the list of relationship types, tup[1] is the count.
	unless max_path_len=1 and it's missing a target_name, then just return the relationship types
	"""
	if max_path_len == 1 and source_name and not target_name:
		query = "match (s:%s{rtx_name:'%s'})-[r]-(t:%s) return distinct type(r)" % (source_label, source_name, target_label)
		if debug:
			return query
		else:
			res = session.run(query)
			res = [i["type(r)"] for i in res]
			return res
	elif max_path_len == 1 and not source_name and not target_name:
		query = "match (s:%s)-[r]-(t:%s) return distinct type(r)" % (source_label, target_label)
		if debug:
			return query
		else:
			res = session.run(query)
			res = [i["type(r)"] for i in res]
			return res
	else:
		query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]-(t:%s)) " \
				"WHERE s.rtx_name='%s' AND t.rtx_name='%s' " \
				"RETURN distinct extract (rel in relationships(path) | type(rel) ) as types, count(*)" % (source_label, max_path_len, target_label, source_name, target_name)
		with session.begin_transaction() as tx:
			result = tx.run(query)
			result_list = [i for i in result]
			return_list = list()
			for item in result_list:
				return_list.append((item['types'], item['count(*)']))
			if debug:
				return return_list, query
			else:
				return return_list


# Convert ipython-cypher query (from cypher query) into a networkx graph
def get_graph(res, directed=True, multigraph=False):
	"""
	This function takes the result (subgraph) of a ipython-cypher query and builds a networkx graph from it
	:param res: output from an ipython-cypher query
	:param directed: Flag indicating if the resulting graph should be treated as directed or not
	:return: networkx graph (MultiDiGraph or MultiGraph)
	"""
	if not res:
		#raise Exception("Empty graph. Cypher query input returned no results.")
		raise CustomExceptions.EmptyCypherError("unkown query")
	if nx is None:
		raise ImportError("Try installing NetworkX first.")
	if multigraph:
		if directed:
			graph = nx.MultiDiGraph()
		else:
			graph = nx.MultiGraph()
	else:
		if directed:
			graph = nx.DiGraph()
		else:
			graph = nx.Graph()
	for item in res._results.graph:
		for node in item['nodes']:
			graph.add_node(node['id'], properties=node['properties'], labels=node['labels'], names=node['properties']['rtx_name'], description=node['properties']['name'], id=node['properties']['id'])
		for rel in item['relationships']:
			graph.add_edge(rel['startNode'], rel['endNode'], id=rel['id'], properties=rel['properties'], type=rel['type'])
	return graph


def get_graph_from_nodes(id_list, node_property_label="rtx_name", debug=False):
	"""
	For a list of property names, return a subgraph with those nodes in it
	:param id_list: a list of identifiers
	:param node_property_label: what the identier property is (eg. rtx_name)
	:param debug:
	:return:
	"""
	query = "match (n) where n.%s in [" % node_property_label
	for ID in id_list:
		if ID != id_list[-1]:
			query += " '%s'," % ID
		else:
			query += " '%s'] return n" % ID
	if debug:
		return query
	else:
		try:
			graph = get_graph(cypher.run(query, conn=connection, config=defaults), directed=False)
		except CustomExceptions.EmptyCypherError:
			raise CustomExceptions.EmptyCypherError(query)
		return graph


# since multiple paths can connect two nodes, treat it as a Markov chain and compute the expected path length
# connecting the source omim and the target doid
def expected_graph_distance(source_node, source_node_label, target_node, target_node_label, max_path_len=4, directed=False, connection=connection, defaults=defaults, debug=False):
	"""
	Given a source source_node and target target_node, extract the subgraph from neo4j consisting of all paths connecting these
	two nodes. Treat this as a uniform Markov chain (all outgoing edges with equal weight) and calculate the expected
	path length. This is equivalent to starting a random walker at the source node and calculating how long, on
	average, it takes to reach the target node.
	:param source_node: Input node name (eg: 'OMIM:614317'), source
	:param target_node: Input target name (eg: 'DOID:4916'), target
	:param max_path_len: maximum path length to consider (default=4)
	:param directed: treat the Markov chain as directed or undirected (default=True (directed))
	:param connection: ipython-cypher connection string
	:param defaults: ipython-cypher configurations named tuple
	:return: a pair of floats giving the expected path length from source to target, and target to source respectively
	along with the basis (list of source_node ID's).
	"""
	if directed:
		query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]->(t:%s)) " \
				"WHERE s.rtx_name='%s' AND t.rtx_name='%s' " \
				"RETURN path" % (source_node_label, max_path_len, target_node_label, source_node, target_node)
	else:
		query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]-(t:%s)) " \
				"WHERE s.rtx_name='%s' AND t.rtx_name='%s' " \
				"RETURN path" % (source_node_label, max_path_len, target_node_label, source_node, target_node)
	if debug:
		print(query)
		return
	res = cypher.run(query, conn=connection, config=defaults)
	graph = get_graph(res, directed=directed)  # Note: I may want to make this directed, but sometimes this means no path from OMIM
	mat = nx.to_numpy_matrix(graph)  # get the indidence matrix
	#basis = [i[1] for i in list(graph.nodes(data='names'))]  # basis for the matrix (i.e. list of ID's)
	basis = [d['names'] for u,d in graph.nodes(data=True)]
	doid_index = basis.index(target_node)  # position of the target
	omim_index = basis.index(source_node)  # position of the source
	# print(source_node)  # diagnostics
	if directed:  # if directed, then add a sink node just after the target, make sure we can pass over it
		sink_column = np.zeros((mat.shape[0], 1))
		sink_column[doid_index] = 1  # connect target_node to sink node
		sink_row = np.zeros((1, mat.shape[0] + 1))
		sink_row[0, -1] = 1  # make sink node got to itself
		mat = np.vstack([np.append(mat, sink_column, 1), sink_row])  # append the sink row and column
		row_sums = mat.sum(axis=1)
		zero_indicies = np.where(row_sums == 0)[0]  # even after this, some nodes may not have out-going arrows
		for index in zero_indicies:
			mat[index, index] = 1  # put a self loop in, so we don't get division by zero
		row_sums = mat.sum(axis=1)
		mat_norm = mat / row_sums  # row normalize
	else:
		row_sums = mat.sum(axis=1)
		mat_norm = mat / row_sums
	exp_o_to_d = np.sum([float(i) * LA.matrix_power(mat_norm, i)[omim_index, doid_index] for i in range(15)])  # No need to take the whole infinite sum, let's just do the first 15 terms in the power series
	exp_d_to_o = np.sum([float(i) * LA.matrix_power(mat_norm, i)[doid_index, omim_index] for i in range(15)])
	if exp_o_to_d == 0:
		exp_o_to_d = float("inf")  # no such path
	if exp_d_to_o == 0:
		exp_d_to_o = float("inf")  # no such path
	return (exp_o_to_d, exp_d_to_o)  # (E(source->target), E(target->source))


def return_subgraph_paths_of_type(source_node, source_node_label, target_node, target_node_label, relationship_list, directed=True, debug=False):
	"""
	This function extracts the subgraph of a neo4j database consisting of those paths that have the relationships (in
	order) of those given by relationship_list
	:param session: neo4j session
	:param source_node: source node name (eg: DOID:1798)
	:param target_node: target node name (eg: 'DOID:0110307')
	:param relationship_list: list of relationships (must be valid neo4j relationship types), if this is a list of lists
	then the subgraph consisting of all valid paths will be returned
	:param debug: Flag indicating if the cypher query should be returned
	:return: networkx graph
	"""
	if not any(isinstance(el, list) for el in relationship_list):  # It's a single list of relationships
		if directed:
			if target_node is not None:
				query = "MATCH path=(s:%s)-" % source_node_label
				for i in range(len(relationship_list) - 1):
					query += "[:" + relationship_list[i] + "]->()-"
				query += "[:" + relationship_list[-1] + "]->" + "(t:%s) " % target_node_label
				query += "WHERE s.rtx_name='%s' and t.rtx_name='%s' " % (source_node, target_node)
				query += "RETURN path"
			else:
				query = "MATCH path=(s:%s)-" % source_node_label
				for i in range(len(relationship_list) - 1):
					query += "[:" + relationship_list[i] + "]->()-"
				query += "[:" + relationship_list[-1] + "]->" + "(t:%s) " % target_node_label
				query += "WHERE s.rtx_name='%s'" % (source_node)
				query += "RETURN path"
			if debug:
				return query
		else:
			if target_node is not None:
				query = "MATCH path=(s:%s)-" % source_node_label
				for i in range(len(relationship_list) - 1):
					query += "[:" + relationship_list[i] + "]-()-"
				query += "[:" + relationship_list[-1] + "]-" + "(t:%s) " % target_node_label
				query += "WHERE s.rtx_name='%s' and t.rtx_name='%s' " % (source_node, target_node)
				query += "RETURN path"
			else:
				query = "MATCH path=(s:%s)-" % source_node_label
				for i in range(len(relationship_list) - 1):
					query += "[:" + relationship_list[i] + "]-()-"
				query += "[:" + relationship_list[-1] + "]-" + "(t:%s) " % target_node_label
				query += "WHERE s.rtx_name='%s'" % (source_node)
				query += "RETURN path"
			if debug:
				return query
	else:  # it's a list of lists
		if directed:
			query = "MATCH (s:%s{rtx_name:'%s'}) " % (source_node_label, source_node)
			for rel_index in range(len(relationship_list)):
				rel_list = relationship_list[rel_index]
				query += "OPTIONAL MATCH path%d=(s)-" % rel_index
				for i in range(len(rel_list) - 1):
					query += "[:" + rel_list[i] + "]->()-"
				query += "[:" + rel_list[-1] + "]->" + "(t:%s)" % target_node_label
				query += " WHERE t.rtx_name='%s' " % target_node
			query += "RETURN "
			for rel_index in range(len(relationship_list) - 1):
				query += "collect(path%d)+" % rel_index
			query += "collect(path%d)" % (len(relationship_list) - 1)
			if debug:
				return query
		else:
			query = "MATCH (s:%s{rtx_name:'%s'}) " % (source_node_label, source_node)
			for rel_index in range(len(relationship_list)):
				rel_list = relationship_list[rel_index]
				query += "OPTIONAL MATCH path%d=(s)-" % rel_index
				for i in range(len(rel_list) - 1):
					query += "[:" + rel_list[i] + "]-()-"
				query += "[:" + rel_list[-1] + "]-" + "(t:%s)" % target_node_label
				query += " WHERE t.rtx_name='%s' " % target_node
			query += "RETURN "
			for rel_index in range(len(relationship_list) - 1):
				query += "collect(path%d)+" % rel_index
			query += "collect(path%d)" % (len(relationship_list) - 1)
			if debug:
				return query
	try:
		graph = get_graph(cypher.run(query, conn=connection, config=defaults), directed=directed)
	except CustomExceptions.EmptyCypherError:
		raise CustomExceptions.EmptyCypherError(query)
	return graph


def return_subgraph_through_node_labels(source_node, source_node_label, target_node, target_node_label, node_list,
										with_rel=[], directed=True, debug=False):
	"""
	Return a subgraph with the following constraints: from source_node to target_node through node_list node labels.
	Optionally only return paths that have a (node_label)-[relationship_type]-(node_label) give by the three element
	list with_rel.
	:param source_node: Source node name (eg. 'naproxen')
	:param source_node_label:  source node label (eg. 'drug')
	:param target_node: target node name (eg. 'DOID:8398') or a list of names (["x","y","z"]) all must be of target_node_label type
	:param target_node_label: target node lable (eg. 'disease')
	:param node_list: list of node labels that all paths must go through
	:param with_rel: an optional triplet where with_rel[0] is a node label, with_rel[1] is a relationship type,
	and with_rel[2] is a node label
	:param directed: If the graph should be directed or not
	:param debug: Just print the cypher query
	:return: a networkx graph containing all paths satisfying the query
	"""
	if with_rel:
		if any(isinstance(el, list) for el in node_list):
			raise Exception("node_list must be a single list of nodes (not a list of lists) if you want to use with_rel.")
		query = "MATCH path=(%s:%s{rtx_name:'%s'})" % (source_node_label, source_node_label, source_node)
		for i in range(len(node_list) - 1):
			if with_rel[0] == node_list[i]:
				query += "-[]-(%s:%s)" % (node_list[i], node_list[i])
			else:
				query += "-[]-(:%s)" % node_list[i]
		query += "-[]-(:%s)-[]-(%s:%s{rtx_name:'%s'}) " % (node_list[-1], target_node_label, target_node_label, target_node)
		query += "WHERE exists((%s)-[:%s]-(%s)) " % (with_rel[0], with_rel[1], with_rel[2])
		query += "RETURN path"
		if debug:
			return query
	elif not any(isinstance(el, list) for el in node_list):  # It's a single list of relationships
		if not isinstance(target_node, list):
			query = "MATCH path=(s:%s)" % source_node_label
			for i in range(len(node_list) - 1):
				query += "-[]-(:" + node_list[i] + ")"
			query += "-[]-(:" + node_list[-1] + ")-[]-" + "(t:%s) " % target_node_label
			query += "WHERE s.rtx_name='%s' and t.rtx_name='%s' " % (source_node, target_node)
			query += "RETURN path"
		else:
			query = "MATCH path=(s:%s)" % source_node_label
			for i in range(len(node_list) - 1):
				query += "-[]-(:" + node_list[i] + ")"
			query += "-[]-(:" + node_list[-1] + ")-[]-" + "(t:%s) " % target_node_label
			query += "WHERE s.rtx_name='%s' and t.rtx_name in ['%s'" % (source_node, target_node[0])
			for node in target_node:
				query += ",'%s'" % node
			query += "] "
			query += "RETURN path"
		if debug:
			return query
	else:  # it's a list of lists
		query = "MATCH (s:%s{rtx_name:'%s'}) " % (source_node_label, source_node)
		for rel_index in range(len(node_list)):
			rel_list = node_list[rel_index]
			query += "OPTIONAL MATCH path%d=(s)" % rel_index
			for i in range(len(rel_list) - 1):
				query += "-[]-(:" + rel_list[i] + ")"
			query += "-[]-(:" + rel_list[-1] + ")-[]-" + "(t:%s)" % target_node_label
			query += " WHERE t.rtx_name='%s' " % target_node
		query += "RETURN "
		for rel_index in range(len(node_list) - 1):
			query += "collect(path%d)+" % rel_index
		query += "collect(path%d)" % (len(node_list) - 1)
		if debug:
			return query
	res = cypher.run(query, conn=connection, config=defaults)
	if not res:
		raise CustomExceptions.EmptyCypherError(query)
	else:
		graph = get_graph(res, directed=directed)
		return graph


def get_shortest_subgraph_between_nodes(source_name, source_label, target_name, target_label, max_path_len=4, limit=50,
										debug=False, directed=False):
	"""
	This function will return the sugraph between between fixed source and target nodes
	:param source_name: source node name (in KG)
	:param source_label: source node label
	:param target_name: target node name
	:param target_label: target node label
	:param max_path_len: maximum path length to consider
	:param limit: max number of paths to return
	:param session: neo4j session
	:param debug: just return the cypher query
	:param directed: treat the graph as directed or not
	:return: networkx graph
	"""
	query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]-(t:%s)) " \
			"WHERE s.rtx_name='%s' AND t.rtx_name='%s' " \
			"RETURN path limit %d" % (source_label, max_path_len, target_label, source_name, target_name, limit)
	if debug:
		return query

	res = cypher.run(query, conn=connection, config=defaults)
	if not res:
		raise CustomExceptions.EmptyCypherError(query)
	else:
		graph = get_graph(res, directed=directed)
		return graph


def get_node_as_graph(node_name, debug=False, use_description=False):
	"""
	Get a node and return it as a networkx graph model
	:param node_name: KG neo4j node name
	:param debug: just return the cypher command
	:param use_description: use the description of the node, not the name
	:return: networkx graph
	"""
	if use_description:
		query = "MATCH (n{name:'%s'}) return n" % node_name
	else:
		query = "MATCH (n{rtx_name:'%s'}) return n" % node_name
	if debug:
		return query

	res = cypher.run(query, conn=connection, config=defaults)
	if not res:
		raise CustomExceptions.EmptyCypherError(query)
	else:
		graph = get_graph(res, directed=False)
		return graph


def return_exact_path(node_list, relationship_list, directed=True, debug=False):
	"""
	Returns a networkx representation of a path through node_list via relationship_list
	:param node_list: list of KG nodes
	:param relationship_list: list of KG relationships (in order)
	:param directed: return a directed graph or not
	:param debug: just print the cypher query
	:return: networkx graph of the path
	"""
	query = "MATCH path=(s{rtx_name:'%s'})-" % node_list[0]
	for i in range(len(relationship_list) - 1):
		query += "[:" + relationship_list[i] + "]-({rtx_name:'%s'})-" % node_list[i+1]
	query += "[:" + relationship_list[-1] + "]-" + "(t{rtx_name:'%s'}) " % node_list[-1]
	query += "RETURN path"
	if debug:
		return query

	graph = get_graph(cypher.run(query, conn=connection, config=defaults), directed=directed)
	return graph


def count_nodes_of_type_on_path_of_type_to_label(source_name, source_label, target_label, node_label_list, relationship_label_list, node_of_interest_position, debug=False, session=session):
	"""
	This function will take a source node, look for paths along given node and relationship types to a certain target node,
	and then count the number distinct number of nodes of interest that occur along that path.
	:param source_name: source node name
	:param source_label: source node label
	:param target_label: target node label
	:param node_label_list: list of node labels (eg. ['phenotypic_feature'])
	:param relationship_label_list: list of relationship types (eg. ['has_phenotype', 'has_phenotype'])
	:param node_of_interest_position: position of node to count (in this eg, node_of_interest_position = 0)
	:param debug: just print the cypher query
	:param session: neo4j session
	:return: two dictionaries: names2counts, names2nodes (keys = target node names, counts is number of nodes of interest in the paths, nodes are the actual nodes of interest)
	"""
	query = "MATCH (s:%s{rtx_name:'%s'})-" % (source_label, source_name)
	for i in range(len(relationship_label_list) - 1):
		if i == node_of_interest_position:
			query += "[:%s]-(n:%s)-" % (relationship_label_list[i], node_label_list[i])
		else:
			query += "[:%s]-(:%s)-" % (relationship_label_list[i], node_label_list[i])
	query += "[:%s]-(t:%s) " % (relationship_label_list[-1], target_label)
	query += "RETURN t.rtx_name, count(distinct n.rtx_name), collect(distinct n.rtx_name)"
	if debug:
		return query
	else:
		result = session.run(query)
		result_list = [i for i in result]
		names2counts = dict()
		names2nodes = dict()
		for i in result_list:
			names2counts[i['t.rtx_name']] = int(i['count(distinct n.rtx_name)'])
			names2nodes[i['t.rtx_name']] = i['collect(distinct n.rtx_name)']
		return names2counts, names2nodes

def count_nodes_of_type_for_nodes_that_connect_to_label(source_name, source_label, target_label, node_label_list, relationship_label_list, node_of_interest_position, debug=False, session=session):
	"""
	This function will take a source node, get all the target nodes of node_label type that connect to the source via node_label_list
	and relationship_label list, it then takes each target node, and counts the number of nodes of type node_label_list[node_of_interest] that are connected to the target.
	An example cypher result is:
	MATCH (t:disease)-[:has_phenotype]-(n:phenotypic_feature) WHERE (:disease{rtx_name:'DOID:8398'})-[:has_phenotype]-(:phenotypic_feature)-[:has_phenotype]-(t:disease) RETURN t.rtx_name, count(distinct n.name)
	which will return
	DOID:001	18
	DOID:002	200
	which means that DOID:001 and DOID:002 both are connected to the source, and DOID:001 has 18 phenotypes, DOID:002 has 200 phenotypes.
	:param source_name: source node name
	:param source_label: source node label
	:param target_label: target node label
	:param node_label_list: list of node labels (eg. ['phenotypic_feature'])
	:param relationship_label_list: list of relationship types (eg. ['has_phenotype', 'has_phenotype'])
	:param node_of_interest_position: position of node to count (in this eg, node_of_interest_position = 0)
	:param debug: just print the cypher query
	:param session: neo4j session
	:return: dict: names2counts, (keys = target node names, values = number of nodes of interest connected to target)
	"""
	temp_rel_list = list(reversed(relationship_label_list))
	temp_node_list = list(reversed(node_label_list))
	query = " MATCH (:%s{rtx_name:'%s'})-" % (source_label, source_name)
	for i in range(len(relationship_label_list) - 1):
		query += "[:%s]-(:%s)-" % (relationship_label_list[i], node_label_list[i])
	query += "[:%s]-(t:%s) " % (relationship_label_list[-1], target_label)
	query += "with distinct t as t "
	query += "MATCH (t:%s)" % (target_label)
	for i in range(len(relationship_label_list) - 1):
		if i == node_of_interest_position:
			query += "-[:%s]-(n:%s)" % (temp_rel_list[i], temp_node_list[i])
			break
		else:
			query += "-[:%s]-(:%s)" % (temp_rel_list[i], temp_node_list[i])

	query += " RETURN t.rtx_name, count(distinct n.rtx_name)"
	if debug:
		return query
	else:
		result = session.run(query)
		result_list = [i for i in result]
		names2counts = dict()
		for i in result_list:
			names2counts[i['t.rtx_name']] = int(i['count(distinct n.rtx_name)'])
		return names2counts

def interleave_nodes_and_relationships(session, source_node, source_node_label, target_node, target_node_label, max_path_len=3, debug=False):
	"""
	Given fixed source source_node and fixed target target_node, returns a list consiting of the types of relationships and nodes
	in the path between the source and target
	:param session: neo4j-driver session
	:param source_node: source source_node OMIM:1234
	:param target_node: target target_node DOID:1234
	:param max_path_len: maximum path length to search over
	:param debug: if you just want the query to be returned
	:return: a list of lists of relationship and node types (strings) linking the source and target
	"""
	query_name = "match p= shortestPath((s:%s)-[*1..%d]-(t:%s)) " \
				 "where s.rtx_name='%s' " \
				 "and t.rtx_name='%s' " \
				 "with nodes(p) as ns, rels(p) as rs, range(0,length(nodes(p))+length(rels(p))-1) as idx " \
				 "return [i in idx | case i %% 2 = 0 when true then coalesce((ns[i/2]).rtx_name, (ns[i/2]).title) else type(rs[i/2]) end] as path " \
				 "" % (source_node_label, max_path_len, target_node_label ,source_node, target_node)
	query_type = "match p= shortestPath((s:%s)-[*1..%d]-(t:%s)) " \
				 "where s.rtx_name='%s' " \
				 "and t.rtx_name='%s' " \
				 "with nodes(p) as ns, rels(p) as rs, range(0,length(nodes(p))+length(rels(p))-1) as idx " \
				 "return [i in idx | case i %% 2 = 0 when true then coalesce(labels(ns[i/2])[1], (ns[i/2]).title) else type(rs[i/2]) end] as path " \
				 "" % (source_node_label, max_path_len, target_node_label, source_node, target_node)
	if debug:
		return query_name, query_type
	res_name = session.run(query_name)
	res_name = [item['path'] for item in res_name]
	res_type = session.run(query_type)
	res_type = [item['path'] for item in res_type]
	return res_name, res_type


def get_results_object_model(target_node, paths_dict, name_to_description, q1_doid_to_disease, probs=False):
	"""
	Returns pathway results as an object model
	:param target_node: target_node DOID:1234
	:param paths_dict: a dictionary (keys OMIM id's) with values (path_name,path_type)
	:param name_to_description: a dictionary to translate between source_node and genetic condition name
	:param q1_doid_to_disease:  a dictionary to translate between target_node and disease name
	:param probs: optional probability of the OMIM being the right one
	:return: ``dict``
	"""

	ret_obj = dict()

	source_node_list = paths_dict.keys()
	if len(source_node_list) > 0:
		if target_node in q1_doid_to_disease:
			doid_name = q1_doid_to_disease[target_node]
		else:
			doid_name = target_node
		ret_obj['target_disease'] = doid_name
		ret_source_nodes_dict = dict()
		ret_obj['source_genetic_conditions'] = ret_source_nodes_dict
		source_node_names = []
		for source_node in source_node_list:
			if source_node in name_to_description:
				source_node_names.append(name_to_description[source_node])
			else:
				source_node_names.append(source_node)
		for source_node in source_node_list:
			source_node_dict = {}

			path_names, path_types = paths_dict[source_node]
			if len(path_names) == 1:
				path_list = []
				path_list.append({'type': 'node',
								  'name': source_node,
								  'desc': name_to_description.get(source_node, '')})
				path_names = path_names[0]
				path_types = path_types[0]
				for index in range(1, len(path_names) - 1):
					if index % 2 == 1:
						path_list.append({'type': 'rel',
										  'name': path_types[index]})
					else:
						path_list.append({'type': 'node',
										  'name': path_names[index],
										  'desc': get_node_property(path_names[index], 'name')})
				path_list.append({'type': 'node',
								  'name': target_node,
								  'desc': q1_doid_to_disease.get(target_node, '')})
				if probs:
					if source_node in probs:
						source_node_dict['conf'] = probs[source_node]

				source_node_dict['path'] = path_list
			else:
				# print(to_print)
				if probs:
					if source_node in probs:
						source_node_dict['conf'] = probs[source_node]
				relationships_and_counts_dict = Counter(map(tuple, path_types))
				relationships = list(relationships_and_counts_dict.keys())
				counts = []
				for rel in relationships:
					counts.append(relationships_and_counts_dict[rel])
				relationships_and_counts = []
				for i in range(len(counts)):
					relationships_and_counts.append((relationships[i], counts[i]))
				relationships_and_counts_sorted = sorted(relationships_and_counts, key=lambda tup: tup[1])
				count_list = []
				for index in range(len(relationships_and_counts_sorted)):
					relationship = relationships_and_counts_sorted[index][0]
					count = relationships_and_counts_sorted[index][1]
					count_list.append({'count': count,
									   'reltype': str(relationship)})
				source_node_dict['counts'] = count_list
			ret_source_nodes_dict[source_node] = source_node_dict
	return ret_obj


def weight_graph_with_google_distance(g, context_node_id=None, context_node_descr=None, default_value=10):
	"""
	Creates a new property on the edges called 'gd_weight' that gives the google distance between source/target between that edge
	:param g: a networkx graph
	:return: None (graph properties are updated)
	"""
	descriptions = nx.get_node_attributes(g, 'description')
	curie_id = nx.get_node_attributes(g, 'id')
	labels = nx.get_node_attributes(g, 'labels')
	nodes = list(nx.nodes(g))
	edges = list(nx.edges(g))
	edges2gd = dict()
	for edge in edges:
		source_id = curie_id[edge[0]]
		target_id = curie_id[edge[1]]
		source_descr = descriptions[edge[0]]
		target_descr = descriptions[edge[1]]
		gd = np.inf
		if context_node_id is not None and context_node_descr is not None:
			gd_temp = NormGoogleDistance.get_ngd_for_all([source_id, target_id, context_node_id], [source_descr, target_descr, context_node_descr])
		else:
			gd_temp = NormGoogleDistance.get_ngd_for_all([source_id, target_id], [source_descr, target_descr])
		if not np.isnan(gd_temp):
			if gd_temp < gd:
				gd = gd_temp
		if not np.isinf(gd):
			if gd > default_value:
				gd = default_value
			edges2gd[edge] = gd
		else:
			edges2gd[edge] = default_value  # TODO: check if this default threshold (10) is acceptable

	# decorate the edges with these weights
	#g2 = nx.set_edge_attributes(g, edges2gd)  # This only works if I use the keys of the multigraph, not sure I want that since I'm basing it off source/target
	for u, v, d in g.edges(data=True):
		d['gd_weight'] = edges2gd[(u, v)]


def weight_graph_with_property(g, property, default_value=0, transformation=lambda x: x):
	"""
	Adds a new property to the edges in g
	:param g: networkx graph
	:param property: name of property (eg. 'probability' or 'gd_weight')
	:param default_value: default value for the property to have
	:param transformation: a lambda expression for transforming the property values
	:return: None (changes the graph directly)
	"""
	if property == 'gd_weight':
		weight_graph_with_google_distance(g, default_value=default_value)
		for u, v, d in g.edges(data=True):
			d[property] = transformation(d[property])
	else:
		for u, v, d in g.edges(data=True):
			if property not in d['properties']:
				d[property] = default_value
			else:
				d[property] = transformation(d['properties'][property])


def merge_graph_properties(g, properties_list, new_property_name, operation=lambda x,y: x+y):
	"""
	Takes two or more properties and combines them into a new property
	:param g: networkx graph
	:param properties_list: a list of properties to merge
	:param new_property_name: the new property name it will be called
	:param operation: lambda expression saying how properties should be combined (eg. lambda x,y: x*y)
	:return: None (modifies the graph directly)
	"""
	for u, v, d in g.edges(data=True):
		values = [d[prop] for prop in properties_list]
		d[new_property_name] = functools.reduce(operation, values)


def make_graph_simple(g, directed=False):
	"""
	Makes a multigraph into a simple graph, summing weights if data is different
	:param g: networkx graph weighted with google distance
	:param directed: whether to treat the graph as directed or not
	:return: simple graph (networkx)
	"""
	g_nodes = g.nodes(data=True)
	if directed:
		g_simple = nx.DiGraph()
	else:
		g_simple = nx.Graph()
	for u, v, k, data in g.edges(data=True, keys=True):
		w = data['gd_weight']
		# If the edge already exists in the graph
		if g_simple.has_edge(u, v):
			# check if the data matches in the simple graph
			in_data = g_simple.get_edge_data(u, v)
			# If not, add the edge weights. TODO: this ignores duplicate edges!! Can't get around it though due to path finding algorithm
			if in_data != data:
				g_simple[u][v]['gd_weight'] += w
		else:
			u_node_data = g_nodes[u]
			v_node_data = g_nodes[v]
			g_simple.add_node(u, **u_node_data)
			g_simple.add_node(v, **v_node_data)
			g_simple.add_edge(u, v, **data)
	return g_simple


def get_top_shortest_paths(g, source_name, target_name, k, property='gd_weight', default_value=10):
	"""
	Returns the top k shortest paths through the graph g (which has been weighted with Google distance using
	weight_graph_with_google_distance). This will weight the graph with google distance if it is not already.
	:param g:  Google weighted network x graph
	:param source_name: name of the source node of interest
	:param target_name: name of the target node of interest
	:param k: number of top paths to return
	:return: tuple (top k paths as a list of dictionaries, top k path edges as a list of dictionaries, path_lengths)
	"""
	# Check if the graph has been weighted with google distance
	weighted_flag = False
	for u, v, data in g.edges(data=True):
		if property in data:
			weighted_flag = True
		else:
			weighted_flag = False
		break
	if weighted_flag is False:
		if property == 'gd_weights':
			weight_graph_with_google_distance(g)
		else:
			weight_graph_with_property(g, property, default_value=default_value)
	# Check if the graph is simple or not
	if isinstance(g, nx.MultiDiGraph):
		g_simple = make_graph_simple(g, directed=True)
	elif isinstance(g, nx.MultiGraph):
		g_simple = make_graph_simple(g, directed=False)
	else:
		g_simple = g
	# Map back and forth between nodes and names (this assume names are unique, which they are since they're neo4j keys)
	nodes2names = nx.get_node_attributes(g_simple, 'names')
	names2nodes = dict()
	for node in nodes2names.keys():
		names2nodes[nodes2names[node]] = node
	paths = list(islice(nx.shortest_simple_paths(g_simple, names2nodes[source_name], names2nodes[target_name], weight=property), k))
	#g_simple_nodes = g_simple.nodes(data=True)
	g_simple_nodes = dict()
	for u,d in g_simple.nodes(data=True):
		g_simple_nodes[u] = d
	decorated_paths = []
	for path in paths:
		temp_path = []
		for node in path:
			temp_path.append(g_simple_nodes[node])
		decorated_paths.append(temp_path)
	decorated_path_edges = []
	path_lengths = []
	for path in paths:
		edge_list = []
		path_length = 0
		for i in range(len(path)-1):
			source_node = path[i]
			target_node = path[i+1]
			edge = g_simple.get_edge_data(source_node, target_node)
			path_length += edge[property]
			edge_list.append(edge)
		decorated_path_edges.append(edge_list)
		path_lengths.append(path_length)
	return decorated_paths, decorated_path_edges, path_lengths

def cohd_ngd(node_descr1, node_descr2):
	"""
	This function will return the normalized google distance between terms based on the columbia open health
	data (cohd.nsides.io)
	:param node_descr1: human readable name of a node (eg. naproxen)
	:param node_descr2: human readable name of a node (eg. hypertension)
	:return: float
	"""

def cohd_pair_frequency(node_descr1, node_descr2):
	"""
	This function returns node co-occurance based on columbia open health data
	:param node_descr1: human readable name of a node (eg. naproxen)
	:param node_descr2:
	:return:
	"""
	# First, get all the concept IDs, select an exact match if it's in there
	concept_ids_list1 = QueryCOHD.find_concept_ids(node_descr1)
	concept_id1 = None
	for res in concept_ids_list1:
		if res['concept_name'].lower() == node_descr1.lower():
			concept_id1 = res['concept_id']
			concept_ids_list1 = [res]  # discard the rest of them
			break

	concept_ids_list2 = QueryCOHD.find_concept_ids(node_descr2)
	concept_id2 = None
	for res in concept_ids_list2:
		if res['concept_name'].lower() == node_descr2.lower():
			concept_id2 = res['concept_id']
			concept_ids_list2 = [res]  # discard the rest of them
			break

	# If I found unique concept ids for both, go ahead and return them
	if concept_id1 is not None and concept_id2 is not None:
		paired_concept_freq = QueryCOHD.get_paired_concept_freq(concept_id1, concept_id2)
		return paired_concept_freq

	#otherwise, sum up the counts and frequencies
	count = 0
	freq = 0
	for res1 in concept_ids_list1:
		id1 = res1['concept_id']
		for res2 in concept_ids_list2:
			id2 = res2['concept_id']
			paired_concept_freq = QueryCOHD.get_paired_concept_freq(id1, id2)
			if paired_concept_freq:
				if "concept_count" in paired_concept_freq and "concept_frequency" in paired_concept_freq:
					if isinstance(paired_concept_freq["concept_count"], int) and isinstance(paired_concept_freq["concept_frequency"], float):
						count += paired_concept_freq["concept_count"]
						freq += paired_concept_freq["concept_frequency"]
	paired_concept_freq = dict()
	paired_concept_freq["concept_count"] = count
	paired_concept_freq["concept_frequency"] = freq
	return paired_concept_freq


def weight_graph_with_cohd_frequency(g, default_value=0, normalized=False):
	"""
	Weight a graph with the cohd frequency data
	:param g: networkx graph
	:param default_value: default value for the property
	:param normalized: if you want the results to all sum to 1 or not
	:return: None (modifies graph directly)
	"""
	descriptions = nx.get_node_attributes(g, 'description')
	names = nx.get_node_attributes(g, 'names')
	labels = nx.get_node_attributes(g, 'labels')
	nodes = list(nx.nodes(g))
	edges = list(nx.edges(g))
	edges2freq = dict()
	for edge in edges:
		source_id = names[edge[0]]
		target_id = names[edge[1]]
		source_descr = descriptions[edge[0]]
		target_descr = descriptions[edge[1]]
		res = cohd_pair_frequency(source_descr, target_descr)
		if res:
			if "concept_frequency" in res:
				if isinstance(res["concept_frequency"], float):
					freq = res["concept_frequency"]
				else:
					freq = default_value
			else:
				freq = default_value
		else:
			freq = default_value
		edges2freq[edge] = freq

	if normalized:
		total = float(np.sum(list(edges2freq.values())))
		if total > 0:
			for key in edges2freq.keys():
				edges2freq[key] = edges2freq[key] / total

	# decorate the edges with these weights
	for u, v, d in g.edges(data=True):
		d['cohd_freq'] = edges2freq[(u, v)]





############################################################################################
# Stopping point 3/22/18 DK





def display_results_str(doid, paths_dict, probs=False):
	"""
	Format the results in a pretty manner
	:param doid: souce doid DOID:1234
	:param paths_dict: a dictionary (keys OMIM id's) with values (path_name,path_type)
	:param omim_to_genetic_cond: a dictionary to translate between omim and genetic condition name
	:param q1_doid_to_disease:  a dictionary to translate between doid and disease name
	:param probs: optional probability of the OMIM being the right one
	:return: none (just prints to screen)
	"""
	to_print = ''
	omim_list = paths_dict.keys()
	if len(omim_list) > 0:
		#if doid in q1_doid_to_disease:
		#	doid_name = q1_doid_to_disease[doid]
		#else:
		#	doid_name = doid
		doid_name = get_node_property(doid, 'name')
		omim_names = []
		for omim in omim_list:
			#if omim in omim_to_genetic_cond:
			#	omim_names.append(omim_to_genetic_cond[omim])
			#else:
			#	omim_names.append(omim)
			omim_name = get_node_property(omim, 'name')
			omim_names.append(omim_name)
		ret_str = "Possible genetic conditions that protect against {doid_name}: ".format(doid_name=doid_name) + str(omim_names) + '\n'
		for omim in omim_list:
			#if omim in omim_to_genetic_cond:
			to_print += "The proposed mechanism of action for %s (%s) is: " % (get_node_property(omim, 'name'), omim)
			#else:
			#	to_print += "The proposed mechanism of action for %s is: " % omim
			path_names, path_types = paths_dict[omim]
			if len(path_names) == 1:
				path_names = path_names[0]
				path_types = path_types[0]
				#if omim in omim_to_genetic_cond:
				#	to_print += "(%s)" % (omim_to_genetic_cond[omim])
				#else:
				#to_print += "(%s:%s)" % (path_types[0], path_names[0])
				to_print += "(%s:%s)" % (omim, get_node_property(omim, 'name'))
				for index in range(1, len(path_names) - 1):
					if index % 2 == 1:
						to_print += "--[%s]-->" % (path_types[index])
					else:
						#to_print += "(%s:%s:%s)" % (node_to_description(path_names[index]), path_names[index], path_types[index])
						to_print += "(%s:%s:%s)" % (get_node_property(path_names[index], "name"), path_names[index], get_node_property(path_names[index], 'label'))
				#if doid in q1_doid_to_disease:
				#	to_print += "(%s). " % q1_doid_to_disease[doid]
				#else:
				#to_print += "(%s:%s). " % (path_names[-1], path_types[-1])
				to_print += "(%s:%s:%s). " % (path_names[-1], get_node_property(path_names[-1], 'name'), get_node_property(path_names[-1], 'label'))
				if probs:
					if omim in probs:
						to_print += "Confidence: %f" % probs[omim]
				to_print += '\n'
			else:
				to_print += '\n'
				if probs:
					if omim in probs:
						to_print += "With confidence %f, the mechanism is one of the following paths: " % probs[omim] + '\n'
				relationships_and_counts_dict = Counter(map(tuple, path_types))
				relationships = list(relationships_and_counts_dict.keys())
				counts = []
				for rel in relationships:
					counts.append(relationships_and_counts_dict[rel])
				relationships_and_counts = []
				for i in range(len(counts)):
					relationships_and_counts.append((relationships[i], counts[i]))
				relationships_and_counts_sorted = sorted(relationships_and_counts, key=lambda tup: tup[1])
				for index in range(len(relationships_and_counts_sorted)):
					relationship = relationships_and_counts_sorted[index][0]
					count = relationships_and_counts_sorted[index][1]
					to_print = "%d. " % (index + 1)
					to_print += ("There were %d paths of the form " % count) + str(relationship) + '\n'
	else:
		name = get_node_property(doid, 'description')
		#if doid in q1_doid_to_disease:
		#	name = q1_doid_to_disease[doid]
		#else:
		#	name = doid
		to_print = "Sorry, I was unable to find a genetic condition that protects against {name}".format(name=name) + '\n'
	return to_print


def refine_omims_graph_distance(source_names, source_label, target_name, target_label, directed=False, max_path_len=3, verbose=False):
	"""
	take an omim list and subset it to consist of those that have low expected graph distance (according to
	a random walk
	:param omims: list of omims
	:param doid: target DOID
	:param directed: treat the graph as directed or not
	:param max_path_len: maximum path length to consider
	:param verbose: display help messages or not
	:return: a list consisting of a subset of omims
	"""
	# Computing expected graph distance
	exp_graph_distance_s_t = []  # source to target
	exp_graph_distance_t_s = []  # target to source
	for source_name in source_names:
		o_to_do, d_to_o = expected_graph_distance(source_name, source_label, target_name, target_label, directed=directed, max_path_len=max_path_len)
		exp_graph_distance_s_t.append(o_to_do)
		exp_graph_distance_t_s.append(d_to_o)
	s_t_np = np.array(exp_graph_distance_s_t)  # convert to numpy array, source to target
	# prioritize short paths
	omim_exp_distances = list()
	for i in range(len(source_names)):
		omim_exp_distances.append((source_names[i], s_t_np[i]))
	# Selecting relevant genetic diseases
	# get the non-zero, non-inf graph distance OMIMS, select those that are close to the median, sort them, store them
	non_zero_distances = s_t_np[np.where((s_t_np > 0) & (s_t_np < float("inf")))]
	distance_mean = np.mean(non_zero_distances)  # mean distance
	distance_median = np.median(non_zero_distances)  # median distance
	distance_std = np.std(non_zero_distances)  # standard deviation
	# to_select = np.where(s_t_np < distance_mean+distance_std)[0]  # those not more than 1*\sigma above the mean
	if directed:  # if it's directed, then we want short paths
		to_select = np.where(s_t_np <= distance_median)[0]
	else:  # if it's undirected, we want long paths (since that implies high connectivity (lots of paths between source
		# and target)
		to_select = np.where(s_t_np >= distance_median)[0]
	prioritized_omims_and_dist = list()
	for index in to_select:
		prioritized_omims_and_dist.append((source_names[index], s_t_np[index]))
	prioritized_omims_and_dist_sorted = sorted(prioritized_omims_and_dist, key=lambda tup: tup[1])
	prioritized_omims = list()
	for omim, dist in prioritized_omims_and_dist_sorted:
		prioritized_omims.append(omim)
	if verbose:
		print("Found %d omims nearby (according to the random walk)" % len(prioritized_omims))
	return prioritized_omims


def refine_omims_well_studied(omims, doid, omim_to_mesh, q1_doid_to_mesh, verbose=False):
	"""
	Subset given omims to those that are well studied (have low google distance between the source
	omim mesh name and the target doid mesh name
	:param omims:
	:param doid:
	:param omim_to_mesh:
	:param q1_doid_to_mesh:
	:param verbose:
	:return:
	"""
	# Getting well-studied omims
	omims_GD = list()
	for omim in omims:  # only the on the prioritized ones
		omim_descr = get_node_property(omim, "name", node_label="disease")
		doid_descr = get_node_property(doid, "name", node_label="disease")
		res = NormGoogleDistance.get_ngd_for_all([omim, doid], [omim_descr, doid_descr])
		omims_GD.append((omim, res))
	well_studied_omims = list()
	for tup in omims_GD:
		if tup[1] != math.nan and tup[1] > 0:
			well_studied_omims.append(tup)
	well_studied_omims = [item[0] for item in sorted(well_studied_omims, key=lambda tup: tup[1])]
	if verbose:
		print("Found %d well-studied omims" % len(well_studied_omims))
	# print(well_studied_omims)
	return well_studied_omims


def refine_omims_Markov_chain(omim_list, doid, max_path_len=3, verbose=False):
	"""
	Subset an omim_list to be only those for which there is a high probability path between
	the omim and the target doid according the Markov chain model
	:param omim_list: input list of source omims
	:param doid: target doid
	:param max_path_len: how many hops we want to go looking for a path between the source and target
	:return: tuple
	1. subseted omim list,
	2. dictionary with keys=omim_subset_list and values=the path names and types,
	3. a dictionary with keys=omim_subset_list and values=the probabilities given by the Markov chain
	"""
	# Select likely paths and report them
	trained_MC, quad_to_matrix_index = MarkovLearning.trained_MC()  # initialize the Markov chain
	paths_dict_prob_all = dict()
	paths_dict_selected = dict()
	# get the probabilities for each path
	for omim in omim_list:
		path_name, path_type = interleave_nodes_and_relationships(session, omim, "disease", doid, "disease", max_path_len=max_path_len)
		probabilities = []
		for path in path_type:
			prob = MarkovLearning.path_probability(trained_MC, quad_to_matrix_index, path)
			probabilities.append(prob)
		total_prob = np.sum(
			probabilities)  # add up all the probabilities of all paths TODO: could also take the mean, etc.
		# Only select the relevant paths
		prob_np = np.array(probabilities)
		prob_np /= np.sum(prob_np)  # normalize TODO: see if we should leave un-normalized
		prob_np_mean = np.mean(prob_np)
		to_select = np.where(prob_np >= prob_np_mean)[0]  # select ones above the mean
		selected_probabilities = prob_np[to_select]
		selected_path_name = []
		selected_path_type = []
		for index in to_select:
			selected_path_name.append(path_name[index])
			selected_path_type.append(path_type[index])
		paths_dict_prob_all[omim] = (selected_path_name, selected_path_type, total_prob)

	# now select which omims I actually want to display
	omim_probs = []
	for omim in omim_list:
		omim_probs.append(paths_dict_prob_all[omim][2])
	omim_probs_np = np.array(omim_probs)
	total = np.sum(omim_probs_np)
	omim_probs_np /= total
	omim_probs_np_mean = np.mean(omim_probs_np)
	to_select = np.where(omim_probs_np >= omim_probs_np_mean)[0]  # TODO: see if we should leave un-normalized
	# to_select = np.where(omim_probs_np > 0)[0]
	selected_probs = dict()
	selected_omims = []
	for index in to_select:
		selected_omim = omim_list[index]
		selected_omims.append(selected_omim)
		path_name, path_type, prob = paths_dict_prob_all[selected_omim]
		selected_probs[selected_omim] = prob  # /float(1.5*total)
		paths_dict_selected[selected_omim] = (path_name, path_type)

	if verbose:
		print("Found %d omims (according to the Markov chain model)" % len(selected_omims))
	return selected_omims, paths_dict_selected, selected_probs

###################################################################
# Tests

def test_get_node_names_of_type_connected_to_target():
	res = get_node_names_of_type_connected_to_target("disease", "DOID:14793", "protein", max_path_len=1, direction="u")
	assert res == ['Q92838']
	res = get_node_names_of_type_connected_to_target("disease", "DOID:14793", "protein", max_path_len=1,direction="f")
	assert res == []
	res = get_node_names_of_type_connected_to_target("disease", "DOID:14793", "protein", max_path_len=1, direction="r")
	assert res == ['Q92838']
	res = get_node_names_of_type_connected_to_target("disease", "DOID:14793", "disease", max_path_len=2, direction="u")
	assert set(res) == set(['OMIM:305100','OMIM:313500'])

def test_get_node_property():
	res = get_node_property("DOID:14793", "description")
	assert res == 'hypohidrotic ectodermal dysplasia'
	res = get_node_property("DOID:14793", "description", "disease")
	assert res == 'hypohidrotic ectodermal dysplasia'
	res = get_node_property("UBERON:0001259", "description")
	assert res == 'mucosa of urinary bladder'
	res = get_node_property("UBERON:0001259", "description", "anatomical_entity")
	assert res == 'mucosa of urinary bladder'
	res = get_node_property("DOID:13306", "description")
	assert res == 'diphtheritic cystitis'
	res = get_node_property("DOID:13306", "expanded")
	assert res == False
	res = get_node_property("metolazone", "label")
	assert res == 'drug'


def test_get_one_hop_target():
	res = get_one_hop_target("disease", "DOID:14793", "protein", "associated_with_condition")
	assert res == ["Q92838"]
	res = get_one_hop_target("drug", "carbetocin", "protein", "directly_interacts_with")
	assert res == ["P30559"]


def test_get_relationship_types_between():
	res = get_relationship_types_between("DOID:0110307","disease","DOID:1798","disease",max_path_len=5)
	known_result = [(['subset_of', 'has_phenotype', 'has_phenotype'], 40), (['subset_of', 'associated_with_condition', 'associated_with_condition'], 2)]
	for tup in res:
		assert tup in known_result
	for tup in known_result:
		assert tup in res

	res = get_relationship_types_between("benzilonium","drug","DOID:14325","disease",max_path_len=5)
	known_result = [(['directly_interacts_with', 'regulates', 'associated_with_condition', 'subset_of'], 10), (['directly_interacts_with', 'regulates', 'associated_with_condition', 'subset_of'], 7)]
	for tup in res:
		assert tup in known_result
	for tup in known_result:
		assert tup in res


def test_get_graph():
	query = 'match p=(s:disease{rtx_name:"DOID:14325"})-[*1..3]-(t:drug) return p limit 10'
	res = cypher.run(query, conn=connection, config=defaults)
	graph = get_graph(res)
	nodes = set(['138403', '148895', '140062', '140090', '139899', '140317', '138536', '121114', '138632', '147613', '140300', '140008', '140423'])
	edges = set([('138403', '121114', 0), ('148895', '147613', 0), ('148895', '147613', 1), ('148895', '147613', 2), ('148895', '147613', 3), ('148895', '147613', 4), ('148895', '147613', 5), ('148895', '147613', 6), ('148895', '147613', 7), ('148895', '147613', 8), ('148895', '147613', 9), ('140062', '121114', 0), ('140090', '121114', 0), ('139899', '121114', 0), ('140317', '121114', 0), ('138536', '121114', 0), ('121114', '148895', 0), ('121114', '148895', 1), ('121114', '148895', 2), ('121114', '148895', 3), ('121114', '148895', 4), ('121114', '148895', 5), ('121114', '148895', 6), ('121114', '148895', 7), ('121114', '148895', 8), ('121114', '148895', 9), ('138632', '121114', 0), ('140300', '121114', 0), ('140008', '121114', 0), ('140423', '121114', 0)])
	assert set(graph.nodes) == nodes
	assert set(graph.edges) == edges


def test_return_subgraph_through_node_labels():
	g = return_subgraph_through_node_labels('naproxen', 'drug', 'UBERON:0001474', 'anatomical_entity',
										['protein'], directed=False)
	nodes = dict()
	for v, data in g.nodes(data=True):
		nodes[v] = data
	names = [v['names'] for v in nodes.values()]
	assert 'naproxen' in names
	assert 'UBERON:0001474' in names
	assert 'P37231' in names


def test_weight_graph_with_google_distance():
	g = return_subgraph_through_node_labels('naproxen', 'drug', 'UBERON:0001474', 'anatomical_entity',
											['protein'], directed=False)
	for u, v, k, data in g.edges(data=True, keys=True):
		assert 'gd_weight' not in data
	weight_graph_with_google_distance(g)
	for u, v, k, data in g.edges(data=True, keys=True):
		assert 'gd_weight' in data
		w = data['gd_weight']
		assert w is not None
		assert np.isfinite(w)


def test_get_top_shortest_paths():
	g = return_subgraph_through_node_labels('naproxen', 'drug', 'UBERON:0001474', 'anatomical_entity',
											['protein'], directed=False)
	node_paths, edge_paths, lengths = get_top_shortest_paths(g, 'naproxen', 'UBERON:0001474', 1)
	for path in node_paths:
		assert 'naproxen' == path[0]['names']
		assert 'UBERON:0001474' == path[-1]['names']
	for path_length in lengths:
		assert np.isfinite(path_length)


def test_suite():
	test_get_node_names_of_type_connected_to_target()
	test_get_node_property()
	test_get_one_hop_target()
	test_get_relationship_types_between()
	test_return_subgraph_through_node_labels()
	test_weight_graph_with_google_distance()
	test_get_top_shortest_paths()
