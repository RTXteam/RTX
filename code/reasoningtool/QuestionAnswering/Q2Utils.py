# A collection of sub-routines helpful for Q2
import numpy as np
np.warnings.filterwarnings('ignore')
from neo4j.v1 import GraphDatabase, basic_auth
import sys
import os
try:
	import QueryNCBIeUtils
except ImportError:
	sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../kg-construction')))  # Go up one level and look for it
	import QueryNCBIeUtils
import requests_cache
requests_cache.install_cache('orangeboard')

# Connection information for the neo4j server, populated with orangeboard
driver = GraphDatabase.driver("bolt://rtx.ncats.io:7687", auth=basic_auth("neo4j", "precisionmedicine"))  # production server
#driver = GraphDatabase.driver("bolt://ncats.saramsey.org:7687", auth=basic_auth("neo4j", "precisionmedicine"))  # test server
session = driver.session()


def has_drug(drug, session=session, debug=False):
	"""
	Check if drug is in the the graph
	:param drug:
	:param session:
	:param debug:
	:return:
	"""
	query = "match (n:drug{name:toLower('%s')}) return count(n)" % drug
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
	query = "MATCH (n:disease) where n.name='%s' return count(n)" % disease_doid
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
	query = "MATCH (n:phenotypic_feature) where n.name='%s' return count(n)" % disease
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


def node_name_and_label_in_path(drug, disease, max_path_len=2, debug=False, disont=True, session=session):
	"""
	Return nodes and labels in short paths that connect drug to disease that also go through anatomy and pathway
	:param session: neo4j session
	:param drug: source pharos drug
	:param disease: target disease
	:param max_path_len: maximum path length to consider
	:param debug: just return the query
	:param disont: flag if this is a disont disease (false if phenotype)
	:return: list of lists of name, label tuples
	"""
	if disont:
		#query = "match p=allShortestPaths((s:drug)-[*1..%d]-(t:disease)) "\
		#		"where s.name='%s' and t.name='%s' "\
		#		"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx "\
		#		"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, drug, disease)
		#query = "match p=(s:drug)-[*1..%d]-(t:disease) " \
		#		"where s.name='%s' and t.name='%s' " \
		#		"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx " \
		#		"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, drug, disease)
		query = "match p=(n:drug{name:'%s'})-[]-(:protein)-[]-(t)-[*0..%d]-(:disease{name:'%s'}) "\
				"where t:anatomical_entity or t:pathway "\
				"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx " \
				"return [i in idx | [(ns[i]).name, labels(ns[i])[1]] ] as path " % (drug, max_path_len, disease)
	else:
		#query = "match p=allShortestPaths((s:drug)-[*1..%d]-(t:phenotypic_feature)) "\
		#		"where s.name='%s' and t.name='%s' "\
		#		"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx "\
		#		"return [i in idx | [(ns[i]).name, labels(ns[i])[0]] ] as path " % (max_path_len, drug, disease)
		query = "match p=(n:drug{name:'%s'})-[]-(:protein)-[]-(t)-[*0..%d]-(:phenotypic_feature{name:'%s'}) " \
				"where t:anatomical_entity or t:pathway " \
				"with nodes(p) as ns, range(0,length(nodes(p))-1) as idx " \
				"return [i in idx | [(ns[i]).name, labels(ns[i])[1]] ] as path " % (drug, max_path_len, disease)
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
		if 'protein' in labels_set:
			if 'pathway' in labels_set:
				has_prot_and_path.append(True)
			else:
				has_prot_and_path.append(False)
			if 'anatomical_entity' in labels_set:
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
			if node[1] == 'drug' and node[0] != drug:
				to_include = False  # don't include if you find another drug in the path
			if is_disont:
				if node[1] == 'disease' and node[0] != disease:
					to_include = False  # don't include if you find another disease in the path (and looking at disont)
			if not is_disont:
				if node[1] == 'disease':
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


