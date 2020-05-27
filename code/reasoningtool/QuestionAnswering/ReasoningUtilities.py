# This script will contain a bunch of utilities that help with graph/path extraction
# Should subsume Q1Utils and Q2Utils
import networkx as nx
from numpy import linalg as LA
import numpy as np
np.warnings.filterwarnings('ignore')
import cypher
import os
import re
import sys
import time
import warnings
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
from collections import Counter
import requests_cache
from itertools import islice
import itertools
import functools
import CustomExceptions
import pickle

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

import fisher_exact


#requests_cache.install_cache('orangeboard')
# specifiy the path of orangeboard database
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
dbpath = os.path.sep.join([*pathlist[:(RTXindex+1)],'data','orangeboard'])
requests_cache.install_cache(dbpath)

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
rtxConfig = RTXConfiguration()

# Connection information for the neo4j server, populated with orangeboard
driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
session = driver.session()

# Connection information for the ipython-cypher package
connection = "http://" + rtxConfig.neo4j_username + ":" + rtxConfig.neo4j_password + "@" + rtxConfig.neo4j_database
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


def node_exists_with_property(term, property_name, node_label=""):
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
	with driver.session() as session:
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
	with driver.session() as session:
		res = session.run(query)

	return res.single()["count(n)"]


def get_random_nodes(label, property="id", num=10, debug=False):
	query = "match (n:%s) with rand() as r, n as n return n.%s order by r limit %d" % (label, property, num)
	if debug:
		return query
	else:
		with driver.session() as session:
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
	with driver.session() as session:
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
	with driver.session() as session:
		res = session.run(query)
	labels = []
	for i in res:
		label = list(set(i["labels(n)"]).difference({"Base"}))  # get rid of the extra base label
		label = label.pop()  # this assumes only a single relationship type, but that's ok since that's how neo4j works
		labels.append(label)
	return labels


def get_full_meta_graph():
	"""
	Get all the node types and the edge types that can connect them in the neo4j database
	:return: dict with all node types and how they can connect
	"""

	#### Try the cache first
	saved_metagraph_file = "apoc.meta.graph.p"
	if os.path.isfile(saved_metagraph_file):
		metagraph = pickle.load(open(saved_metagraph_file,"rb"))
		return(metagraph)

	query = "call apoc.meta.graph"
	with driver.session() as session:
		result = session.run(query)
	metagraph = {}
	for record in result:
		for relationship in record["relationships"]:
			start_name = relationship.start_node.get("name")
			end_name = relationship.end_node.get("name")
			if start_name == "Base" or end_name == "Base":
			  continue
			if start_name not in metagraph:
				metagraph[start_name] = {}
			if end_name not in metagraph[start_name]:
				metagraph[start_name][end_name] = []
			metagraph[start_name][end_name].append(relationship.type)

	#### Store the metagraph as a pickle file
	pickle.dump(metagraph,open(saved_metagraph_file,"wb"))

	return(metagraph)


def get_id_from_property(property_value, property_name, label=None, debug=False):
	"""
	Get a node with property having value property_value
	:param property_value: string
	:param property_name: string (eg. name)
	:return: string
	"""
	if label:
		query = "match (n:%s{%s:'%s'}) return n.id" % (label, property_name, property_value)
	else:
		query = "match (n{%s:'%s'}) return n.id" % (property_name, property_value)
	if debug:
		return query
	with driver.session() as session:
		res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]["n.id"]
	else:
		return None

def get_name_to_description_dict():
	"""
	Create a dictionary of all nodes, keys being the names, items being the descriptions
	:param session: neo4j session
	:return: dictionary of node names and descriptions
	"""
	query = "match (n) return properties(n) as n"
	name_to_descr = dict()
	with driver.session() as session:
		res = session.run(query)
	for item in res:
		item_dict = item['n']
		name_to_descr[item_dict['id']] = item_dict['name']
	return name_to_descr


def get_node_property(name, node_property, node_label="", name_type="id", debug=False):
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
		if debug: return query
		with driver.session() as session:
			record = session.run(query).single()
		if record:
			#return(record.value(key='n.%s' % node_property))
			for key in record.keys():
				if key == "n.%s" % node_property: return(record[key])
		else:
			raise Exception("Node or property not found using query: '%s'" % query)
	else:
		if node_label == "":
			query = "match (n{%s:'%s'}) return labels(n)" % (name_type, name)
		else:
			query = "match (n:%s{%s:'%s'}) return labels(n)" % (node_label, name_type, name)
		if debug: return query
		with driver.session() as session:
			record = session.run(query).single()
		if record:
			#node_types = record.value(key='labels(n)')
			for key in record.keys():
				if key == "labels(n)": node_types = record[key]
			non_base_node_types = list(set(node_types).difference({"Base"}))
			return non_base_node_types.pop()  # TODO: this assumes only a single result is returned
		else:
			raise Exception("Node or property not found using query: '%s'" % query)


def get_node_properties(name, node_label="", name_type="id", debug=False):
	"""
	Get all properties of a node. Eric added this and wonders if it is redundant, but couldn't find equivalent. FIXME
	:param name: name of the node
	:param node_label: (optional) label (type) of node (makes the operation slightly faster)
	:param name_type: (optional) which property to search by (default: id) (but "name" might be appropriate)
	:param session: neo4j session
	:param debug: just return the query
	:return: a string (the description of the node)
	"""
	if node_label == "":
		query = "match (n{%s:'%s'}) return properties(n)" % (name_type, name)
	else:
		query = "match (n:%s{%s:'%s'}) return properties(n)" % (node_label, name_type, name)
	if debug:
		return query
	with driver.session() as session:
		record = session.run(query).single()
	if record:
		#return(record.value(key='properties(n)'))
		for key in record.keys():
			if key == "properties(n)": return(record[key])
	else:
		raise Exception("Node or properties not found using query: '%s'" % query)


# Get node names in paths between two fixed endpoints
def get_node_names_of_type_connected_to_target(source_label, source_name, target_label, max_path_len=4, debug=False, verbose=False, direction="u", is_omim=False):
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
				" WHERE s.id='%s' AND t<>s AND t.id=~'OMIM:.*' WITH distinct nodes(path)[0] as p RETURN p.id" % (
				target_label, max_path_len, source_label, source_name)
	elif direction == "r":
		query = "MATCH path=shortestPath((t:%s)-[*1..%d]->(s:%s))" \
				" WHERE s.id='%s' AND t<>s WITH distinct nodes(path)[0] as p RETURN p.id" % (target_label, max_path_len, source_label, source_name)
	elif direction == "f":
		query = "MATCH path=shortestPath((t:%s)<-[*1..%d]-(s:%s))" \
				" WHERE s.id='%s' AND t<>s WITH distinct nodes(path)[0] as p RETURN p.id" % (
				target_label, max_path_len, source_label, source_name)
	elif direction == "u":
		query = "MATCH path=shortestPath((t:%s)-[*1..%d]-(s:%s))" \
				" WHERE s.id='%s' AND t<>s WITH distinct nodes(path)[0] as p RETURN p.id" % (target_label, max_path_len, source_label, source_name)
	else:
		raise Exception("Sorry, the direction must be one of 'f', 'r', or 'u'")
	if debug:
		return query
	with driver.session() as session:
		result = session.run(query)
	result_list = [i for i in result]
	names = [i['p.id'] for i in result_list]
	if verbose:
		print("Found %d nearby %s's" % (len(names), target_label))
	if debug:
		return names, query
	else:
		return names

