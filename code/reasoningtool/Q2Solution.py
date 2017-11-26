import numpy as np
np.warnings.filterwarnings('ignore')
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
import os
import Q1Utils
import argparse
import cypher
import QueryNCBIeUtils
import requests_cache
requests_cache.install_cache('orangeboard')



# Connection information for the neo4j server, populated with orangeboard
driver = GraphDatabase.driver("bolt://lysine.ncats.io:7687", auth=basic_auth("neo4j", "precisionmedicine"))
#driver = GraphDatabase.driver("bolt://ncats.saramsey.org:7687", auth=basic_auth("neo4j", "precisionmedicine"))
session = driver.session()

# Connection information for the ipython-cypher package
connection = "http://neo4j:precisionmedicine@lysine.ncats.io:7473/db/data"
#connection = "http://neo4j:precisionmedicine@ncats.saramsey.org:7473/db/data"
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


drug_to_disease_doid = dict()
disease_doid_to_description = dict()
with open(os.path.abspath('../../data/q2/q2-drugandcondition-list-mapped.txt'), 'r') as fid:
	i = 0
	for line in fid.readlines():
		if i == 0:
			i += 1
			continue
		else:
			i += 1
			line = line.strip()
			line_split = line.split('\t')
			drug = line_split[1].lower()
			disease_doid = line_split[-1]
			disease_descr = line_split[2]
			drug_to_disease_doid[drug] = disease_doid
			disease_doid_to_description[disease_doid] = disease_descr


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


def has_disease(disease_doid, session=session, debug=False):
	"""
	Check if disease is in the the graph
	:param disease:
	:param session:
	:param debug:
	:return:
	"""
	query = "MATCH (n:disont_disease) where n.name='%s' return count(n)" % disease_doid
	if debug:
		return query
	else:
		res = session.run(query)
		res = [i for i in res]
		if len(res) > 1:
			raise Exception("More than one node found for disease %s" % disease_doid)
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
	query = "MATCH (n:phenont_phenotype) where n.name='%s' return count(n)" % disease
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


def node_name_and_label_in_path(session, pharos_drug, disease, max_path_len=2, debug=False, disont=True):
	"""
	Return nodes and labels in short paths that connect drug to disease that also go through anatomy and pathway
	:param session: neo4j session
	:param pharos_drug: source pharos drug
	:param disease: target disease
	:param max_path_len: maximum path length to consider
	:param debug: just return the query
	:param disont: flag if this is a disont disease (false if phenotype)
	:return: list of lists of name, label tuples
	"""
	if disont:
		#query = "match p=allShortestPaths((s:pharos_drug)-[*1..%d]-(t:disont_disease)) "\
		#		"where s.name='%s' and t.name='%s' "\
		#		"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx "\
		#		"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, pharos_drug, disease)
		#query = "match p=(s:pharos_drug)-[*1..%d]-(t:disont_disease) " \
		#		"where s.name='%s' and t.name='%s' " \
		#		"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx " \
		#		"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, pharos_drug, disease)
		query = "match p=(n:pharos_drug{name:'%s'})-[]-(:uniprot_protein)-[]-(t)-[*0..%d]-(:disont_disease{name:'%s'}) "\
				"where t:anatont_anatomy or t:reactome_pathway "\
				"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx " \
				"return [i in idx | [(ns[i]).name, labels(ns[i])[1]] ] as path " % (pharos_drug, max_path_len, disease)
	else:
		#query = "match p=allShortestPaths((s:pharos_drug)-[*1..%d]-(t:phenont_phenotype)) "\
		#		"where s.name='%s' and t.name='%s' "\
		#		"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx "\
		#		"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, pharos_drug, disease)
		query = "match p=(n:pharos_drug{name:'%s'})-[]-(:uniprot_protein)-[]-(t)-[*0..%d]-(:phenont_phenotype{name:'%s'}) " \
				"where t:anatont_anatomy or t:reactome_pathway " \
				"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx " \
				"return [i in idx | [(ns[i]).name, labels(ns[i])[1]] ] as path " % (pharos_drug, max_path_len, disease)
	if debug:
		return query
	res = session.run(query)
	res = [list(map(tuple, item['path'])) for item in res]
	return res


def look_for_pathway_and_anat(paths):
	"""
	Given a set of paths, count the number of distinct labels, where pathways, and where anatomy occur
	:param paths: a list of paths (from node_name_and_label_in_path)
	:return: a list of number of distinct labels in the paths, a list of logicals indicating if that path has a pathway
	and a list of logicals indicating if that path has an anatomy node
	"""
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

def delete_paths_through_other_drugs_diseases(paths, drug, disease):
	"""
	Delete from paths those that contain other drugs or diseases
	:param paths: a list of paths (from node_name_and_label_in_path)
	:param drug: the source drug
	:param disease: the target disease or phenotype
	:return: a subset of paths that don't contain other drugs or diseases
	"""
	if disease.split(':')[0] == "DOID":
		is_disont = True
	else:
		is_disont = False
	good_paths = []
	for path in paths:
		to_include = True
		for node in path:
			if node[1] == 'pharos_drug' and node[0] != drug:
				to_include = False  # don't include if you find another drug in the path
			if is_disont:
				if node[1] == 'disont_disease' and node[0] != disease:
					to_include = False  # don't include if you find another disease in the path (and looking at disont)
			if not is_disont:
				if node[1] == 'disont_disease':
					to_include = False  # if looking at phenotype, don't include paths with disont in it
		if to_include:
			good_paths.append(path)
	return good_paths


