# Solution to question 1, this assumes the neo4j network has already been populated with the relevant data
import numpy as np
from collections import namedtuple
from neo4j.v1 import GraphDatabase, basic_auth
import os
import QueryPubMedNGD
import math
import Q1Utils
import MarkovLearning

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



########################################################################################
# Main body

# Dictionary converting disease to disont_disease ID
# TODO: double check the DOID's, possibly add synonyms for the diseases
## seed all 21 diseases in the Orangeboard
q1_doid_to_disease = {'DOID:11476': 'osteoporosis',
					'DOID:526': 'HIV infectious disease',
					'DOID:1498': 'cholera',
					'DOID:4325': 'Ebola hemmorhagic fever',
					'DOID:12365': 'malaria',
					'DOID:10573': 'Osteomalacia',
					'DOID:13810': 'hypercholesterolemia',
					'DOID:9352': 'type 2 diabetes mellitus',
					'DOID:2841': 'asthma',
					'DOID:4989': 'pancreatitis',
					'DOID:10652': 'Alzheimer Disease',
					'DOID:5844': 'Myocardial Infarction',
					'DOID:11723': 'Duchenne Muscular Dystrophy',
					'DOID:0060728': 'NGLY1-deficiency',
					'DOID:0050741': 'Alcohol Dependence',
					'DOID:1470': 'major depressive disorder',
					'DOID:14504': 'Niemann-Pick disease',
					'DOID:12858': 'Huntington\'s Disease',
					'DOID:9270': 'Alkaptonuria',
					'DOID:10923': 'sickle cell anemia',
					'DOID:2055': 'post-traumatic stress disorder'}
q1_disease_to_doid = dict()
for key in q1_doid_to_disease.keys():
	q1_disease_to_doid[q1_doid_to_disease[key]] = key

# Get the genetic diseases of interest
genetic_condition_to_omim = dict()
genetic_condition_to_mesh = dict()
fid = open(os.path.abspath('../../q1/Genetic_conditions_from_OMIM.txt'), 'r')
i = 0
for line in fid.readlines():
	if i == 0:
		i += 1
		continue
	else:
		i += 1
	line = line.strip()
	condition_name = line.split('\t')[2]
	mim_id = int(line.split('\t')[1])
	mesh = condition_name.split(';')[0].lower()
	genetic_condition_to_omim[condition_name] = "OMIM:%d" % (mim_id)
	genetic_condition_to_mesh[condition_name] = mesh
fid.close()

omim_to_genetic_cond = dict()
omim_to_mesh = dict()
for condition in genetic_condition_to_omim.keys():
	omim_to_genetic_cond[genetic_condition_to_omim[condition]] = condition
	omim_to_mesh[genetic_condition_to_omim[condition]] = genetic_condition_to_mesh[condition]

###################################################
# Start input

def answerQ1(input_disease, directed=True, max_path_len=3):  # I'm thinking directed true is best
	"""
	Answers Q1.
	:param input_disease: input disease (from the list)
	:param directed: if true, treats the graph as directed and looks for short paths, if false, looks for nodes with
	many paths from source to target
	:param max_path_len: maximum path length to consider
	:return: nothing, prints to screen
	"""
	#input_disease = 'cholera'  # input disease
	#test_disease = 'malaria'
	#test_disease = 'asthma'
	#test_disease = 'Alkaptonuria'
	# TODO: synonyms for diseases
	if input_disease not in q1_disease_to_doid:
		print("Sorry, the disease %s is not one of the Q1 diseases." % input_disease)
		return
	doid = q1_disease_to_doid[input_disease]  # get the DOID for this disease
	#directed = True  # If directed is False, then the random walk can get spend a lot of time hanging out in
	# intermediate nodes: source-[lots of interconnected stuff]-target)
	# so these distances will be quite large. If directed is true, then some times there is not a directed path, so
	# the expected graph distance is zero (no paths)

	# Getting nearby genetic diseases
	omims = Q1Utils.get_omims_connecting_to_fixed_doid(session, doid, max_path_len=max_path_len)
	if not omims:
		print("No nearby omims found. Please raise the max_path_len and try again.")
		return

	# Computing expected graph distance
	exp_graph_distance_s_t = []  # source to target
	exp_graph_distance_t_s = []  # target to source
	for omim in omims:
		o_to_do, d_to_o = Q1Utils.expected_graph_distance(omim, doid, directed=directed, max_path_len=max_path_len+1)
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
	#to_select = np.where(s_t_np < distance_mean+distance_std)[0]  # those not more than 1*\sigma above the mean
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
	#print("path prioritized omims: ")
	#print(prioritized_omims)

	# Getting well-studied omims
	omims_GD = list()
	#for omim in omims:
	for omim in prioritized_omims:  # only the on the prioritized ones
		if omim in omim_to_mesh:
			res = QueryPubMedNGD.QueryPubMedNGD.normalized_google_distance(omim_to_mesh[omim], input_disease)
			omims_GD.append((omim, res))
	well_studied_omims = list()
	for tup in omims_GD:
		if tup[1] != math.nan and tup[1] > 0:
			well_studied_omims.append(tup)
	well_studied_omims = [item[0] for item in sorted(well_studied_omims, key=lambda tup: tup[1], reverse=True)]
	#print("Well-studied OMIMS:")
	#print(well_studied_omims)

	#############################################
	# Select omim's to report
	well_studied_prioritized = list(set(prioritized_omims).intersection(set(well_studied_omims)))
	#print("The following conditions may protect against %s:" % input_disease)
	#print(well_studied_prioritized)

	# Report them
	omim_list = well_studied_prioritized
	#display_results(session, omim_list, doid, omim_to_genetic_cond, q1_doid_to_disease)

	# Select likely paths and report them
	trained_MC, quad_to_matrix_index = MarkovLearning.trained_MC()  # initilize the Markov chain
	paths_dict_prob_all = dict()
	paths_dict_selected = dict()
	# get the probabilities for each path
	for omim in omim_list:
		path_name, path_type = Q1Utils.interleave_nodes_and_relationships(session, omim, doid, max_path_len=max_path_len+1)
		probabilities = []
		for path in path_type:
			prob = MarkovLearning.path_probability(trained_MC, quad_to_matrix_index, path)
			probabilities.append(prob)
		total_prob = np.sum(probabilities)  # add up all the probabilities of all paths TODO: could also take the mean, etc.
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
		paths_dict_prob_all[omim] = (path_name, path_type, total_prob)

	# now select which omims I actually want to display
	omim_probs = []
	for omim in omim_list:
		omim_probs.append(paths_dict_prob_all[omim][2])
	omim_probs_np = np.array(omim_probs)
	total = np.sum(omim_probs_np)
	omim_probs_np /= total
	omim_probs_np_mean = np.mean(omim_probs_np)
	to_select = np.where(omim_probs_np >= omim_probs_np_mean)[0]  # TODO: see if we should leave un-normalized
	selected_probs = dict()
	for index in to_select:
		selected_omim = omim_list[index]
		path_name, path_type, prob = paths_dict_prob_all[selected_omim]
		selected_probs[selected_omim] = prob/total
		paths_dict_selected[selected_omim] = (path_name, path_type)

	Q1Utils.display_results(doid, paths_dict_selected, omim_to_genetic_cond, q1_doid_to_disease, probs=selected_probs)

def run_on_all():
	for disease in q1_disease_to_doid.keys():
		answerQ1(disease)