def get_nodes_that_match_in_list(node_id_list, node_label):
	query = "match (n:%s) where n.id in " % node_label
	if node_id_list:
		query += "["
	for label in node_id_list:
		query += '"%s",' % label
	if node_id_list:
		query = query[:-1]
		query += "]"
	query += " return collect(n.id)"
	with driver.session() as session:
		res = session.run(query)
	return [i for i in res]

def get_one_hop_target(source_label, source_name, target_label, edge_type, debug=False, verbose=False, direction="u"):
	"""
	This function finds all target nodes connected in one hop to a source node (with a given edge type). EG: what proteins does drug X target?
	:param source_label: kind of source node (eg: disease)
	:param source_name: actual name of the source node (eg: DOID:14793)
	:param target_label: kind of target nodes to look for (eg: disease)
	:param edge_type: Type of edge to be interested in (eg: physically_interacts_with, affects)
	:param debug: flag indicating if the query should also be returned
	:param direction: Which direction to look (u: undirected, f: source->target, r: source<-target
	:param session: neo4j server session
	:return: list of omim ID's
	"""
	if direction == "r":
		query = "MATCH path=(s:%s{id:'%s'})<-[:%s]-(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.id" % (source_label, source_name, edge_type, target_label)
	elif direction == "f":
		query = "MATCH path=(s:%s{id:'%s'})-[:%s]->(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.id" % (
				source_label, source_name, edge_type, target_label)
	elif direction == "u":
		query = "MATCH path=(s:%s{id:'%s'})-[:%s]-(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.id" % (
				source_label, source_name, edge_type, target_label)
	else:
		raise Exception("Sorry, the direction must be one of 'f', 'r', or 'u'")
	with driver.session() as session:
		result = session.run(query)
	result_list = [i for i in result]
	names = [i['p.id'] for i in result_list]
	if verbose:
		print("Found %d nearby %s's" % (len(names), target_label))
	if debug:
		return names, query
	else:
		return names


def get_relationship_types_between(source_name, source_label, target_name, target_label, max_path_len=4, debug=False):
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
		query = "match (s:%s{id:'%s'})-[r]-(t:%s) return distinct type(r)" % (source_label, source_name, target_label)
		if debug:
			return query
		else:
			with driver.session() as session:
				res = session.run(query)
			res = [i["type(r)"] for i in res]
			return res
	elif max_path_len == 1 and not source_name and not target_name and not target_label:
		query = "match (s:%s)-[r]-(t) return distinct type(r)" % (source_label)
		if debug:
			return query
		else:
			with driver.session() as session:
				res = session.run(query)
			res = [i["type(r)"] for i in res]
			return res
	elif max_path_len == 1 and not source_name and not target_name:
		query = "match (s:%s)-[r]-(t:%s) return distinct type(r)" % (source_label, target_label)
		if debug:
			return query
		else:
			with driver.session() as session:
				res = session.run(query)
			res = [i["type(r)"] for i in res]
			return res
	else:
		query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]-(t:%s)) " \
				"WHERE s.id='%s' AND t.id='%s' " \
				"RETURN distinct extract (rel in relationships(path) | type(rel) ) as types, count(*)" % (source_label, max_path_len, target_label, source_name, target_name)
		with driver.session() as session:
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
			graph.add_node(node['id'], properties=node['properties'], labels=node['labels'], names=node['properties']['id'], description=node['properties']['name'], id=node['properties']['id'])
		for rel in item['relationships']:
			graph.add_edge(rel['startNode'], rel['endNode'], id=rel['id'], properties=rel['properties'], type=rel['type'])
	return graph


def get_graph_from_nodes(id_list, node_property_label="id", debug=False, edges=False):
	"""
	For a list of property names, return a subgraph with those nodes in it
	:param id_list: a list of identifiers
	:param node_property_label: what the identier property is (eg. id)
	:param debug:
	:return:
	"""
	if edges:
		query = "with ['%s'" % id_list[0]
		for node_id in id_list[1:]:
			query += ",'%s'" % node_id
		query += "] as l match p=(n)-[]-(m) where n.%s in l and m.%s in l return p" % (node_property_label, node_property_label)
	else:
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
				"WHERE s.id='%s' AND t.id='%s' " \
				"RETURN path" % (source_node_label, max_path_len, target_node_label, source_node, target_node)
	else:
		query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]-(t:%s)) " \
				"WHERE s.id='%s' AND t.id='%s' " \
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
				query += "WHERE s.id='%s' and t.id='%s' " % (source_node, target_node)
				query += "RETURN path"
			else:
				query = "MATCH path=(s:%s)-" % source_node_label
				for i in range(len(relationship_list) - 1):
					query += "[:" + relationship_list[i] + "]->()-"
				query += "[:" + relationship_list[-1] + "]->" + "(t:%s) " % target_node_label
				query += "WHERE s.id='%s'" % (source_node)
				query += "RETURN path"
			if debug:
				return query
		else:
			if target_node is not None:
				query = "MATCH path=(s:%s)-" % source_node_label
				for i in range(len(relationship_list) - 1):
					query += "[:" + relationship_list[i] + "]-()-"
				query += "[:" + relationship_list[-1] + "]-" + "(t:%s) " % target_node_label
				query += "WHERE s.id='%s' and t.id='%s' " % (source_node, target_node)
				query += "RETURN path"
			else:
				query = "MATCH path=(s:%s)-" % source_node_label
				for i in range(len(relationship_list) - 1):
					query += "[:" + relationship_list[i] + "]-()-"
				query += "[:" + relationship_list[-1] + "]-" + "(t:%s) " % target_node_label
				query += "WHERE s.id='%s'" % (source_node)
				query += "RETURN path"
			if debug:
				return query
	else:  # it's a list of lists
		if directed:
			query = "MATCH (s:%s{id:'%s'}) " % (source_node_label, source_node)
			for rel_index in range(len(relationship_list)):
				rel_list = relationship_list[rel_index]
				query += "OPTIONAL MATCH path%d=(s)-" % rel_index
				for i in range(len(rel_list) - 1):
					query += "[:" + rel_list[i] + "]->()-"
				query += "[:" + rel_list[-1] + "]->" + "(t:%s)" % target_node_label
				query += " WHERE t.id='%s' " % target_node
			query += "RETURN "
			for rel_index in range(len(relationship_list) - 1):
				query += "collect(path%d)+" % rel_index
			query += "collect(path%d)" % (len(relationship_list) - 1)
			if debug:
				return query
		else:
			query = "MATCH (s:%s{id:'%s'}) " % (source_node_label, source_node)
			for rel_index in range(len(relationship_list)):
				rel_list = relationship_list[rel_index]
				query += "OPTIONAL MATCH path%d=(s)-" % rel_index
				for i in range(len(rel_list) - 1):
					query += "[:" + rel_list[i] + "]-()-"
				query += "[:" + rel_list[-1] + "]-" + "(t:%s)" % target_node_label
				query += " WHERE t.id='%s' " % target_node
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
		query = "MATCH path=(%s:%s{id:'%s'})" % (source_node_label, source_node_label, source_node)
		seen_flag = False  # TODO: the node names are not nec. unique, which may cause issues, and ambiguity in with_rel
		for i in range(len(node_list) - 1):
			if with_rel[0] == node_list[i]:
				query += "-[]-(%s:%s)" % (node_list[i], node_list[i])
			elif with_rel[0] == source_node_label and not seen_flag:  # since names used need to be unique, only evaluate at most once
				query += "-[]-(%s:%s)" % (node_list[i], node_list[i])
				seen_flag = True
			else:
				query += "-[]-(:%s)" % node_list[i]
		query += "-[]-(:%s)-[]-(%s:%s{id:'%s'}) " % (node_list[-1], target_node_label, target_node_label, target_node)
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
			query += "WHERE s.id='%s' and t.id='%s' " % (source_node, target_node)
			query += "RETURN path"
		else:
			query = "MATCH path=(s:%s)" % source_node_label
			for i in range(len(node_list) - 1):
				query += "-[]-(:" + node_list[i] + ")"
			query += "-[]-(:" + node_list[-1] + ")-[]-" + "(t:%s) " % target_node_label
			query += "WHERE s.id='%s' and t.id in ['%s'" % (source_node, target_node[0])
			for node in target_node:
				query += ",'%s'" % node
			query += "] "
			query += "RETURN path"
		if debug:
			return query
	else:  # it's a list of lists
		query = "MATCH (s:%s{id:'%s'}) " % (source_node_label, source_node)
		for rel_index in range(len(node_list)):
			rel_list = node_list[rel_index]
			query += "OPTIONAL MATCH path%d=(s)" % rel_index
			for i in range(len(rel_list) - 1):
				query += "-[]-(:" + rel_list[i] + ")"
			query += "-[]-(:" + rel_list[-1] + ")-[]-" + "(t:%s)" % target_node_label
			query += " WHERE t.id='%s' " % target_node
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
			"WHERE s.id='%s' AND t.id='%s' " \
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
		query = "MATCH (n{id:'%s'}) return n" % node_name
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
	query = "MATCH path=(s{id:'%s'})-" % node_list[0]
	for i in range(len(relationship_list) - 1):
		query += "[:" + relationship_list[i] + "]-({id:'%s'})-" % node_list[i+1]
	query += "[:" + relationship_list[-1] + "]-" + "(t{id:'%s'}) " % node_list[-1]
	query += "RETURN path"
	if debug:
		return query

	graph = get_graph(cypher.run(query, conn=connection, config=defaults), directed=directed)
	return graph


