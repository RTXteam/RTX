import networkx as nx
from numpy import linalg as LA
import numpy as np
np.warnings.filterwarnings('ignore')
import cypher
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
from collections import Counter

# Connection information for the neo4j server, populated with orangeboard
driver = GraphDatabase.driver("bolt://lysine.ncats.io:7687", auth=basic_auth("neo4j", "precisionmedicine"))
session = driver.session()

# Connection information for the ipython-cypher package
connection = "http://neo4j:precisionmedicine@lysine.ncats.io:7473/db/data"
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


# Get the omims that connect up to a given doid
def get_omims_connecting_to_fixed_doid(session, doid, max_path_len=4, debug=False):
	"""
	This function finds all omim's within max_path_len steps (undirected) of a given disont_disease
	:param session: neo4j server session
	:param doid: disont_disease ID (eg: 'DOID:12345')
	:param max_path_len: Maximum path length to consider (default =4)
	:param debug: flag indicating if the query should also be returned
	:return: list of omim ID's
	"""
	query = "MATCH path=allShortestPaths((s:omim_disease)-[*1..%d]-(t:disont_disease))" \
			" WHERE t.name='%s' WITH distinct nodes(path)[0] as p RETURN p.name" %(max_path_len, doid)
	with session.begin_transaction() as tx:
		result = tx.run(query)
		result_list = [i for i in result]
		names = [i['p.name'] for i in result_list]
		if debug:
			return names, query
		else:
			return names


# get the list of relationships (and counts) between a fixed omim and fixed doid
def get_rels_fixed_omim_to_fixed_doid(session, omim, doid, max_path_len=4, debug=False):
	"""
	This function returns all unique relationships in paths from a given OMIM to a disont disease.
	:param session: neo4j server session
	:param omim: omim ID (eg: 'OMIM:12345')
	:param doid: disont_disease ID (eg: 'DOID:12345')
	:param max_path_len: Maximum path length to consider (default =4)
	:param debug: Flag that if true, also returns the cypher query
	:return: a list of cypher results (path) along with their counts.
	"""
	query = "MATCH path=allShortestPaths((s:omim_disease)-[*1..%d]-(t:disont_disease)) " \
			"WHERE s.name='%s' AND t.name='%s' " \
			"RETURN distinct extract (rel in relationships(path) | type(rel) ) as types, count(*)" % (max_path_len, omim, doid)
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


# Convert neo4j subgraph (from cypher query) into a networkx graph
def get_graph(res, directed=True):
	"""
	This function takes the result (subgraph) of a ipython-cypher query and builds a networkx graph from it
	:param res: output from an ipython-cypher query
	:param directed: Flag indicating if the resulting graph should be treated as directed or not
	:return: networkx graph (MultiDiGraph or MultiGraph)
	"""
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
def expected_graph_distance(omim, doid, max_path_len=4, directed=True, connection=connection, defaults=defaults):
	"""
	Given a source omim and target doid, extract the subgraph from neo4j consisting of all paths connecting these
	two nodes. Treat this as a uniform Markov chain (all outgoing edges with equal weight) and calculate the expected
	path length. This is equivalent to starting a random walker at the source node and calculating how long, on
	average, it takes to reach the target node.
	:param omim: Input OMIM ID (eg: 'OMIM:1234'), source
	:param doid: Input DOID ID (eg: 'DOID:1234'), target
	:param max_path_len: maximum path length to consider (default=4)
	:param directed: treat the Markov chain as directed or undirected (default=True (directed))
	:param connection: ipython-cypher connection string
	:param defaults: ipython-cypher configurations named tuple
	:return: a pair of floats giving the expected path length from source to target, and target to source respectively
	along with the basis (list of omim ID's).
	"""
	query = "MATCH path=allShortestPaths((s:omim_disease)-[*1..%d]-(t:disont_disease)) " \
			"WHERE s.name='%s' AND t.name='%s' " \
			"RETURN path" % (max_path_len, omim, doid)
	res = cypher.run(query, conn=connection, config=defaults)
	graph = get_graph(res, directed=directed)  # Note: I may want to make this directed, but sometimes this means no path from OMIM
	mat = nx.to_numpy_matrix(graph)  # get the indidence matrix
	basis = [i[1] for i in list(graph.nodes(data='names'))]  # basis for the matrix (i.e. list of ID's)
	doid_index = basis.index(doid)  # position of the target
	omim_index = basis.index(omim)  # position of the source
	#print(omim)  # diagnostics
	if directed:  # if directed, then add a sink node just after the target, make sure we can pass over it
		sink_column = np.zeros((mat.shape[0], 1))
		sink_column[doid_index] = 1  # connect doid to sink node
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
	exp_o_to_d = np.sum([float(i) * LA.matrix_power(mat_norm, i)[omim_index, doid_index] for i in range(15)])
	exp_d_to_o = np.sum([float(i) * LA.matrix_power(mat_norm, i)[doid_index, omim_index] for i in range(15)])
	if exp_o_to_d == 0:
		exp_o_to_d = float("inf")  # no such path
	if exp_d_to_o == 0:
		exp_d_to_o = float("inf")  # no such path
	return (exp_o_to_d, exp_d_to_o)  # (E(source->target), E(target->source))


