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

from scipy import stats

def rtx_fisher_test(input_node_list, input_node_label, compare_node_label, debug=False):

	"""
	Answer the question: how signifigant is the connection of the set input_node_list to each of the adjacent
	nodes of type compare_node_label by the fisher's exact test. Used to compute GO term enrichment.
	:param input_node_list: list of node id IDs e.g ["Q6UWI4", "P09110",.. etc]
	:param input_node_label: node label for types in list e.g. "protein"
	:param compare_node_label: node label to compare against  e.g. "biological_process"
	:return: dictionary of connecting nodes from compare_node_label and corresponding signifigance levels
	"""
	dict_in_compare = {}

	for node in input_node_list: # get all the nodes adjacent to those in input_node_list from compare_node_label ex. pathways
		query = "MATCH (n:%s{id:'%s'})-[]-(s:%s) RETURN distinct s.id" % (input_node_label,node,compare_node_label)
		if debug:
			print(query)
		else:
			res = session.run(query)
			result_list = [item['s.id'] for item in res]
			for adj in result_list:
				if adj not in dict_in_compare:
					dict_in_compare[adj]=[node]
				else:
					dict_in_compare[adj].append(node)

	size_of_adjacent={} # degree of each adjacent node with respect to input_node_label in compare_node_label

	for node in dict_in_compare: # fill that guy in. ex: find number of proteins (or length) of each involved pathway
		query = "MATCH (n:%s{id:'%s'})-[]-(s:%s) return count(distinct s)" % (compare_node_label,node, input_node_label)
		if debug:
			print(query)
		else:
			res = session.run(query)
			size_of_adjacent[node] = res.single()["count(distinct s)"]

	query = "MATCH (n:%s) return count(distinct n)" % (input_node_label) # now find number of nodes in compare_node_label ex: find size of proteome

	if debug:
		return query
	else:
		res = session.run(query)

	size_of_total = res.single()["count(distinct n)"]
	size_of_set = len(input_node_list)

	output = {} # prep the answer

	for node in dict_in_compare: # go find signifigance levels ex. GO term enrichments. table is: [[in pathway and sample, in pathway],[in sample not in pathway],[in proteome and not in pathway]]
		contingency_table = [[len(dict_in_compare[node]),size_of_adjacent[node]],[size_of_set-len(dict_in_compare[node]),size_of_total-size_of_adjacent[node]]]
		output[node] = stats.fisher_exact(contingency_table)

	return output


def fisher_exact(input_node_list, input_node_label, compare_node_label, rel_type=False, debug=False):
	"""
	Answer the question: how signifigant is the connection of the set input_node_list to each of the adjacent
	nodes of type compare_node_label by the fisher's exact test. Used to compute GO term enrichment.
	:param input_node_list: list of node id IDs e.g ["Q6UWI4", "P09110",.. etc]
	:param input_node_label: node label for types in list e.g. "protein"
	:param compare_node_label: node label to compare against  e.g. "biological_process"
	:return: dictionary of connecting nodes from compare_node_label and corresponding signifigance levels
	"""
	dict_in_compare = dict()
	query = 'with ["%s"' % input_node_list[0]
	for node in input_node_list[1:]:
		query += ',"%s"' % node
	query += "]"
	if not rel_type:
		query += " as inlist match (d:%s)-[]-(s:%s) where s.id in inlist return d.id as ident, count(*) as ct" % (compare_node_label, input_node_label)
	else:
		query += " as inlist match (d:%s)-[:%s]-(s:%s) where s.id in inlist return d.id as ident, count(*) as ct" % (
		compare_node_label, rel_type, input_node_label)
	if debug:
		print(query)
	else:
		res = session.run(query)
		for item in res:
			dict_in_compare[item["ident"]] = item["ct"]

	size_of_adjacent = dict()  # degree of each adjacent node with respect to input_node_label in compare_node_label

	query = 'with ["%s"' % input_node_list[0]
	for node in input_node_list[1:]:
		query += ',"%s"' % node
	query += "]"
	if not rel_type:
		query += " as inlist match (d:%s)-[]-(s:%s) where s.id in inlist with distinct d as d match (d)-[]-(:%s) return d.id as ident, count(*) as ct" % (compare_node_label, input_node_label, input_node_label)
	else:
		query += " as inlist match (d:%s)-[:%s]-(s:%s) where s.id in inlist with distinct d as d match (d)-[:%s]-(:%s) return d.id as ident, count(*) as ct" % (
		compare_node_label, rel_type, input_node_label, rel_type, input_node_label)
	if debug:
		print(query)
	else:
		res = session.run(query)
		for item in res:
			size_of_adjacent[item["ident"]] = item["ct"]

	query = "MATCH (n:%s) return count(distinct n)" % (input_node_label) # now find number of nodes in compare_node_label ex: find size of proteome

	if debug:
		return query
	else:
		res = session.run(query)

	size_of_total = res.single()["count(distinct n)"]
	size_of_set = len(input_node_list)

	output = {}  # prep the answer

	for node in dict_in_compare: # go find signifigance levels ex. GO term enrichments. table is: [[in pathway and sample, in pathway],[in sample not in pathway],[in proteome and not in pathway]]
		contingency_table = [[dict_in_compare[node], size_of_adjacent[node]], [max(0, size_of_set-dict_in_compare[node]), max(0, size_of_total-size_of_adjacent[node])]]
		output[node] = stats.fisher_exact(contingency_table)

	return output