def get_intermediate_path_length(source_type, source_name, intermediate_type, intermediate_name,
								 target_type, target_name, session=session, debug=False, max_path_len=1):
	"""
	get the smallest path length between a source and target where an intermediate node is specified
	:param source_type: source node type
	:param source_name: source node name
	:param intermediate_type: intermediate node type
	:param intermediate_name: intermediate node name
	:param target_type: target node type
	:param target_name: target node name
	:param session: neo4j session
	:param debug: just return the query (flag)
	:param max_path_len: maximum distance to pad the intermediate node from the source and the target
	:return: int (shortest path length of such paths)
	"""
	query = "match p = (s:%s{name:'%s'})-[*0..%d]-(i:%s{name:'%s'})-[*0..%d]-(t:%s{name:'%s'}) "\
			"return length(p) order by length(p) limit 1" % (source_type, source_name, max_path_len, intermediate_type,
															 intermediate_name, max_path_len, target_type, target_name)
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['length(p)']
	else:
		return np.inf


def anatomy_name_to_description(anatomy_name, session=session, debug=False):
	"""
	Get the description of an anatomy node
	:param anatomy_name: name of the node
	:param session: neo4j session
	:param debug: just return the query
	:return: a string (the description of the node)
	"""
	query = "match (n:anatomical_entity{name:'%s'}) return n.description" % anatomy_name
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['n.description']
	else:
		return "a tissue "


def protein_name_to_description(protein_name, session=session, debug=False):
	"""
	Get the description of an protein node
	:param protein_name: name of the node
	:param session: neo4j session
	:param debug: just return the query
	:return: a string (the description of the node)
	"""
	query = "match (n:protein{name:'%s'}) return n.description" % protein_name
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['n.description']
	else:
		return " "


def connect_to_pathway(path, pathway_near_intersection_names):
	"""
	For the given path and pathway node names, find the pathway that is closest to the path
	:param path: input path
	:param pathway_near_intersection_names: a set of pathway node names (looking for the closest)
	:return: the (a) pathway node that is closest to the given path
	"""
	proteins = []
	for node in path:
		if node[1] == "protein":
			proteins.append(node[0])
	if len(proteins) == 1:
		pathway_distances = []
		for pathway in pathway_near_intersection_names:
			path_dist = get_path_length("protein", proteins[0], "pathway", pathway)
			pathway_distances.append((pathway, path_dist))
	else:
		pathway_distances = []
		for pathway in pathway_near_intersection_names:
			path_dist = get_intermediate_path_length("protein", proteins[0], "pathway", pathway,
													"protein", proteins[1])
			pathway_distances.append((pathway, path_dist))
	# pick the smallest
	if pathway_distances:
		pathway_distances_sorted = sorted(pathway_distances, key=lambda tup: tup[1])
		smallest_pathway = pathway_distances_sorted[0][0]
		return smallest_pathway
	else:
		return False


def pathway_name_to_description(pathway_name, session=session, debug=False):
	"""
	Get the description of a pathway node
	:param pathway_name: pathway node name
	:param session: neo4j session
	:param debug: just return the query
	:return: string (pathway node description)
	"""
	query = "match (n:pathway{name:'%s'}) return n.description" % pathway_name
	if debug:
		return query
	res = session.run(query)
	res = [i for i in res]
	if res:
		return res[0]['n.description']
	else:
		return " "