def return_subgraph_paths_of_type(session, omim, doid, relationship_list, debug=False):
	"""
	This function extracts the subgraph of a neo4j database consisting of those paths that have the relationships (in
	order) of those given by relationship_list
	:param session: neo4j session
	:param omim: source OMIM ID (eg: OMIM:1234)
	:param doid: target disont_disease ID (eg: 'DOID:1235')
	:param relationship_list: list of relationships (must be valid neo4j relationship types), if this is a list of lists
	then the subgraph consisting of all valid paths will be returned
	:param debug: Flag indicating if the cypher query should be returned
	:return: networkx graph
	"""
	if not any(isinstance(el, list) for el in relationship_list):  # It's a single list of relationships
		query = "MATCH path=(s:omim_disease)-"
		for i in range(len(relationship_list)-1):
			query += "[:" + relationship_list[i] + "]-()-"
		query += "[:" + relationship_list[-1] + "]-" + "(t:disont_disease) "
		query += "WHERE s.name='%s' and t.name='%s' " %(omim, doid)
		query += "RETURN path"
		if debug:
			return query
	else:  # it's a list of lists
		query = "MATCH (s:omim_disease{name:'%s'}) " % omim
		for rel_index in range(len(relationship_list)):
			rel_list = relationship_list[rel_index]
			query += "OPTIONAL MATCH path%d=(s)-" % rel_index
			for i in range(len(rel_list)-1):
				query += "[:" + rel_list[i] + "]-()-"
			query += "[:" + rel_list[-1] + "]-" + "(t:disont_disease)"
			query += " WHERE t.name='%s' " % doid
		query += "RETURN "
		for rel_index in range(len(relationship_list)-1):
			query += "collect(path%d)+" % rel_index
		query += "collect(path%d)" %(len(relationship_list) - 1)
		if debug:
			return query
	graph = get_graph(cypher.run(query, conn=connection, config=defaults))
	return graph

def interleave_nodes_and_relationships(session, omim, doid, max_path_len=3, debug=False):
	"""
	Given fixed source omim and fixed target doid, returns a list consiting of the types of relationships and nodes
	in the path between the source and target
	:param session: neo4j-driver session
	:param omim: source omim OMIM:1234
	:param doid: target doid DOID:1234
	:param max_path_len: maximum path length to search over
	:param debug: if you just want the query to be returned
	:return: a list of lists of relationship and node types (strings) linking the source and target
	"""
	query_name = "match p= shortestPath((s:omim_disease)-[*1..%d]-(t:disont_disease)) "\
			"where s.name='%s' "\
			"and t.name='%s' "\
			"with nodes(p) as ns, rels(p) as rs, range(0,length(nodes(p))+length(rels(p))-1) as idx "\
			"return [i in idx | case i %% 2 = 0 when true then coalesce((ns[i/2]).name, (ns[i/2]).title) else type(rs[i/2]) end] as path "\
			"" %(max_path_len, omim, doid)
	query_type = "match p= shortestPath((s:omim_disease)-[*1..%d]-(t:disont_disease)) " \
				 "where s.name='%s' " \
				 "and t.name='%s' " \
				 "with nodes(p) as ns, rels(p) as rs, range(0,length(nodes(p))+length(rels(p))-1) as idx " \
				 "return [i in idx | case i %% 2 = 0 when true then coalesce(labels(ns[i/2])[1], (ns[i/2]).title) else type(rs[i/2]) end] as path " \
				 "" % (max_path_len, omim, doid)
	if debug:
		return query_name, query_type
	res_name = session.run(query_name)
	res_name = [item['path'] for item in res_name]
	res_type = session.run(query_type)
	res_type = [item['path'] for item in res_type]
	return res_name, res_type


def display_results(doid, paths_dict, omim_to_genetic_cond, q1_doid_to_disease, probs=False):
	"""
	Format the results in a pretty manner
	:param doid: souce doid DOID:1234
	:param paths_dict: a dictionary (keys OMIM id's) with values (path_name,path_type)
	:param omim_to_genetic_cond: a dictionary to translate between omim and genetic condition name
	:param q1_doid_to_disease:  a dictionary to translate between doid and disease name
	:param probs: optional probability of the OMIM being the right one
	:return: none (just prints to screen)
	"""
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
		print(("Possible genetic conditions that protect against %s: " % doid_name) + str(omim_names))
		for omim in omim_list:
			if omim in omim_to_genetic_cond:
				to_print = "The proposed mechanism of action for %s (%s) is: " % (omim_to_genetic_cond[omim], omim)
			else:
				to_print = "The proposed mechanism of action for %s is: " % omim
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
						to_print += "(%s:%s)" % (path_names[index], path_types[index])
				if doid in q1_doid_to_disease:
					to_print += "(%s). " % q1_doid_to_disease[doid]
				else:
					to_print += "(%s:%s). " % (path_names[-1], path_types[-1])
				if probs:
					if omim in probs:
						to_print += "Confidence: %f" % probs[omim]
				print(to_print)
			else:
				print(to_print)
				if probs:
					if omim in probs:
						print("With confidence %f, the mechanism is one of the following paths: " % probs[omim])
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
					to_print += ("There were %d paths of the form " % count) + str(relationship)
					print(to_print)
	else:
		if doid in q1_doid_to_disease:
			name = q1_doid_to_disease[doid]
		else:
			name = doid
		print("Sorry, I was unable to find a genetic condition that protects against %s" % name)

