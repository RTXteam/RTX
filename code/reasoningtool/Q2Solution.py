import numpy as np
np.warnings.filterwarnings('ignore')
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
import os
import Q1Utils
import argparse
import cypher


# Connection information for the neo4j server, populated with orangeboard
#driver = GraphDatabase.driver("bolt://lysine.ncats.io:7687", auth=basic_auth("neo4j", "precisionmedicine"))
driver = GraphDatabase.driver("bolt://ncats.saramsey.org:7687", auth=basic_auth("neo4j", "precisionmedicine"))
session = driver.session()

# Connection information for the ipython-cypher package
#connection = "http://neo4j:precisionmedicine@lysine.ncats.io:7473/db/data"
connection = "http://neo4j:precisionmedicine@ncats.saramsey.org:7473/db/data"
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



drug_to_disease = dict()
with open(os.path.abspath('../../q2/q2-drugandcondition-list.txt'), 'r') as fid:
	i = 0
	for line in fid.readlines():
		if i == 0:
			i += 1
			continue
		else:
			i += 1
			line = line.strip()
			drug = line.split('\t')[0].lower()
			disease = line.split('\t')[1].lower()
			drug_to_disease[drug] = disease

def has_drug(drug, session=session, debug=False):
	"""
	Check if drug is in the the graph
	:param drug:
	:param session:
	:param debug:
	:return:
	"""
	query = "match (n:pharos_drug{name:toLower('%s')}) return count(n)" % drug
	if debug:
		return query
	else:
		res = session.run(query)
		res = [i for i in res]
		if len(res) > 1:
			raise Exception("More than one node found for drug %s" % drug)
		elif len(res) == 1:
			if res[0]['count(n)'] > 0:
				return True
			else:
				return False
		else:
			return False


def has_disease(disease, session=session, debug=False):
	"""
	Check if disease is in the the graph
	:param disease:
	:param session:
	:param debug:
	:return:
	"""
	query = "MATCH (n:disont_disease) where '%s' in n.description return count(n)" % disease
	if debug:
		return query
	else:
		res = session.run(query)
		res = [i for i in res]
		if len(res) > 1:
			raise Exception("More than one node found for disease %s" % disease)
		elif len(res) == 1:
			if res[0]['count(n)'] > 0:
				return True
			else:
				return False
		else:
			return False

def has_phenotype(disease, session=session, debug=False):
	"""
	Check if phenotype is in the the graph
	:param phenotype:
	:param session:
	:param debug:
	:return:
	"""
	query = "MATCH (n:phenont_phenotype) where '%s' in n.name return count(n)" % disease
	if debug:
		return query
	else:
		res = session.run(query)
		res = [i for i in res]
		if len(res) > 1:
			raise Exception("More than one node found for disease %s" % disease)
		elif len(res) == 1:
			if res[0]['count(n)'] > 0:
				return True
			else:
				return False
		else:
			return False


def node_name_and_label_in_path(session, pharos_drug, disease, max_path_len=4, debug=False, disont=True):
	if disont:
		query = "match p=allShortestPaths((s:pharos_drug)-[*1..%d]-(t:disont_disease)) "\
				"where s.name='%s' and t.name='%s' "\
				"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx "\
				"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, pharos_drug, disease)
	else:
		query = "match p=allShortestPaths((s:pharos_drug)-[*1..%d]-(t:phenont_phenotype)) "\
				"where s.name='%s' and t.name='%s' "\
				"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx "\
				"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, pharos_drug, disease)
	if debug:
		return query
	res = session.run(query)
	res = [list(map(tuple, item['path'])) for item in res]
	return res


def pick_promising_paths(paths):
	num_labels = []
	has_prot_and_path = []
	has_prot_and_anat = []
	for path in paths:
		labels_set = set()
		for tup in path:
			labels_set.add(tup[1])
		num_labels.append(len(labels_set))
		if 'uniprot_protein' in labels_set:
			if 'reactome_pathway' in labels_set:
				has_prot_and_path.append(True)
			else:
				has_prot_and_path.append(False)
			if 'anatont_anatomy' in labels_set:
				has_prot_and_anat.append(True)
			else:
				has_prot_and_anat.append(False)
		else:
			has_prot_and_path.append(False)
			has_prot_and_anat.append(False)
	return num_labels, has_prot_and_path, has_prot_and_anat


disease = 'DOID:1686'
#disease = 'glaucoma'
drug = 'physostigmine'
res = node_name_and_label_in_path(session, drug, disease, max_path_len=6, debug=False, disont=True)

num_labels, has_prot_and_path, has_prot_and_anat = pick_promising_paths(res)

np.where(np.array(num_labels)>3)  # has more than 3 node types
np.where(np.array(has_prot_and_path)==True)  # has protein and reactome pathway
np.where(np.array(has_prot_and_anat)==True) # has protein and anatont_anatomy

# Now go through each of the anatont_anatomy things and find the ones that are the absolute closest to the
# disease

# Just need to connect things together


























