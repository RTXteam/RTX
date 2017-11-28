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

def node_to_description(name, session=session, debug=False):
	"""
	Get the description of an protein node
	:param name: name of the node
	:param session: neo4j session
	:param debug: just return the query
	:return: a string (the description of the node)
	"""
	query = "match (n{name:'%s'}) return n.description" % name
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['n.description']
	else:
		return " "


# Get the omims that connect up to a given doid
def get_omims_connecting_to_fixed_doid(doid, max_path_len=4, debug=False, verbose=False, directed=False):
	"""
	This function finds all omim's within max_path_len steps (undirected) of a given disont_disease
	:param session: neo4j server session
	:param doid: disont_disease ID (eg: 'DOID:12345')
	:param max_path_len: Maximum path length to consider (default =4)
	:param debug: flag indicating if the query should also be returned
	:return: list of omim ID's
	"""
	if directed:
		query = "MATCH path=allShortestPaths((s:omim_disease)-[*1..%d]->(t:disont_disease))" \
				" WHERE t.name='%s' WITH distinct nodes(path)[0] as p RETURN p.name" % (max_path_len, doid)
	else:
		query = "MATCH path=allShortestPaths((s:omim_disease)-[*1..%d]-(t:disont_disease))" \
				" WHERE t.name='%s' WITH distinct nodes(path)[0] as p RETURN p.name" %(max_path_len, doid)
	result = session.run(query)
	result_list = [i for i in result]
	names = [i['p.name'] for i in result_list]
	if verbose:
		print("Found %d nearby omims" % len(names))
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
	if directed:
		query = "MATCH path=allShortestPaths((s:omim_disease)-[*1..%d]->(t:disont_disease)) " \
				"WHERE s.name='%s' AND t.name='%s' " \
				"RETURN path" % (max_path_len, omim, doid)
	else:
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
						to_print += "(%s:%s:%s)" % (node_to_description(path_names[index]), path_names[index], path_types[index])
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
		#print(well_studied_omims)
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