def count_nodes_of_type_on_path_of_type_to_label(source_name, source_label, target_label, node_label_list, relationship_label_list, node_of_interest_position, debug=False):
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
	query = "MATCH (s:%s{id:'%s'})-" % (source_label, source_name)
	for i in range(len(relationship_label_list) - 1):
		if i == node_of_interest_position:
			query += "[:%s]-(n:%s)-" % (relationship_label_list[i], node_label_list[i])
		else:
			query += "[:%s]-(:%s)-" % (relationship_label_list[i], node_label_list[i])
	query += "[:%s]-(t:%s) " % (relationship_label_list[-1], target_label)
	query += "RETURN t.id, count(distinct n.id), collect(distinct n.id)"
	if debug:
		return query
	else:
		with driver.session() as session:
			result = session.run(query)
		result_list = [i for i in result]
		names2counts = dict()
		names2nodes = dict()
		for i in result_list:
			names2counts[i['t.id']] = int(i['count(distinct n.id)'])
			names2nodes[i['t.id']] = i['collect(distinct n.id)']
		return names2counts, names2nodes


def count_nodes_of_type_for_nodes_that_connect_to_label(source_name, source_label, target_label, node_label_list, relationship_label_list, node_of_interest_position, debug=False):
	"""
	This function will take a source node, get all the target nodes of node_label type that connect to the source via node_label_list
	and relationship_label list, it then takes each target node, and counts the number of nodes of type node_label_list[node_of_interest] that are connected to the target.
	An example cypher result is:
	MATCH (t:disease)-[:has_phenotype]-(n:phenotypic_feature) WHERE (:disease{id:'DOID:8398'})-[:has_phenotype]-(:phenotypic_feature)-[:has_phenotype]-(t:disease) RETURN t.id, count(distinct n.name)
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
	query = " MATCH (:%s{id:'%s'})-" % (source_label, source_name)
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

	query += " RETURN t.id, count(distinct n.id)"
	if debug:
		return query
	else:
		with driver.session() as session:
			result = session.run(query)
		result_list = [i for i in result]
		names2counts = dict()
		for i in result_list:
			names2counts[i['t.id']] = int(i['count(distinct n.id)'])
		return names2counts


def interleave_nodes_and_relationships(source_node, source_node_label, target_node, target_node_label, max_path_len=3, debug=False):
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
				 "where s.id='%s' " \
				 "and t.id='%s' " \
				 "with nodes(p) as ns, rels(p) as rs, range(0,length(nodes(p))+length(rels(p))-1) as idx " \
				 "return [i in idx | case i %% 2 = 0 when true then coalesce((ns[i/2]).id, (ns[i/2]).title) else type(rs[i/2]) end] as path " \
				 "" % (source_node_label, max_path_len, target_node_label ,source_node, target_node)
	query_type = "match p= shortestPath((s:%s)-[*1..%d]-(t:%s)) " \
				 "where s.id='%s' " \
				 "and t.id='%s' " \
				 "with nodes(p) as ns, rels(p) as rs, range(0,length(nodes(p))+length(rels(p))-1) as idx " \
				 "return [i in idx | case i %% 2 = 0 when true then coalesce(labels(ns[i/2])[1], (ns[i/2]).title) else type(rs[i/2]) end] as path " \
				 "" % (source_node_label, max_path_len, target_node_label, source_node, target_node)
	if debug:
		return query_name, query_type
	with driver.session() as session:
		res_name = session.run(query_name)
	res_name = [item['path'] for item in res_name]
	with driver.session() as session:
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


def transform_graph_weight(g, property, default_value=0, transformation=lambda x: x):
	"""
	Transform an existing graph property, using the default value if it doesn't exist
	:param g: networkx graph
	:param property: the string property name you are trying to transform
	:param default_value: the default value to use for the property
	:param transformation: the lambda function way you want to transform the property
	:return: nothing (modifies the graph in place)
	"""
	for u, v, d in g.edges(data=True):
		if property in d:
			d[property] = transformation(d[property])
		else:
			d[property] = default_value


def weight_graph_with_property(g, property, default_value=0, transformation=lambda x: x):
	"""
	Adds a new property to the edges in g, extracting it from the 'properties' property if necessary (for drug->target binding prob, for ex)
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


