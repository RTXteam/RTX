# This script will dump indexes like node names, edge names, etc.
import networkx as nx
from numpy import linalg as LA
import numpy as np

np.warnings.filterwarnings('ignore')
import cypher
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
import requests_cache

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

def dump_name_description(file_name, session=session):
	"""
	dump node names and descriptions of all nodes
	:param file_name: name of file to save to (TSV)
	:param session: neo4j session
	:return: None
	"""
	query = "match (n) return properties(n) as n"
	res = session.run(query)
	with open(file_name, 'w') as fid:
		for item in res:
			item_dict = item['n']
			fid.write('%s\t' % item_dict['name'])
			fid.write('%s\n' % item_dict['description'])
	return

def dump_node_labels(file_name, session=session):
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

def dump_edge_types(file_name, session=session):
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

# Actually dump the data
dump_name_description('NodeNamesDescriptions.tsv')
dump_node_labels('NodeLabels.tsv')
dump_edge_types('EdgeTypes.tsv')
