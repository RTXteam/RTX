# This script will dump indexes like node names, edge names, etc.
import numpy as np
np.warnings.filterwarnings('ignore')
from neo4j.v1 import GraphDatabase, basic_auth
import requests_cache
import os
import sys
import re

#requests_cache.install_cache('orangeboard')
# specifiy the path of orangeboard database
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
dbpath = os.path.sep.join([*pathlist[:(RTXindex+1)],'data','orangeboard'])
requests_cache.install_cache(dbpath)

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../code")  # code directory
from RTXConfiguration import RTXConfiguration

remove_tab_newlines = re.compile(r"\s+")

def dump_name_description_KG2(file_name, session, write_mode):
	"""
	dump node names and descriptions of all nodes
	:param file_name: name of file to save to (TSV)
	:param session: neo4j session
	:param write_mode: 'w' for overwriting the file, 'a' for appending to the file at the end (or creating a new on if it DNE)
	:return: None
	"""
	query = "match (n) return properties(n) as p, labels(n) as l"
	res = session.run(query)
	with open(file_name, write_mode, encoding="utf-8") as fid:
		for item in res:
			prop_dict = item['p']
			labels = item['l']
			if 'id' in prop_dict and 'name' in prop_dict:
				if prop_dict['id'] and prop_dict['name'] and labels:
					label = list(set(labels) - {'Base'}).pop()
					if label:
						fid.write('%s\t' % prop_dict['id'])
						#fid.write('%s\t' % ' '.join(prop_dict['name'].split('\n')))  # FIXME: ugly workaround for node CHEMBL.COMPOUND:CHEMBL2259757 that has a tab in its name
						fid.write('%s\t' % remove_tab_newlines.sub(" ", prop_dict['name']))  # better approach
						fid.write('%s\n' % label)
				if label == "protein" and 'id' in prop_dict and 'symbol' in prop_dict:  # If it's a protein, also do the symbol
					if prop_dict['id'] and prop_dict['symbol'] and label:
						fid.write('%s\t' % prop_dict['id'])
						fid.write('%s\t' % prop_dict['symbol'])
						fid.write('%s\n' % label)
	return


def dump_name_description_KG1(file_name, session, write_mode):
	"""
	dump node names and descriptions of all nodes
	:param file_name: name of file to save to (TSV)
	:param session: neo4j session
	:param write_mode: 'w' for overwriting the file, 'a' for appending to the file at the end (or creating a new on if it DNE)
	:return: None
	"""
	query = "match (n) return properties(n) as p, labels(n) as l"
	res = session.run(query)
	with open(file_name, write_mode) as fid:
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

def dump_node_labels_KG1(file_name, session, write_mode):
	"""
	Dump the types of nodes
	:param file_name: to write to
	:param session: neo4j session
	:param write_mode: 'w' for overwriting the file, 'a' for appending to the file at the end (or creating a new on if it DNE)
	:return: None
	"""
	query = "match (n) return distinct labels(n)"
	res = session.run(query)
	with open(file_name, write_mode) as fid:
		for i in res:
			label = list(set(i["labels(n)"]).difference({"Base"}))  # get rid of the extra base label
			label = label.pop()  # this assumes only a single relationship type, but that's ok since that's how neo4j works
			fid.write('%s\n' % label)
	return

def dump_edge_types_KG1(file_name, session, write_mode):
	"""
	Dump the types of nodes
	:param file_name: to write to
	:param session: neo4j session
	:param write_mode: 'w' for overwriting the file, 'a' for appending to the file at the end (or creating a new on if it DNE)
	:return: None
	"""
	query = "match ()-[r]-() return distinct type(r)"
	res = session.run(query)
	with open(file_name, write_mode) as fid:
		for i in res:
			type = i["type(r)"]
			fid.write('%s\n' % type)
	return

# Actually dump the data for KG1
rtxConfig = RTXConfiguration()
rtxConfig.live = 'Production'
driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
session = driver.session()
dump_name_description_KG1('NodeNamesDescriptions_KG1.tsv', session, 'w')
#dump_node_labels_KG1('NodeLabels.tsv', session, 'w') # TODO: these are apparently unused?
#dump_edge_types_KG1('EdgeTypes.tsv', session, 'w') # TODO: these are apparently unused?


# now dump data for KG2
del rtxConfig
rtxConfig = RTXConfiguration()
rtxConfig.live = 'KG2'
driver = GraphDatabase.driver(rtxConfig.neo4j_bolt, auth=basic_auth(rtxConfig.neo4j_username, rtxConfig.neo4j_password))
session = driver.session()
dump_name_description_KG2('NodeNamesDescriptions_KG2.tsv', session, 'w')
#dump_node_labels_KG2('NodeLabels.tsv', session, 'w')  # TODO: these are apparently unused?
#dump_edge_types_KG2('EdgeTypes.tsv', session, 'w') # TODO: these are apparently unused?