def get_top_shortest_paths(g, source_name, target_name, k, num_nodes=None, property='gd_weight', default_value=10, max_check=100):
	"""
	Returns the top k shortest paths through the graph g (which has been weighted with Google distance using
	weight_graph_with_google_distance). This will weight the graph with google distance if it is not already.
	:param g:  Google weighted network x graph
	:param source_name: name of the source node of interest
	:param target_name: name of the target node of interest
	:param k: number of top paths to return
	:param num_nodes: if you want paths of a certain length
	:param max_check: only try these many paths when looking for ones of a certain length
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
	if num_nodes:
		paths = []
		num_tried = 0
		num_found = 0
		for path in nx.shortest_simple_paths(g_simple, names2nodes[source_name], names2nodes[target_name], weight=property):
			if len(path) == num_nodes:
				paths.append(path)
				num_found += 1
			num_tried += 1
			if num_found == k or num_tried > max_check:
				break
	else:
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
	# TODO: finish this


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



def get_networkx_path_weight(g, path, prop):
	"""
	Gets the weight of a networkx path
	:param g: networkx graph
	:param path: a path in the networkx
	:param prop: the property you want to use to compute the weight
	:return:
	"""
	prop_dict = nx.get_edge_attributes(g, prop)
	# iterate over all pairs in the path
	weight = 0
	for first, second in zip(path, path[1:]):
		if (first, second) in prop_dict:
			weight += prop_dict[first, second]
		elif (second, first) in prop_dict:
			weight += prop_dict[second, first]
		else:
			raise Exception("Apparently that wasn't actually a path...")
	return weight


def weight_disease_phenotype_by_cohd(g, max_phenotype_oxo_dist=1, default_value=0):
	"""
	Weights a networkx graph by cohd frequency, specialized to disease/phenotypes
	:param g: networkx graph
	:param max_phenotype_oxo_dist: maximum distance to try and find HP mapping in oxo
	:param default_value: default value to use
	:return: nothing (modifies graph in place)
	"""
	node_properties = nx.get_node_attributes(g, 'properties')
	node_ids = dict()
	node_labels = dict()
	for node in node_properties.keys():
		node_ids[node] = node_properties[node]['id']
		node_labels[node] = node_properties[node]['category']
	for u, v, d in g.edges(data=True):
		source_id = node_ids[u]
		source_label = node_labels[u]
		target_id = node_ids[v]
		target_label = node_labels[v]
		if {source_label, target_label} != {"disease", "phenotypic_feature"}:
			d['cohd_freq'] = default_value
			continue
		else:
			if source_label == "disease":
				disease_id = source_id
				symptom_id = target_id
			else:
				disease_id = target_id
				symptom_id = source_id
		# look up these in COHD
		# disease
		disease_omop_id = None
		for distance in [1, 2, 3]:
			xref = QueryCOHD.get_xref_to_OMOP(disease_id, distance=distance)
			for ref in xref:
				if ref['omop_domain_id'] == "Condition":
					disease_omop_id = str(ref["omop_standard_concept_id"])
					break
			if disease_omop_id:
				break
		# symptom, loop over them all and take the largest
		if not disease_omop_id:
			d['cohd_freq'] = default_value
		else:
			xrefs = QueryCOHD.get_xref_to_OMOP(symptom_id, distance=max_phenotype_oxo_dist)
			freq = 0
			# look for the most frequently appearing xref TODO: could total this if I wanted to
			# TODO: figure out which way is better
			for xref in xrefs:
				symptom_omop_id = str(xref['omop_standard_concept_id'])
				res = QueryCOHD.get_paired_concept_freq(disease_omop_id, symptom_omop_id, dataset_id=1)
				if res:
					temp_freq = res['concept_frequency']
					#if temp_freq > freq:
					#	freq = temp_freq
					freq += temp_freq
				res = QueryCOHD.get_paired_concept_freq(disease_omop_id, symptom_omop_id, dataset_id=2)
				if res:
					temp_freq = res['concept_frequency']
					#if temp_freq > freq:
					#	freq = temp_freq
					freq += temp_freq
			d['cohd_freq'] = freq


def get_sorted_path_weights_disease_to_disease(g, disease_id):
	"""
	Return a sorted list of disease ID's y based on mean path length between disease_id and y weighted by COHD frequency
	:param g: network x graph WEIGHTED BY COHD FREQ 'cohd_freq'
	:param disease_id: id of source node
	:return: list of tuples (id, weight)
	"""
	# get the networkx location of the input disease
	node_properties = nx.get_node_attributes(g, 'properties')
	node_ids = dict()
	node_labels = dict()
	for node in node_properties.keys():
		node_ids[node] = node_properties[node]['id']
		node_labels[node] = node_properties[node]['category']
	disease_networkx_id = None
	for node in node_ids.keys():
		if node_ids[node] == disease_id:
			disease_networkx_id = node

	if not disease_networkx_id:
		raise Exception("Disease node %s does not exist in the graph." % disease_id)

	# get the networkx location of the other diseases
	other_disease_networkx_ids = []
	for node in node_ids.keys():
		if node_labels[node] == "disease":
			if node != disease_networkx_id:
				other_disease_networkx_ids.append(node)

	# get the mean path lengths of all the diseases
	other_disease_median_path_weight = dict()
	for other_disease_networkx_id in other_disease_networkx_ids:
		other_disease_median_path_weight[node_ids[other_disease_networkx_id]] = np.mean(
			[get_networkx_path_weight(g, path, 'cohd_freq') for path in
			 nx.all_simple_paths(g, disease_networkx_id, other_disease_networkx_id, cutoff=2)])

	other_disease_median_path_weight_sorted = []
	for key in other_disease_median_path_weight.keys():
		weight = other_disease_median_path_weight[key]
		other_disease_median_path_weight_sorted.append((key, weight))

	other_disease_median_path_weight_sorted.sort(key=lambda x: x[1], reverse=True)
	return other_disease_median_path_weight_sorted


def get_top_n_most_frequent_from_list(id_list, n):
	"""
	Get the top n most frequently appearing items in the id_list
	:param id_list: a list of entities
	:param n: number to return
	:return: a subset of id_list consisting of the top n most frequently appearing items in id_list
	"""
	id_list_counts_sorted = []
	ids, counts = np.unique(id_list, return_counts=True)
	for i in range(len(ids)):
		id = ids[i]
		count = counts[i]
		id_list_counts_sorted.append((id, count))
	id_list_counts_sorted.sort(key=lambda x: x[1], reverse=True)
	id_list_counts_sorted = id_list_counts_sorted[:n]
	top_n = []
	for id, _ in id_list_counts_sorted:
		top_n.append(id)
	return top_n


def count_paths_of_type_source_fixed_target_free(source_id, source_type, rel_type_node_label_list, debug=False, limit=False):
	"""
	Given a fixed source node, look for targets along rel_type_node_label_list, counting the number of such paths
	for each target found
	:param source_id: id of source node (eg. OMIM:605724)
	:param source_type: type of source node (eg. disease)
	:param rel_type_node_label_list: list of path type to look for. eg.
	[gene_mutations_contribute_to, protein, participates_in, pathway, participates_in, protein, physically_interacts_with, chemical_substance]
	:param debug: just print the cypher command
	:param limit: limit the number of targets (for speed debugging purposes)
	:return: list of tuples the id's of nodes of type rel_type_node_label_list[-1] and values the number of paths
	(of desired kind) connecting source to target.
	 Example: RU.count_paths_of_type_source_fixed_target_free("DOID:8398","disease",["has_phenotype", "phenotypic_feature", "has_phenotype", "protein"], limit=5)
	"""
	path = '(n:%s{id:"%s"})' %(source_type, source_id)
	is_rel = True
	for label in rel_type_node_label_list[:-1]:
		if is_rel:
			path += "-[:%s]" % label
			is_rel = False
		else:
			path += "-(:%s)" % label
			is_rel = True
	path += "-(m:%s)" % rel_type_node_label_list[-1]
	if limit:
		query = "MATCH " + path + " return m.id as ident, count(*) as ct order by ct desc limit %d" % limit
	else:
		query = "MATCH " + path + " return m.id as ident, count(*) as ct order by ct desc"
	if debug:
		return query
	with driver.session() as session:
		res = session.run(query)
	res_list = []
	for item in res:
		res_list.append((item['ident'], item['ct']))
	return res_list



def paths_of_type_source_fixed_target_free_exists(source_id, source_type, rel_type_node_label_list, debug=False, limit=False):
	"""
	Given a fixed source node, look for targets along rel_type_node_label_list, return True iff such paths exist (see above function)
	:param source_id: id of source node (eg. OMIM:605724)
	:param source_type: type of source node (eg. disease)
	:param rel_type_node_label_list: list of path type to look for. eg.
	[gene_mutations_contribute_to, protein, participates_in, pathway, participates_in, protein, physically_interacts_with, chemical_substance]
	:param debug: just print the cypher command
	:param limit: limit the number of targets (for speed debugging purposes)
	:return: True iff such paths exist
	 Example: RU.paths_of_type_source_fixed_target_free_exists("DOID:8398","disease",["has_phenotype", "phenotypic_feature", "has_phenotype", "protein"], limit=5)
	"""
	path = '(n:%s{id:"%s"})' % (source_type, source_id)
	is_rel = True
	for label in rel_type_node_label_list[:-1]:
		if is_rel:
			path += "-[:%s]" % label
			is_rel = False
		else:
			path += "-(:%s)" % label
			is_rel = True
	path += "-(m:%s)" % rel_type_node_label_list[-1]
	if limit:
		query = "MATCH p=" + path + " WITH DISTINCT m AS m limit %d return m.id" % limit
	else:
		query = "MATCH p=" + path + " WITH DISTINCT m AS m return m.id"
	if debug:
		return query
	with driver.session() as session:
		res = session.run(query)
	res_list = []
	for item in res:
		res_list.append(item['m.id'])
	if res_list:
		return True
	else:
		return False


def get_intermediate_node_ids(source_id, source_type, inter_rel_1, inter_type, inter_rel2, target_id, target_type, debug=False):
	"""
	Returns the ID's of the intermediate node type inter_type that are connected via the relationship:
	(source_type{id:"source_id"})-[:inter_rel_1]-(i:inter_type)-[:inter_rel2]-(:target_type{id:"target_id"}) return distinct i.id
	:param source_id: source node id
	:param source_type: source node type
	:param inter_rel_1: relationship type (from source node)
	:param inter_type: intermediate node type
	:param inter_rel2: relationship type (to target node)
	:param target_id: target node id (can be none if you only want to fix the target node type, but not it's id
	:param target_type: target node type
	:return: list of ids of type inter_type
	"""
	if target_id:
		query = 'match (s:%s{id:"%s"})-[:%s]-(i:%s)-[:%s]-(t:%s{id:"%s"}) where s<>t return distinct i.id' % (
			source_type, source_id, inter_rel_1, inter_type, inter_rel2, target_type, target_id)
	else:
		query = 'match (s:%s{id:"%s"})-[:%s]-(i:%s)-[:%s]-(t:%s) where s<>t return distinct i.id' % (
			source_type, source_id, inter_rel_1, inter_type, inter_rel2, target_type)
	if debug:
		return query
	else:
		res_list = []
		with driver.session() as session:
			res = session.run(query)
		for item in res:
			res_list.append(item["i.id"])
		return res_list


def get_subgraph_through_node_sets_known_relationships(node_label_relationship_type_list, list_of_node_id_lists, directed=False, debug=False):
	"""
	Function that extracts a subgraph of a neo4j graph given a list of node labels and relationship types, where the nodes IDs are specified as
	belonging to a given set
	:param node_label_relationship_type_list: list of node labels and relationship types (eg. ["drug", "target", "protein"] can have None entries
	:param list_of_node_id_lists: list of lists to constrain nodes as members of eg. [["drug1", "drug2"], ["protein1","protein2"]] can have None entries
	:param directed: if the networkx graph should be directed or not
	:param debug: just print the cypher command
	:return: networkx graph
	"""
	query = "match path="
	if len(node_label_relationship_type_list) != 2*len(list_of_node_id_lists)-1:
		raise Exception("node_label_relationship_type_list must be equal in length to 2*len(list_of_node_id_lists)-1")
	for i in range(0, len(node_label_relationship_type_list) - 1, 2):
		node_label = node_label_relationship_type_list[i]
		rel_type = node_label_relationship_type_list[i + 1]
		if node_label:
			query += "(n%d:%s)" % (i, node_label)
		else:
			query += "(n%d)" % i
		if rel_type:
			query += "-[r%d:%s]-" % (i, rel_type)
		else:
			query += "-[r%d]-" % i
	# tack on the last guy
	node_label = node_label_relationship_type_list[-1]
	if node_label:
		query += "(n%d:%s)" % (len(node_label_relationship_type_list)-1, node_label)
	else:
		query += "(n%d)" % (len(node_label_relationship_type_list)-1)
	if not all(v is None for v in list_of_node_id_lists):
		query += " where "
		for i in range(len(list_of_node_id_lists)):
			index = 2*i
			id_list = list_of_node_id_lists[i]
			if id_list:
				query += "n%d.id in [" % index
				for id in id_list:
					query += '"%s",' % id
				query = query[:-1]
				query += "] and "
		query = query[:-4]  # drop the last " and"
	##########################################
	# Hacky way to get it to run fast. If you want neo4j to return two lists of different lengths, you get as many rows
	# as is in the longer list (and sometimes a cross product)
	# so do them one at a time, get the unique nodes, then get the unique edges
	query_nodes = query + " unwind nodes(path) as ns with distinct ns as ns return collect(ns)"
	query_edges = query + " unwind relationships(path) as rels with distinct rels as rels return collect(rels)"
	if debug:
		print(query_nodes)
		print(query_edges)
		return
	res_nodes = cypher.run(query_nodes, conn=connection, config=defaults)
	res_edges = cypher.run(query_edges, conn=connection, config=defaults)
	# stick the relationships in the right place
	res_nodes._results.graph[0]['relationships'] = res_edges._results.graph[0]['relationships']
	graph = get_graph(res_nodes, directed=directed)
	return graph
	# end hack
	######################################################
	# query += " unwind nodes(path) as ns unwind relationships(path) as rels with distinct rels as rels, ns as ns return collect(ns) as ns, collect(rels) as rels"
	#if debug:
	#	print(query)
	#else:
	#	res = cypher.run(query, conn=connection, config=defaults)
	#	if not res:
	#		raise CustomExceptions.EmptyCypherError(query)
	#	else:
	#		graph = get_graph(res, directed=directed)
	#		return graph


def top_n_fisher_exact(id_list, id_node_label, target_node_label, rel_type=None, n=10, curie_prefix=None, on_path=None, exclude=None):
	"""
	Performs a fisher exact test
	:param id_list: list of node ids eg. ["DOID:8398","DOID:3222"]
	:param id_node_label: node label of ALL the node in id_list eg. "disease"
	:param target_node_label: target of the fisher test, eg. "phenotypic_feature"
	:param rel_type: optional relationship type to consider, eg. "has_phenotype"
	:param n: Number of results to return
	:param curie_prefix: Optional string specifying the prefix of the curie ID
	:param on_path: None, or a path for which the results need to be on. eg. on_path = ["physically_interacts_with", "chemical_substance"]
	:param exclude: an id to exclude eg. "DOID:1234"
	:return: (dict: keys id's, values p-values, sorted list of identities (in ascending p-values))
	"""
	if rel_type:
		fisher_res = fisher_exact.fisher_exact(id_list, id_node_label, target_node_label, rel_type=rel_type)
	else:
		fisher_res = fisher_exact.fisher_exact(id_list, id_node_label, target_node_label)
	fisher_res_tuples_sorted = []
	for key in fisher_res.keys():
		odds, prob = fisher_res[key]
		fisher_res_tuples_sorted.append((key, prob))
	fisher_res_tuples_sorted.sort(key=lambda x: x[1])
	selected = []
	res_dict = dict()
	num_selected = 0
	for id, prob in fisher_res_tuples_sorted:
		if curie_prefix:
			if id.split(":")[0] == curie_prefix:
				pass
			else:
				continue
		if on_path:
			if paths_of_type_source_fixed_target_free_exists(id, target_node_label, on_path, limit=1):
				pass
			else:
				continue
		if exclude:
			if id == exclude:
				continue
			else:
				pass
		res_dict[id] = prob
		selected.append(id)
		num_selected += 1
		if num_selected >= n:
			break
	return (res_dict, selected)


def does_connect(source_list, source_type, target_type):
	"""
	Answers the questions: Does any of the elements of 'source_list' connect directly to any element of 'target_type'
	:param source_list: list of ids
	:param source_type: label for node of elements in list
	:param target_type: label for node of target
	:return:
	"""
	query = "MATCH (s:%s)-[]-(t:%s)" \
			" WHERE s.id in %s return count(t)" % (
				source_type, target_type, str(source_list))
	with driver.session() as session:
		result = session.run(query)
	out = result.single()["count(t)"]
	if out > 0:
		return 1
	else:
		return 0

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
		path_name, path_type = interleave_nodes_and_relationships(omim, "disease", doid, "disease", max_path_len=max_path_len)
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


def one_hope_neighbors_of_type(g, source_node, node_type, arrow_dir):
	"""
	Given a networx graph g, start at the source_node and return the neighbors of type node_type
	:param g: networkx graph
	:param source_node_id: neo4j node id
	:param node_type: neo4j node type
	:param arrow_dir: 'L' or 'R' depicting arrow direction
	:return: networkx neo4j node id
	"""
	netnodes2id = nx.get_node_attributes(g, 'names')
	netnode2type = nx.get_node_attributes(g, 'labels')
	for key in netnode2type.keys():
		val = set(netnode2type[key]).difference({'Base'}).pop()
		netnode2type[key] = val
	id2netnode = dict()
	for key, val in netnodes2id.items():
		id2netnode[val] = key
	if arrow_dir == 'R':
		neighbor_ids = g.neighbors(id2netnode[source_node])
	elif arrow_dir == 'L':
		neighbor_ids = g.predecessors(id2netnode[source_node])
	else:
		raise Exception("arrow_dir must be one of 'L' or 'R'")
	ret_neighbors = []
	for node in neighbor_ids:
		if netnode2type[node] == node_type:
			ret_neighbors.append(netnodes2id[node])
	return ret_neighbors


def cypher_prop_string(value):
	"""Convert property value to cypher string representation."""
	if isinstance(value, bool):
		return str(value).lower()
	elif isinstance(value, str):
		return f"'{value}'"
	elif isinstance(value, int):
		return f"{value}"
	else:
		raise ValueError(f'Unsupported property type: {type(value).__name__}.')


class NodeReference():
	"""Node reference object."""

	def __init__(self, node):
		"""Create a node reference."""
		node = dict(node)
		name = f'{node.pop("id")}'
		label = node.pop('type', None)
		props = {}

		if label == 'biological_process':
			label = 'biological_process_or_activity'

		curie = node.pop("curie", None)
		if curie is not None:
			if isinstance(curie, str):
				props['id'] = curie
				conditions = ''
			elif isinstance(curie, list):
				conditions = []
				for ci in curie:
					# generate curie-matching condition
					conditions.append(f"{name}.id = '{ci}'")
				# OR curie-matching conditions together
				conditions = ' OR '.join(conditions)
			else:
				raise TypeError("Curie should be a string or list of strings.")
		else:
			conditions = ''

		node.pop('name', None)
		node.pop('set', False)
		props.update(node)

		self.name = name
		self.label = label
		self.prop_string = ' {' + ', '.join([f"`{key}`: {cypher_prop_string(props[key])}" for key in props]) + '}'
		self._conditions = conditions
		self._num = 0

	def __str__(self):
		"""Return the cypher node reference."""
		self._num += 1
		if self._num == 1:
			return f'{self.name}' + \
				   f'{":" + self.label if self.label else ""}' + \
				   f'{self.prop_string}'
		return self.name

	@property
	def conditions(self):
		"""Return conditions for the cypher node reference.

		To be used in a WHERE clause following the MATCH clause.
		"""
		if self._num == 1:
			return self._conditions
		else:
			return ''

class EdgeReference():
	"""Edge reference object."""

	def __init__(self, edge):
		"""Create an edge reference."""
		name = f'{edge["id"]}'
		label = edge['type'] if 'type' in edge else None

		if 'type' in edge and edge['type'] is not None:
			if isinstance(edge['type'], str):
				label = edge['type']
				conditions = ''
			elif isinstance(edge['type'], list):
				conditions = []
				for predicate in edge['type']:
					conditions.append(f'type({name}) = "{predicate}"')
				conditions = ' OR '.join(conditions)
				label = None
		else:
			label = None
			conditions = ''

		self.name = name
		self.label = label
		self._num = 0
		self._conditions = conditions

	def __str__(self):
		"""Return the cypher edge reference."""
		self._num += 1
		if self._num == 1:
			return f'{self.name}{":" + self.label if self.label else ""}'
		else:
			return self.name

	@property
	def conditions(self):
		"""Return conditions for the cypher node reference.

		To be used in a WHERE clause following the MATCH clause.
		"""
		if self._num == 1:
			return self._conditions
		else:
			return ''

class get_cypher_from_question_graph:

	def __init__(self, *args, **kwargs):
		"""Create a question.

		keyword arguments: question_graph or machine_question, knowledge_graph, answers
		"""
		# initialize all properties
		self.natural_question = ''
		self.question_graph = {}
		self.knowledge_graph = None
		self.answers = None

		# apply json properties to existing attributes
		attributes = self.__dict__.keys()
		if args:
			struct = args[0]
			for key in struct:
				if key in attributes:
					setattr(self, key, struct[key])
				elif key == 'machine_question':
					setattr(self, 'question_graph', struct[key])
				else:
					warnings.warn("JSON field {} ignored.".format(key))

		# override any json properties with the named ones
		for key in kwargs:
			if key in attributes:
				setattr(self, key, kwargs[key])
			elif key == 'machine_question':
				setattr(self, 'question_graph', kwargs[key])
			else:
				warnings.warn("Keyword argument {} ignored.".format(key))

		# Added this to remove values
		if 'edges' in self.question_graph:
			for edge in self.question_graph['edges']:
				key_list = list(edge.keys())
				for edge_key in key_list:
					if edge[edge_key] is None:
						edge.pop(edge_key)
					elif edge_key == 'edge_id':
						edge['id'] = edge.pop(edge_key)

		# add ids to question graph edges if necessary ()
		if not any(['id' in e for e in self.question_graph['edges']]):
			for i, e in enumerate(self.question_graph['edges']):
				e['id'] = chr(ord('a') + i)

		# Added this to remove values
		if 'nodes' in self.question_graph:
			for node in self.question_graph['nodes']:
				key_list = list(node.keys())
				for node_key in key_list:
					if node[node_key] is None:
						node.pop(node_key)
					elif node_key == 'node_id':
						node['id'] = node.pop(node_key)

	def cypher_query_fragment_match(self, max_connectivity=0): # cypher_match_string
		'''
		Generate a Cypher query fragment to match the nodes and edges that correspond to a question.

		This is used internally for cypher_query_answer_map and cypher_query_knowledge_graph

		Returns the query fragment as a string.
		'''

		nodes, edges = self.question_graph['nodes'], self.question_graph['edges']

		# generate internal node and edge variable names
		node_references = {n['id']: NodeReference(n) for n in nodes}
		edge_references = [EdgeReference(e) for e in edges]

		match_strings = []

		# match orphaned nodes
		def flatten(l):
			return [e for sl in l for e in sl]
		all_nodes = set([n['id'] for n in nodes])
		all_referenced_nodes = set(flatten([[e['source_id'], e['target_id']] for e in edges]))
		orphaned_nodes = all_nodes - all_referenced_nodes
		for n in orphaned_nodes:
			match_strings.append(f"MATCH ({node_references[n]})")
			if node_references[n].conditions:
				match_strings.append("WHERE " + node_references[n].conditions)

		# match edges
		include_size_constraints = bool(max_connectivity)
		for e, eref in zip(edges, edge_references):
			source_node = node_references[e['source_id']]
			target_node = node_references[e['target_id']]
			has_type = 'type' in e and e['type']
			is_directed = e.get('directed', has_type)
			if is_directed:
				match_strings.append(f"MATCH ({source_node})-[{eref}]->({target_node})")
			else:
				match_strings.append(f"MATCH ({source_node})-[{eref}]-({target_node})")
			conditions = [f'({c})' for c in [source_node.conditions, target_node.conditions, eref.conditions] if c]
			if conditions:
				match_strings.append("WHERE " + " AND ".join(conditions))
				if include_size_constraints:
					match_strings.append(f"AND size( ({target_node})-[]-() ) < {max_connectivity}")
			else:
				if include_size_constraints:
					match_strings.append(f"WHERE size( ({target_node})-[]-() ) < {max_connectivity}")



		match_string = ' '.join(match_strings)
		# logger.debug(match_string)
		return match_string

	def cypher_query_answer_map(self, options=None):
		'''
		Generate a Cypher query to extract the answer maps for a question.

		Returns the query as a string.
		'''

		max_connectivity = 0
		if options and 'max_connectivity' in options:
			max_connectivity = options['max_connectivity']

		match_string = self.cypher_query_fragment_match(max_connectivity)

		nodes, edges = self.question_graph['nodes'], self.question_graph['edges']
		# node_map = {n['id']: n for n in nodes}

		# generate internal node and edge variable names
		node_names = [f"{n['id']}" for n in nodes]
		edge_names = [f"{e['id']}" for e in edges]

		# deal with sets
		node_id_accessor = [f"collect(distinct {n['id']}.id) as {n['id']}" if 'set' in n and n['set'] else f"{n['id']}.id as {n['id']}" for n in nodes]
		edge_id_accessor = [f"collect(distinct toString(id({e['id']}))) as {e['id']}" for e in edges]
		with_string = f"WITH {', '.join(node_id_accessor+edge_id_accessor)}"

		# add bound fields and return map
		answer_return_string = f"RETURN {{{', '.join([f'{n}:{n}' for n in node_names])}}} as nodes, {{{', '.join([f'{e}:{e}' for e in edge_names])}}} as edges"

		# return answer maps matching query
		query_string = ' '.join([match_string, with_string, answer_return_string])
		if options is not None:
			if 'skip' in options:
				query_string += f' SKIP {options["skip"]}'
			if 'limit' in options:
				query_string += f' LIMIT {options["limit"]}'

		return query_string

	def cypher_query_knowledge_graph(self, options=None): #kg_query
		'''
		Generate a Cypher query to extract the knowledge graph for a question.

		Returns the query as a string.
		'''

		max_connectivity = 0
		if options and 'max_connectivity' in options:
			max_connectivity = options['max_connectivity']

		match_string = self.cypher_query_fragment_match(max_connectivity)

		nodes, edges = self.question_graph['nodes'], self.question_graph['edges']

		# generate internal node and edge variable names
		node_names = [f"{n['id']}" for n in nodes]
		edge_names = [f"{e['id']}" for e in edges]

		collection_string = "WITH "
		collection_string += ' + '.join([f'collect(distinct {n})' for n in node_names]) + ' as nodes, '
		if edge_names:
			collection_string += ' + '.join([f'collect(distinct {e})' for e in edge_names]) + ' as edges'
		else:
			collection_string += '[] as edges'
		collection_string += "\nUNWIND nodes as n WITH collect(distinct n) as nodes, edges"
		if edge_names:
			collection_string += "\nUNWIND edges as e WITH nodes, collect(distinct e) as edges"""
		support_string = """WITH
			[r in edges | r{.*, source_id:startNode(r).id, target_id:endNode(r).id, type:type(r), id:toString(id(r))}] as edges,
			[n in nodes | n{.*, type:labels(n)}] as nodes"""
		return_string = 'RETURN nodes, edges'
		query_string = "\n".join([match_string, collection_string, support_string, return_string])

		return query_string

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
	res = get_one_hop_target("disease", "DOID:14793", "protein", "gene_associated_with_condition")
	assert res == ["Q92838"]
	res = get_one_hop_target("drug", "carbetocin", "protein", "physically_interacts_with")
	assert res == ["P30559"]


def test_get_relationship_types_between():
	res = get_relationship_types_between("DOID:0110307","disease","DOID:1798","disease",max_path_len=5)
	known_result = [(['subclass_of', 'has_phenotype', 'has_phenotype'], 40), (['subclass_of', 'gene_associated_with_condition', 'gene_associated_with_condition'], 2)]
	for tup in res:
		assert tup in known_result
	for tup in known_result:
		assert tup in res

	res = get_relationship_types_between("benzilonium","drug","DOID:14325","disease",max_path_len=5)
	known_result = [(['physically_interacts_with', 'regulates', 'gene_associated_with_condition', 'subclass_of'], 10), (['physically_interacts_with', 'regulates', 'gene_associated_with_condition', 'subclass_of'], 7)]
	for tup in res:
		assert tup in known_result
	for tup in known_result:
		assert tup in res


def test_get_graph():
	query = 'match p=(s:disease{id:"DOID:14325"})-[*1..3]-(t:drug) return p limit 10'
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

def test_cypher_gen_one_hop():
	test_graph = {'question_graph':{"edges":[{"id":"e00","source_id":"n00","target_id":"n01","type":"physically_interacts_with"}],"nodes":[{"curie":"CHEMBL.COMPOUND:CHEMBL112","id":"n00","type":"chemical_substance"},{"id":"n01","type":"protein"}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))

def test_cypher_gen_two_hop():
	test_graph = {'knowledge_graph': {'edges': [], 'nodes': [{'id': 'DOID:12365', 'name': 'Ebola hemorrhagic fever', 'type': 'disease'}]}, 'question_graph': {'edges': [{'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'}, {'id': 'e01', 'source_id': 'n01', 'target_id': 'n02'}], 'nodes': [{'curie': 'DOID:12365', 'id': 'n00', 'type': 'disease'}, {'id': 'n01', 'type': 'protein'}, {'id': 'n02', 'type': 'pathway'}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))

def test_cypher_gen_three_hop():
	test_graph = {'knowledge_graph': {'edges': [], 'nodes': [{'id': 'DOID:12365', 'name': 'Ebola hemorrhagic fever', 'type': 'disease'}]}, 'question_graph': {'edges': [{'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'}, {'id': 'e01', 'source_id': 'n01', 'target_id': 'n02'}, {'id': 'e02',  'source_id': 'n02', 'target_id': 'n03'}], 'nodes': [{'curie': 'DOID:12365', 'id': 'n00', 'type': 'disease'}, {'id': 'n01', 'type': 'protein'}, {'id': 'n02', 'type': 'pathway'}, {'id': 'n03', 'type': 'protien'}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))

def test_cypher_gen_no_results():
	test_graph = {'knowledge_graph': {'edges': [], 'nodes': [{'id': 'DOID:12365', 'name': 'Ebola hemorrhagic fever', 'type': 'disease'}]}, 'question_graph': {'edges': [{'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'}, {'id': 'e01', 'source_id': 'n01', 'target_id': 'n02'}, {'id': 'e02',  'source_id': 'n02', 'target_id': 'n03'}], 'nodes': [{'curie': 'DOID:12365', 'id': 'n00', 'type': 'disease'}, {'id': 'n01', 'type': 'protein'}, {'id': 'n02', 'type': 'pathway'}, {'id': 'n03', 'type': 'chemical_substance'}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))

def test_cypher_gen_self_loop():
	test_graph = {'question_graph':
					{'edges': [{'id': 'e00', 'source_id': 'n00', 'target_id': 'n00'},
							{'id': 'e01', 'source_id': 'n00', 'target_id': 'n01'},
							{'id': 'e02',  'source_id': 'n01', 'target_id': 'n02'}],
					'nodes': [{'curie': 'DOID:12365', 'id': 'n00', 'type': 'disease'},
							{'id': 'n01', 'type': 'protein'},
							{'id': 'n02', 'type': 'pathway'}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	print("query:\n",cypher_query,"\n")
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))

def test_cypher_gen_two_hop_loop():
	test_graph = {'question_graph':
					{'edges': [{'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'},
							{'id': 'e01', 'source_id': 'n01', 'target_id': 'n00'},
							{'id': 'e02',  'source_id': 'n00', 'target_id': 'n02'}],
					'nodes': [{'curie': 'DOID:3312', 'id': 'n00', 'type': 'disease'},
							{'id': 'n01', 'type': 'protein'},
							{'id': 'n02', 'type': 'chemical_substance'}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	print("query:\n",cypher_query,"\n")
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))

def test_cypher_gen_three_hop_loop():
	test_graph = {'question_graph':
					{'edges': [{'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'},
							{'id': 'e01', 'source_id': 'n01', 'target_id': 'n03'},
							{'id': 'e03', 'source_id': 'n03', 'target_id': 'n00'},
							{'id': 'e02',  'source_id': 'n00', 'target_id': 'n02'}],
					'nodes': [{'curie': 'DOID:8337', 'id': 'n00', 'type': 'disease'},
							{'id': 'n01', 'type': 'protein'},
							{'id': 'n03', 'type': 'phenotypic_feature'},
							{'id': 'n02', 'type': 'chemical_substance'}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	print("query:\n",cypher_query,"\n")
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))

def test_cypher_gen_large_set(res_limit = None):
	test_graph = {'knowledge_graph': {'edges': [], 'nodes': [{'id': 'DOID:12365', 'name': 'Ebola hemorrhagic fever', 'type': 'disease'}]}, 'question_graph': {'edges': [{'id': 'e00', 'source_id': 'n00', 'target_id': 'n01'}, {'id': 'e01', 'source_id': 'n01', 'target_id': 'n02'}, {'id': 'e02',  'source_id': 'n02', 'target_id': 'n03'}], 'nodes': [{'curie': 'DOID:12365', 'id': 'n00', 'type': 'disease'}, {'id': 'n01', 'type': 'protein'}, {'id': 'n02', 'type': 'protein'}, {'id': 'n03', 'type': 'pathway'}]}}
	query_gen = get_cypher_from_question_graph(test_graph)
	print("answer_map")
	print("==========")
	cypher_query = query_gen.cypher_query_answer_map()
	if res_limit is not None:
		cypher_query += " limit " + str(res_limit)
	t0 = time.time()
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))
	print("knowledge_graph:")
	print("===============")
	cypher_query = query_gen.cypher_query_knowledge_graph()
	t0 = time.time()
	if res_limit is not None:
		cypher_query = cypher_query.replace("\nUNWIND",", limit " + str(res_limit) + "\nUNWIND",1)
	#print(cypher_query)
	res = cypher.run(cypher_query, conn=connection, config=defaults)
	print("time: ",time.time()-t0)
	print("results: ", len(res))



def test_cypher_gen_suite():
	print("###########")
	print("# One Hop #")
	print("###########")
	test_cypher_gen_one_hop()
	print("###########")
	print("# Two Hop #")
	print("###########")
	test_cypher_gen_two_hop()
	print("#############")
	print("# Three Hop #")
	print("#############")
	test_cypher_gen_two_hop()
	print("##############")
	print("# No Results #")
	print("##############")
	test_cypher_gen_no_results()
	print("#############")
	print("# Self Loop #")
	print("#############")
	test_cypher_gen_self_loop()
	print("################")
	print("# Two Hop Loop #")
	print("################")
	test_cypher_gen_two_hop_loop()
	print("##################")
	print("# Three Hop Loop #")
	print("##################")
	test_cypher_gen_three_hop_loop()
	print("#####################")
	print("# Large Set No Limit#")
	print("#####################")
	test_cypher_gen_large_set()
	#print("##########################")
	#print("# Large Set Limit 1,000 #")
	#print("##########################")
	#test_cypher_gen_self_loop(10)

def test_suite():
	test_get_node_names_of_type_connected_to_target()
	test_get_node_property()
	test_get_one_hop_target()
	test_get_relationship_types_between()
	test_return_subgraph_through_node_labels()
	test_weight_graph_with_google_distance()
	test_get_top_shortest_paths()