def get_path_length(source_type, source_name, target_type, target_name, session=session, debug=False):
	"""
	Get shortest path length between source and target
	:param source_type: source node type
	:param source_name: source node name
	:param target_type: target node type
	:param target_name: target node name
	:param session: neo4j session
	:param debug: just return query
	:return: shortest path length between source and target
	"""
	query = "match p=shortestPath((s:%s{name:'%s'})-[*0..3]-(t:%s{name:'%s'})) "\
			"return length(p)" % (source_type, source_name, target_type, target_name)
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['length(p)']
	else:
		return np.inf

# TODO: Debug this guy
def get_intermediate_path_lenth(source_type, source_name, intermediate_type, intermediate_name, target_type, target_name, session=session, debug=False):
	query = "match p = (s:%s{name:'%s'})-[*0..2]-(i:%s{name:'%s'})-[*0..2]-(t:%s{name:'%s'}) "\
			"return length(p) order by length(p) limit 1" % (source_type, source_name, intermediate_type, intermediate_name, target_type, target_name)
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['length(p) order by length(p) limit 1']
	else:
		return np.inf


def anatomy_name_to_description(anatomy_name, session=session, debug=False):
	query = "match (n:anatont_anatomy{name:'%s'}) return n.description" % anatomy_name
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['n.description']
	else:
		return "a tissue "


def connect_to_pathway(path, pathway_near_intersection_names):
	proteins = []
	for node in path:
		if node[1] == "uniprot_protein":
			proteins.append(node[0])
	if len(proteins) == 1:
		pathway_distances = []
		for pathway in pathway_near_intersection_names:
			path_dist = get_path_length("uniprot_protein", proteins[0], "reactome_pathway", pathway)
			pathway_distances.append((pathway, path_dist))
	else:
		pathway_distances = []
		for pathway in pathway_near_intersection_names:
			path_dist = get_intermediate_path_lenth("uniprot_protein", proteins[0], "reactome_pathway", pathway,
													"uniprot_protein", proteins[1])
			pathway_distances.append((pathway, path_dist))
	# pick the smallest
	pathway_distances_sorted = sorted(pathway_distances, key=lambda tup: tup[1])
	smallest_pathway = pathway_distances_sorted[0][0]
	return smallest_pathway


def pathway_name_to_description(pathway_name, session=session, debug=False):
	query = "match (n:reactome_pathway{name:'%s'}) return n.description" % pathway_name
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['n.description']
	else:
		return " "


def prioritize_on_gd(found_anat_names, disease_description):
	anat_name_google_distance = []
	for anat in found_anat_names:
		query = "match (n:anatont_anatomy{name:'%s'}) return n.description" % anat
		res = session.run(query)
		res = [i for i in res]
		if res:
			description = res[0]['n.description']
			total_gd = 0
			num_words = 0
			gd = QueryNCBIeUtils.QueryNCBIeUtils.normalized_google_distance(description, disease_description)
			if gd > 0:
				anat_name_google_distance.append((anat, gd))
			else:
				for word in description.split():
					gd = QueryNCBIeUtils.QueryNCBIeUtils.normalized_google_distance(word, disease_description)
					if gd > 0:
						total_gd += gd
						num_words += 1
				if num_words > 0:
					anat_name_google_distance.append((anat, total_gd / float(num_words)))
				else:
					anat_name_google_distance.append((anat, np.inf))
		else:
			anat_name_google_distance.append((anat, np.inf))
	return anat_name_google_distance


def get_proteins_in_both(paths, pathway_indicies, anat_indicies):
	found_path_names = set()
	for index in pathway_indicies:
		path = paths[index]
		for node in path:
			if node[1] == 'reactome_pathway':
				found_path_names.add(node[0])
	# Get the names of the found anatomy entities
	found_anat_names = set()
	for index in anat_indicies:
		path = paths[index]
		for node in path:
			if node[1] == 'anatont_anatomy':
				found_anat_names.add(node[0])
	# get the proteins in the pathway and anat paths
	proteins_in_pathway = set()
	for index in pathway_indicies:
		path = paths[index]
		for node in path:
			if node[1] == "uniprot_protein":
				proteins_in_pathway.add(node[0])
	proteins_in_anat = set()
	for index in anat_indicies:
		path = paths[index]
		for node in path:
			if node[1] == "uniprot_protein":
				proteins_in_anat.add(node[0])
	in_both = proteins_in_pathway.intersection(proteins_in_anat)
	return in_both, found_anat_names


#disease = 'DOID:1686'
#disease_description = 'glaucoma'
#drug = 'physostigmine'