def prioritize_on_gd(found_anat_names, disease_description):
	"""
	Given a list (found_anat_names) of pathway node names and a disease_description (string), compute the
	Google distance (based on NCBI search) between the anatomy names and the disease description
	:param found_anat_names: a list of anatomy node names
	:param disease_description: a string (disease description, MeSH term)
	:return: a list of tuples, first element is anatomy node name, second element is the google distance
	"""
	anat_name_google_distance = []
	for anat in found_anat_names:
		query = "match (n:anatomical_entity{name:'%s'}) return n.description" % anat
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
	"""
	Given a list of paths (paths), a list of indicies of those paths that contain reactome pathways (pathway_indicies)
	and a list of indicies of those paths that contain the anatot_anatomy nodes, find the proteins that are in both
	the pathway_indicies and anat_indicies, and get all the anatomy names in the paths.
	TODO: could possibly restrict to those anatomy names that are in the paths that contain proteins in both
	pathway and anatomy paths (but for completeness, why not include them all?)
	:param paths: a list of paths
	:param pathway_indicies: a list of ints (paths[index] has a reactome pathway in it)
	:param anat_indicies: a list of ints (paths[index] has a anatomical_entity in it)
	:return: a list of proteins in both, and a list of anatomy node names found
	"""
	found_path_names = set()
	for index in pathway_indicies:
		path = paths[index]
		for node in path:
			if node[1] == 'pathway':
				found_path_names.add(node[0])
	# Get the names of the found anatomy entities
	found_anat_names = set()
	for index in anat_indicies:
		path = paths[index]
		for node in path:
			if node[1] == 'anatomical_entity':
				found_anat_names.add(node[0])
	# get the proteins in the pathway and anat paths
	proteins_in_pathway = set()
	for index in pathway_indicies:
		path = paths[index]
		for node in path:
			if node[1] == "protein":
				proteins_in_pathway.add(node[0])
	proteins_in_anat = set()
	for index in anat_indicies:
		path = paths[index]
		for node in path:
			if node[1] == "protein":
				proteins_in_anat.add(node[0])
	in_both = proteins_in_pathway.intersection(proteins_in_anat)
	return in_both, found_anat_names


def print_results(path, pathway_near_intersection_names, best_anat, gd_max, drug, disease_description):
	"""
	Pretty print the results
	:param path: a given path to display
	:param pathway_near_intersection_names: a list of reactome pathways found nearby to this path
	:param best_anat: the best anatomy node name near to this path
	:param gd_max: the maximum google distance of all anatomies found
	:param drug: the target drug of interest (doid)
	:param disease_description: the human-readable description of the drug
	:return: None (print everything to screen)
	"""
	# Then display the results....
	pathway = connect_to_pathway(path, pathway_near_intersection_names)
	pathway_set = False
	if pathway:
		pathway_description = pathway_name_to_description(pathway)
	elif len(pathway_near_intersection_names) > 1:
		pathway_description = " a set of %d pathways " % len(pathway_near_intersection_names)
		pathway_set = True
	else:
		pathway_description = False
	path_proteins = []
	anatomy_name = False
	for node in path:
		if node[1] == "protein":
			path_proteins.append(node[0])
		if node[1] == "anatomical_entity":
			anatomy_name = node[0]
	conf = 1 - best_anat[anatomy_name] / gd_max
	to_print = "The drug %s " % drug
	to_print += "directly_interacts_with the protein %s (%s) " % (protein_name_to_description(path_proteins[0]), path_proteins[0])

	if pathway_description:
		if pathway_set:
			if len(path_proteins) > 1:
				to_print += "which is involved with %s and associated protein %s (%s) " % (
				pathway_description, protein_name_to_description(path_proteins[1]), path_proteins[1])
			else:
				to_print += "which is involved with (among others) the %s pathway " % pathway_description
		else:
			if len(path_proteins) > 1:
				to_print += "which is involved with (among others) the %s pathway and associated protein %s (%s) " % (
					pathway_description, protein_name_to_description(path_proteins[1]), path_proteins[1])
			else:
				to_print += "which is involved with (among others) the %s pathway " % pathway_description
	else:
		to_print += " which is involved with an unknown pathway"

	if anatomy_name:
		anatomy_description = anatomy_name_to_description(anatomy_name)
		to_print += "which is relevant to the %s " % anatomy_description
	to_print += "and alleviates symptoms of %s. " % disease_description
	to_print += "(Confidence %f)." % conf
	print(to_print)
