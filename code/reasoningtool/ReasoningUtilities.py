# This script will contain a bunch of utilities that help with graph/path extraction
# Should subsume Q1Utils and Q2Utils
import networkx as nx
from numpy import linalg as LA
import numpy as np

np.warnings.filterwarnings('ignore')
import cypher
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
from collections import Counter
import requests_cache
import QueryNCBIeUtils
import math
import MarkovLearning

requests_cache.install_cache('orangeboard')

# Connection information for the neo4j server, populated with orangeboard
driver = GraphDatabase.driver("bolt://rtx.ncats.io:7687", auth=basic_auth("neo4j", "precisionmedicine"))
session = driver.session()

# Connection information for the ipython-cypher package
connection = "http://neo4j:precisionmedicine@rtx.ncats.io:7473/db/data"
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

def count_nodes(sessions=session):
	"""
	Count the number of nodes
	:param sessions: neo4j bolt session
	:return: int
	"""
	query = "match (n) return count(n)"
	res = session.run(query)
	return res.single()["count(n)"]


def get_relationship_types(sessions=session):
	"""
	Get all the node labels in the neo4j database
	:param sessions: neo4j bolt session
	:return: list of node labels
	"""
	query = "match ()-[r]-() return distinct type(r)"
	res = session.run(query)
	res = [i["type(r)"] for i in res]
	return res