disease = "DOID:10652"
disease_description = "Alzheimer Disease"
drug = "MEMANTINE".lower()

# get shortest paths between drug and disease
paths = node_name_and_label_in_path(session, drug, disease, max_path_len=2, debug=False, disont=True)

# delete those that go through other drugs or diseases
paths = delete_paths_through_other_drugs_diseases(paths, drug, disease)

# Get: 1. Number of distinct node labels in each path, 2. if the path has a reactome pathway in it and
# 3. If the path has an anatomy node in it
num_labels, has_prot_and_path, has_prot_and_anat = look_for_pathway_and_anat(paths)

# Location of paths with pathway and anatomy
pathway_indicies = np.where(np.array(has_prot_and_path))[0]  # paths that have reactome pathway
anat_indicies = np.where(np.array(has_prot_and_anat))[0]  # paths that have anatomy/tissue in it

# TODO: go to print if this occurs
# See if we get lucky and we have anatomy and pathway in a single path
pathway_and_anat_indicies = set(pathway_indicies).intersection(set(anat_indicies))
if pathway_and_anat_indicies:
	print("RETURN THIS RESULT: " + str(paths[list(pathway_and_anat_indicies)[0]]))

# Otherwise, try to connect them up
# get the names of the found pathway entities
proteins_in_both, found_anat_names = get_proteins_in_both(paths, pathway_indicies, anat_indicies)

#if proteins_in_both:
#	print("There are proteins nearby to anatomy and pathways: " + str(proteins_in_both))

# get the pathway paths and anatomy paths that contain these shared proteins
pathway_near_intersection_indices = []
pathway_near_intersection_names = set()
anat_near_intersection_indicies = []
for index in pathway_indicies:
	path = paths[index]
	path_names = set([node[0] for node in path])
	if path_names.intersection(proteins_in_both):
		for node in path:
			if node[1] == "reactome_pathway":
				pathway_near_intersection_names.add(node[0])
		pathway_near_intersection_indices.append(index)

for index in anat_indicies:
	path = paths[index]
	path_names = set([node[0] for node in path])
	if path_names.intersection(proteins_in_both):
		anat_near_intersection_indicies.append(index)

# Let's find the anatomy that is closest to the disease
#anat_distances = dict()
#for anat in found_anat_names:
#	anat_distances[anat] = get_path_length("anatont_anatomy", anat, "disont_disease", disease)

#pathway_distances = dict()
#for pathway in found_path_names:
#	pathway_distances[pathway] = get_path_length("reactome_pathway", pathway, "disont_disease", disease)

# All the distances are the same, so it's not going to help to prioritize short paths

# Let's try to prioritize the anatomy based on google distance
anat_name_google_distance = prioritize_on_gd(found_anat_names, disease_description)

# Get the top three
anat_name_google_distance_sorted = sorted(anat_name_google_distance, key=lambda tup: tup[1])
num_select = 3
best_anat = dict()
for i in range(num_select):
	anat_name = anat_name_google_distance_sorted[i][0]
	anat_gd = anat_name_google_distance_sorted[i][1]
	best_anat[anat_name] = anat_gd

# Now, for these anatomy, get the relevant paths
best_anat_paths = []
for path in paths:
	for node in path:
		if node[1] == "anatont_anatomy":
			if node[0] in best_anat.keys():
				best_anat_paths.append(path)
				#print(path)

# get confidences (based on google distances)
gd_max = np.ma.masked_invalid(np.array([i[1] for i in anat_name_google_distance_sorted])).max()


# Then display the results....
print("The possible clinical outcome pathways include: ")
#def display_path(path, pathway_near_intersection_names, best_anat, gd_max):
path = best_anat_paths[0]
pathway = connect_to_pathway(path, pathway_near_intersection_names)
pathway_description = pathway_name_to_description(pathway)
path_proteins = []
anatomy_name = False
for node in path:
	if node[1] == "uniprot_protein":
		path_proteins.append(node[0])
	if node[1] == "anatont_anatomy":
		anatomy_name = node[0]
conf = 1-best_anat[anatomy_name]/gd_max
#print("The possible clinical outcome pathways include: ")
#print("The drug %s " % drug)
to_print = "The drug %s " % drug
#print("targets the protein %s" % path_proteins[0])
to_print += "targets the protein %s" % path_proteins[0]
if len(path_proteins) > 1:
	#print("which is involved with the %s pathway and associated protein %s" % (pathway_description, path_proteins[1]))
	to_print += "which is involved with the %s pathway and associated protein %s" % (pathway_description, path_proteins[1])
else:
	#print("which is involved with the %s pathway" % pathway_description)
	to_print = "which is involved with the %s pathway" % pathway_description
if anatomy_name:
	anatomy_description = anatomy_name_to_description(anatomy_name)
	#print("which is relevant to the %s" % anatomy_description)
	to_print += "which is relevant to the %s" % anatomy_description
#print("and alleviates symptoms of %s. " % disease_description)
to_print += "and alleviates symptoms of %s. " % disease_description
#print("(Confidence %f)." % conf)
to_print += "(Confidence %f)." % conf
print(to_print)





















