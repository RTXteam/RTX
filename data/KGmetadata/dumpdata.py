# This script will dump indexes like node names, edge names, etc.
import networkx as nx
from numpy import linalg as LA
import numpy as np

np.warnings.filterwarnings('ignore')
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
import requests_cache
import os
import sys

requests_cache.install_cache('orangeboard')
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../code")  # code directory


def dump_name_description_KG2(file_name, session):
	"""
	dump node names and descriptions of all nodes
	:param file_name: name of file to save to (TSV)
	:param session: neo4j session
	:return: None
	"""
	query = "match (n) return properties(n) as p, labels(n) as l"
	res = session.run(query)
	with open(file_name, 'w') as fid:
		for item in res:
			prop_dict = item['p']
			labels = item['l']
			if 'id' in prop_dict and 'name' in prop_dict:
				fid.write('%s\t' % prop_dict['id'])
				fid.write('%s\t' % prop_dict['name'])
				label = list(set(labels) - {'Base'}).pop()
				fid.write('%s\n' % label)
				if label == "protein" and 'id' in prop_dict and 'symbol' in prop_dict:  # If it's a protein, also do the symbol
					fid.write('%s\t' % prop_dict['id'])
					fid.write('%s\t' % prop_dict['symbol'])
					fid.write('%s\n' % label)
	return


def dump_name_description_KG1(file_name, session):
	"""
	dump node names and descriptions of all nodes
	:param file_name: name of file to save to (TSV)
	:param session: neo4j session
	:return: None
	"""
	query = "match (n) return properties(n) as p, labels(n) as l"
	res = session.run(query)
	with open(file_name, 'w') as fid:
		for item in res:
			prop_dict = item['p']
			labels = item['l']
			fid.write('%s\t' % prop_dict['id'])
			fid.write('%s\t' % prop_dict['name'])
			label = list(set(labels) - {'Base'}).pop()
			fid.write('%s\n' % label)
			if label == "protein":  # If it's a protein, also do the symbol
				fid.write('%s\t' % prop_dict['id'])
				fid.write('%s\t' % prop_dict['symbol'])
				fid.write('%s\n' % label)
	return

def dump_node_labels_KG1(file_name, session):
	"""
	Dump the types of nodes
	:param file_name: to write to
	:param session: neo4j session
	:return: None
	"""
	query = "match (n) return distinct labels(n)"
	res = session.run(query)
	with open(file_name, 'w') as fid:
		for i in res:
			label = list(set(i["labels(n)"]).difference({"Base"}))  # get rid of the extra base label
			label = label.pop()  # this assumes only a single relationship type, but that's ok since that's how neo4j works
			fid.write('%s\n' % label)
	return

def dump_edge_types_KG1(file_name, session):
	"""
	Dump the types of nodes
	:param file_name: to write to
	:param session: neo4j session
	:return: None
	"""
	query = "match ()-[r]-() return distinct type(r)"
	res = session.run(query)
	with open(file_name, 'w') as fid:
		for i in res:
			type = i["type(r)"]
			fid.write('%s\n' % type)
	return

# Actually dump the data for KG1
from RTXConfiguration import RTXConfiguration
rtxConfig = RTXConfiguration()
rtxConfig.live = 'Production'
driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
session = driver.session()
dump_name_description_KG1('NodeNamesDescriptions2.tsv', session)
dump_node_labels_KG1('NodeLabels.tsv', session)
dump_edge_types_KG1('EdgeTypes.tsv', session)