def get_node_labels(sessions=session):
	"""
	Get all the edge labels in the neo4j database
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
		name_to_descr[item_dict['name']] = item_dict['description']
	return name_to_descr


def get_node_property(name, node_property, node_label="", session=session, debug=False):
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
			query = "match (n{name:'%s'}) return n.%s" % (name, node_property)
		else:
			query = "match (n:%s{name:'%s'}) return n.%s" % (node_label, name, node_property)
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
			query = "match (n{name:'%s'}) return labels(n)" % (name)
		else:
			query = "match (n:%s{name:'%s'}) return labels(n)" % (node_label, name)
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
def get_node_names_of_type_connected_to_target(source_label, source_name, target_label, max_path_len=4, debug=False, verbose=False, direction="u", session=session):
	"""
	This function finds all node names of a certain kind (label) within max_path_len steps of a given source node.
	This replaces 'get_omims_connecting_to_fixed_doid' by using the source_label=disont_disease, target_label=omim_disease.
	:param source_label: kind of source node (eg: disont_disease)
	:param source_name: actual name of the source node (eg: DOID:14793)
	:param target_label: kind of target nodes to look for (eg: omim_disease)
	:param max_path_len: Maximum path length to consider (default =4)
	:param debug: flag indicating if the query should also be returned
	:param direction: Which direction to look (u: undirected, f: source->target, r: source<-target
	:param session: neo4j server session
	:return: list of omim ID's
	"""
	if direction == "r":
		query = "MATCH path=allShortestPaths((t:%s)-[*1..%d]->(s:%s))" \
				" WHERE s.name='%s' WITH distinct nodes(path)[0] as p RETURN p.name" % (target_label, max_path_len, source_label, source_name)
	elif direction == "f":
		query = "MATCH path=allShortestPaths((t:%s)<-[*1..%d]-(s:%s))" \
				" WHERE s.name='%s' WITH distinct nodes(path)[0] as p RETURN p.name" % (
				target_label, max_path_len, source_label, source_name)
	elif direction == "u":
		query = "MATCH path=allShortestPaths((t:%s)-[*1..%d]-(s:%s))" \
				" WHERE s.name='%s' WITH distinct nodes(path)[0] as p RETURN p.name" % (target_label, max_path_len, source_label, source_name)
	else:
		raise Exception("Sorry, the direction must be one of 'f', 'r', or 'u'")
	result = session.run(query)
	result_list = [i for i in result]
	names = [i['p.name'] for i in result_list]
	if verbose:
		print("Found %d nearby %s's" % (len(names), target_label))
	if debug:
		return names, query
	else:
		return names


def get_one_hop_target(source_label, source_name, target_label, edge_type, debug=False, verbose=False, direction="u", session=session):
	"""
	This function finds all target nodes connected in one hop to a source node (with a given edge type). EG: what proteins does drug X target?
	:param source_label: kind of source node (eg: disont_disease)
	:param source_name: actual name of the source node (eg: DOID:14793)
	:param target_label: kind of target nodes to look for (eg: omim_disease)
	:param edge_type: Type of edge to be interested in (eg: targets, disease_affects)
	:param debug: flag indicating if the query should also be returned
	:param direction: Which direction to look (u: undirected, f: source->target, r: source<-target
	:param session: neo4j server session
	:return: list of omim ID's
	"""
	if direction == "r":
		query = "MATCH path=(s:%s{name:'%s'})<-[:%s]-(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.name" % (source_label, source_name, edge_type, target_label)
	elif direction == "f":
		query = "MATCH path=(s:%s{name:'%s'})-[:%s]->(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.name" % (
				source_label, source_name, edge_type, target_label)
	elif direction == "u":
		query = "MATCH path=(s:%s{name:'%s'})-[:%s]-(t:%s)" \
				" WITH distinct nodes(path)[1] as p RETURN p.name" % (
				source_label, source_name, edge_type, target_label)
	else:
		raise Exception("Sorry, the direction must be one of 'f', 'r', or 'u'")
	result = session.run(query)
	result_list = [i for i in result]
	names = [i['p.name'] for i in result_list]
	if verbose:
		print("Found %d nearby %s's" % (len(names), target_label))
	if debug:
		return names, query
	else:
		return names

def get_relationship_types_between(source_name, source_label, target_name, target_label, max_path_len=4,session=session, debug=False):
	"""
	This function will return the relationship types between fixed source and target nodes
	:param source_name: source node name (eg: DOID:1234).
	This replaces get_rels_fixed_omim_to_fixed_doid().
	:param target_name: target node name (eg: skin rash)
	:param max_path_len: maximum path length to consider
	:param session: neo4j driver session
	:return: returns a list of tuples where tup[0] is the list of relationship types, tup[1] is the count.
	"""
	query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]-(t:%s)) " \
			"WHERE s.name='%s' AND t.name='%s' " \
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
def get_graph(res, directed=True):
	"""
	This function takes the result (subgraph) of a ipython-cypher query and builds a networkx graph from it
	:param res: output from an ipython-cypher query
	:param directed: Flag indicating if the resulting graph should be treated as directed or not
	:return: networkx graph (MultiDiGraph or MultiGraph)
	"""
	if not res:
		raise Exception("Empty graph. Cypher query input returned no results.")
	if nx is None:
		raise ImportError("Try installing NetworkX first.")
	if directed:
		graph = nx.MultiDiGraph()
	else:
		graph = nx.MultiGraph()
	for item in res._results.graph:
		for node in item['nodes']:
			graph.add_node(node['id'], properties=node['properties'], labels=node['labels'], names=node['properties']['name'], description=node['properties']['description'])
		for rel in item['relationships']:
			graph.add_edge(rel['startNode'], rel['endNode'], id=rel['id'], properties=rel['properties'], type=rel['type'])
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
				"WHERE s.name='%s' AND t.name='%s' " \
				"RETURN path" % (source_node_label, max_path_len, target_node_label, source_node, target_node)
	else:
		query = "MATCH path=allShortestPaths((s:%s)-[*1..%d]-(t:%s)) " \
				"WHERE s.name='%s' AND t.name='%s' " \
				"RETURN path" % (source_node_label, max_path_len, target_node_label, source_node, target_node)
	if debug:
		print(query)
		return
	res = cypher.run(query, conn=connection, config=defaults)
	graph = get_graph(res, directed=directed)  # Note: I may want to make this directed, but sometimes this means no path from OMIM
	mat = nx.to_numpy_matrix(graph)  # get the indidence matrix
	basis = [i[1] for i in list(graph.nodes(data='names'))]  # basis for the matrix (i.e. list of ID's)
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
		query = "MATCH path=(s:%s)-" % source_node_label
		for i in range(len(relationship_list) - 1):
			query += "[:" + relationship_list[i] + "]-()-"
		query += "[:" + relationship_list[-1] + "]-" + "(t:%s) " % target_node_label
		query += "WHERE s.name='%s' and t.name='%s' " % (source_node, target_node)
		query += "RETURN path"
		if debug:
			return query
	else:  # it's a list of lists
		query = "MATCH (s:%s{name:'%s'}) " % (source_node_label, source_node)
		for rel_index in range(len(relationship_list)):
			rel_list = relationship_list[rel_index]
			query += "OPTIONAL MATCH path%d=(s)-" % rel_index
			for i in range(len(rel_list) - 1):
				query += "[:" + rel_list[i] + "]-()-"
			query += "[:" + rel_list[-1] + "]-" + "(t:%s)" % target_node_label
			query += " WHERE t.name='%s' " % target_node
		query += "RETURN "
		for rel_index in range(len(relationship_list) - 1):
			query += "collect(path%d)+" % rel_index
		query += "collect(path%d)" % (len(relationship_list) - 1)
		if debug:
			return query
	graph = get_graph(cypher.run(query, conn=connection, config=defaults), directed=directed)
	return graph

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
				 "where s.name='%s' " \
				 "and t.name='%s' " \
				 "with nodes(p) as ns, rels(p) as rs, range(0,length(nodes(p))+length(rels(p))-1) as idx " \
				 "return [i in idx | case i %% 2 = 0 when true then coalesce((ns[i/2]).name, (ns[i/2]).title) else type(rs[i/2]) end] as path " \
				 "" % (source_node_label, max_path_len, target_node_label ,source_node, target_node)
	query_type = "match p= shortestPath((s:%s)-[*1..%d]-(t:%s)) " \
				 "where s.name='%s' " \
				 "and t.name='%s' " \
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
										  'desc': get_node_property(path_names[index], 'description')})
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



############################################################################################
# Stopping point 3/8/18 DK





def display_results_str(doid, paths_dict, omim_to_genetic_cond, q1_doid_to_disease, probs=False):
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
		if doid in q1_doid_to_disease:
			doid_name = q1_doid_to_disease[doid]
		else:
			doid_name = doid
		omim_names = []
		for omim in omim_list:
			if omim in omim_to_genetic_cond:
				omim_names.append(omim_to_genetic_cond[omim])
			else:
				omim_names.append(omim)
		ret_str = "Possible genetic conditions that protect against {doid_name}: ".format(doid_name=doid_name) + str(
			omim_names) + '\n'
		for omim in omim_list:
			if omim in omim_to_genetic_cond:
				to_print += "The proposed mechanism of action for %s (%s) is: " % (omim_to_genetic_cond[omim], omim)
			else:
				to_print += "The proposed mechanism of action for %s is: " % omim
			path_names, path_types = paths_dict[omim]
			if len(path_names) == 1:
				path_names = path_names[0]
				path_types = path_types[0]
				if omim in omim_to_genetic_cond:
					to_print += "(%s)" % (omim_to_genetic_cond[omim])
				else:
					to_print += "(%s:%s)" % (path_types[0], path_names[0])
				for index in range(1, len(path_names) - 1):
					if index % 2 == 1:
						to_print += "--[%s]-->" % (path_types[index])
					else:
						to_print += "(%s:%s:%s)" % (
						node_to_description(path_names[index]), path_names[index], path_types[index])
				if doid in q1_doid_to_disease:
					to_print += "(%s). " % q1_doid_to_disease[doid]
				else:
					to_print += "(%s:%s). " % (path_names[-1], path_types[-1])
				if probs:
					if omim in probs:
						to_print += "Confidence: %f" % probs[omim]
				to_print += '\n'
			else:
				to_print += '\n'
				if probs:
					if omim in probs:
						to_print += "With confidence %f, the mechanism is one of the following paths: " % probs[
							omim] + '\n'
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
		if doid in q1_doid_to_disease:
			name = q1_doid_to_disease[doid]
		else:
			name = doid
		to_print = "Sorry, I was unable to find a genetic condition that protects against {name}".format(
			name=name) + '\n'
	return to_print


def refine_omims_graph_distance(omims, doid, directed=False, max_path_len=3, verbose=False):
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
	for omim in omims:
		o_to_do, d_to_o = expected_graph_distance(omim, doid, directed=directed, max_path_len=max_path_len)
		exp_graph_distance_s_t.append(o_to_do)
		exp_graph_distance_t_s.append(d_to_o)
	s_t_np = np.array(exp_graph_distance_s_t)  # convert to numpy array, source to target
	# prioritize short paths
	omim_exp_distances = list()
	for i in range(len(omims)):
		omim_exp_distances.append((omims[i], s_t_np[i]))
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
		prioritized_omims_and_dist.append((omims[index], s_t_np[index]))
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
		if omim in omim_to_mesh:
			# res = QueryNCBIeUtils.QueryNCBIeUtils.normalized_google_distance(omim_to_mesh[omim], input_disease)
			omim_mesh = QueryNCBIeUtils.QueryNCBIeUtils.get_mesh_terms_for_omim_id(omim.split(':')[1])
			if len(omim_mesh) > 1:
				omim_mesh = omim_mesh[0]
			res = QueryNCBIeUtils.QueryNCBIeUtils.normalized_google_distance(omim_mesh, q1_doid_to_mesh[doid])
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
		path_name, path_type = interleave_nodes_and_relationships(session, omim, doid, max_path_len=max_path_len)
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
	res = get_node_names_of_type_connected_to_target("disont_disease", "DOID:14793", "uniprot_protein", max_path_len=1, direction="u")
	assert res == ['Q92838']
	res = get_node_names_of_type_connected_to_target("disont_disease", "DOID:14793", "uniprot_protein", max_path_len=1,direction="f")
	assert res == []
	res = get_node_names_of_type_connected_to_target("disont_disease", "DOID:14793", "uniprot_protein", max_path_len=1, direction="r")
	assert res == ['Q92838']
	res = get_node_names_of_type_connected_to_target("disont_disease", "DOID:14793", "omim_disease", max_path_len=2, direction="u")
	assert set(res) == set(['OMIM:305100','OMIM:313500'])

def test_get_node_property():
	res = get_node_property("DOID:14793", "description")
	assert res == 'hypohidrotic ectodermal dysplasia'
	res = get_node_property("DOID:14793", "description", "disont_disease")
	assert res == 'hypohidrotic ectodermal dysplasia'
	res = get_node_property("UBERON:0001259", "description")
	assert res == 'mucosa of urinary bladder'
	res = get_node_property("UBERON:0001259", "description", "anatont_anatomy")
	assert res == 'mucosa of urinary bladder'
	res = get_node_property("DOID:13306", "description")
	assert res == 'diphtheritic cystitis'
	res = get_node_property("DOID:13306", "expanded")
	assert res == False
	res = get_node_property("metolazone", "label")
	assert res == 'pharos_drug'


def test_get_one_hop_target():
	res = get_one_hop_target("disont_disease", "DOID:14793", "uniprot_protein", "gene_assoc_with")
	assert res == ["Q92838"]
	res = get_one_hop_target("pharos_drug", "carbetocin", "uniprot_protein", "targets")
	assert res == ["P30559"]


def test_get_relationship_types_between():
	res = get_relationship_types_between("DOID:0110307","disont_disease","DOID:1798","disont_disease",max_path_len=5)
	known_result = [(['is_parent_of', 'phenotype_assoc_with', 'phenotype_assoc_with'], 40), (['is_parent_of', 'gene_assoc_with', 'gene_assoc_with'], 2)]
	for tup in res:
		assert tup in known_result
	for tup in known_result:
		assert tup in res

	res = get_relationship_types_between("benzilonium","pharos_drug","DOID:14325","disont_disease",max_path_len=5)
	known_result = [(['targets', 'controls_state_change_of', 'gene_assoc_with', 'is_parent_of'], 10), (['targets', 'controls_expression_of', 'gene_assoc_with', 'is_parent_of'], 7)]
	for tup in res:
		assert tup in known_result
	for tup in known_result:
		assert tup in res


def test_get_graph():
	query = 'match p=(s:disont_disease{name:"DOID:14325"})-[*1..3]-(t:pharos_drug) return p limit 10'
	res = cypher.run(query, conn=connection, config=defaults)
	graph = get_graph(res)
	nodes = set(['138403', '148895', '140062', '140090', '139899', '140317', '138536', '121114', '138632', '147613', '140300', '140008', '140423'])
	edges = set([('138403', '121114', 0), ('148895', '147613', 0), ('148895', '147613', 1), ('148895', '147613', 2), ('148895', '147613', 3), ('148895', '147613', 4), ('148895', '147613', 5), ('148895', '147613', 6), ('148895', '147613', 7), ('148895', '147613', 8), ('148895', '147613', 9), ('140062', '121114', 0), ('140090', '121114', 0), ('139899', '121114', 0), ('140317', '121114', 0), ('138536', '121114', 0), ('121114', '148895', 0), ('121114', '148895', 1), ('121114', '148895', 2), ('121114', '148895', 3), ('121114', '148895', 4), ('121114', '148895', 5), ('121114', '148895', 6), ('121114', '148895', 7), ('121114', '148895', 8), ('121114', '148895', 9), ('138632', '121114', 0), ('140300', '121114', 0), ('140008', '121114', 0), ('140423', '121114', 0)])
	assert set(graph.nodes) == nodes
	assert set(graph.edges) == edges


def test_suite():
	test_get_node_names_of_type_connected_to_target()
	test_get_node_property()
	test_get_one_hop_target()
	test_get_relationship_types_between()