# Solution to question 1, this assumes the neo4j network has already been populated with the relevant data
import numpy as np
np.warnings.filterwarnings('ignore')
from collections import namedtuple
#from neo4j.v1 import GraphDatabase, basic_auth
import os
import Q1Utils
import argparse
import sys
import json

# Connection information for the neo4j server, populated with orangeboard
#driver = GraphDatabase.driver("bolt://lysine.ncats.io:7687", auth=basic_auth("neo4j", "precisionmedicine"))
#session = driver.session()

	
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

# TODO: the following two dictionaries would be relatively straightforward to programmatically create
# but given the time contraints, let's just hard code them now...

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

for key in q1_doid_to_disease.keys():
	q1_disease_to_doid[q1_doid_to_disease[key].lower()] = key

for key in q1_doid_to_disease.keys():
	q1_disease_to_doid[q1_doid_to_disease[key].upper()] = key

q1_doid_to_mesh = {'DOID:11476': 'Osteoporosis',
					'DOID:526': 'HIV Infections',
					'DOID:1498': 'Cholera',
					'DOID:4325': 'Ebola Infection',
					'DOID:12365': 'Malaria',
					'DOID:10573': 'Osteomalacia',
					'DOID:13810': 'Hypercholesterolemia',
					'DOID:9352': 'Diabetes Mellitus, Type 2',
					'DOID:2841': 'Asthma',
					'DOID:4989': 'Pancreatitis, Chronic',
					'DOID:10652': 'Alzheimer Disease',
					'DOID:5844': 'Myocardial Infarction',
					'DOID:11723': 'Muscular Dystrophy, Duchenne',
					'DOID:0060728': 'NGLY1 protein, human',
					'DOID:0050741': 'Alcoholism',
					'DOID:1470': 'Depressive Disorder, Major',
					'DOID:14504': 'Niemann-Pick Disease, Type C',
					'DOID:12858': 'Huntington Disease',
					'DOID:9270': 'Alkaptonuria',
					'DOID:10923': 'Anemia, Sickle Cell',
					'DOID:2055': 'Stress Disorders, Post-Traumatic'}

# Get the genetic diseases of interest
genetic_condition_to_omim = dict()
genetic_condition_to_mesh = dict()
fid = open(os.path.abspath('../../data/q1/Genetic_conditions_from_OMIM.txt'), 'r')
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

# These are highly connected, complex diseases (so likely to have the paths we're looking for), but
# not very informative. Will need to further refine the Markov chain to exclude paths through these nodes
disease_ignore_list = [
'OMIM:614389',
'OMIM:601367',
'OMIM:601665',
'OMIM:103780',
'OMIM:164230',
'OMIM:607154',
'OMIM:181500',
'OMIM:608516',
'OMIM:144700',
'OMIM:114480'
]
# May consider 'OMIM:617347', 'OMIM:238600' too



###################################################
# Start input

def answerQ1(input_disease, directed=True, max_path_len=3, verbose=False, use_json=False):  # I'm thinking directed true is best
	"""
	Answers Q1.
	:param input_disease: input disease (from the list)
	:param directed: if true, treats the graph as directed and looks for short paths, if false, looks for nodes with
	many paths from source to target
	:param max_path_len: maximum path length to consider
	:return: nothing, prints to screen
	"""
	#input_disease = 'cholera'  # input disease
	# TODO: synonyms for diseases
	if input_disease not in q1_disease_to_doid:
		if not use_json:
			print("Sorry, the disease %s is not one of the Q1 diseases." % input_disease)
		return
	doid = q1_disease_to_doid[input_disease]  # get the DOID for this disease

	# Getting nearby genetic diseases
	omims = Q1Utils.get_omims_connecting_to_fixed_doid(doid, directed=directed, max_path_len=max_path_len, verbose=verbose)

	if not omims:
		if verbose and not use_json:
			print("No nearby omims found. Please raise the max_path_len and try again.")
		return 1

	# NOTE: the following three can be mixed and matched in any order you please

	# get the ones that are nearby according to a random walk between source and target node
	omims = Q1Utils.refine_omims_graph_distance(omims, doid, directed=directed, max_path_len=max_path_len, verbose=verbose)

	# get the ones that have high probability according to a Markov chain model
	omims, paths_dict, prob_dict = Q1Utils.refine_omims_Markov_chain(omims, doid, max_path_len=max_path_len, verbose=verbose)

	# get the ones that have low google distance (are "well studied")
	omims = Q1Utils.refine_omims_well_studied(omims, doid, omim_to_mesh, q1_doid_to_mesh, verbose=verbose)

	if not omims:
		if verbose and not use_json:
			print("No omims passed all refinements. Please raise the max_path_len and try again.")
		return 1

	# Get rid of the self-loops:
	to_display_paths_dict = dict()
	to_display_probs_dict = dict()
	for omim in omims:
		if omim in disease_ignore_list\
			or q1_doid_to_disease[doid].lower() in omim_to_genetic_cond[omim].lower()\
			or omim_to_genetic_cond[omim].lower() in q1_doid_to_disease[doid].lower()\
			or q1_doid_to_mesh[doid].split(',')[0].lower() in omim_to_genetic_cond[omim].lower():
			# do something with the deleted guys?
			pass
		else:
			to_display_paths_dict[omim] = paths_dict[omim]
			to_display_probs_dict[omim] = prob_dict[omim]

	if not to_display_probs_dict:
		if verbose and not use_json:
			print("No omims passed all refinements. Please raise the max_path_len and try again.")
		return 1

	results_text = Q1Utils.display_results_str(doid, to_display_paths_dict, omim_to_genetic_cond, q1_doid_to_disease, probs=to_display_probs_dict)
	if not use_json:
		print(results_text)
	else:
		ret_obj = Q1Utils.get_results_object_model(doid, to_display_paths_dict, omim_to_genetic_cond, q1_doid_to_disease, probs=to_display_probs_dict)
		ret_obj['text'] = results_text
		print(json.dumps(ret_obj))


def main():
	parser = argparse.ArgumentParser(description="Runs the reasoning tool on Question 1",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-i', '--input_disease', type=str, help="Input disease", default="cholera")
	parser.add_argument('-v', '--verbose', action="store_true", help="Flag to turn on verbosity", default=False)
	parser.add_argument('-d', '--directed', action="store_true", help="To treat the graph as directed or not.", default=True)
	parser.add_argument('-m', '--max_path_len', type=int,
						help="Maximum graph path length for which to look for nearby omims", default=2)
	parser.add_argument('-a', '--all', action="store_true", help="Flag indicating you want to run it on all Q1 diseases",
						default=False)
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)

	if '-h' in sys.argv or '--help' in sys.argv:
		Q1Utils.session.close()
		Q1Utils.driver.close()

	# Parse and check args
	args = parser.parse_args()
	disease = args.input_disease.lower()
	verbose = args.verbose
	directed = args.directed
	max_path_len = args.max_path_len
	use_json = args.json
	all_d = args.all

	if all_d:
		for disease in q1_disease_to_doid.keys():
			print("\n")
			print(disease)
			if disease == 'asthma':  # if we incrementally built it up, we'd be waiting all day
				answerQ1(disease, directed=True, max_path_len=5, verbose=True, use_json=use_json)
			else:
				for len in [2, 3, 4]:  # start out with small path lengths, then expand outward until we find something
					res = answerQ1(disease, directed=True, max_path_len=len, verbose=True, use_json=use_json)
					if res != 1:
						break
				if res == 1:
					print("Sorry, no results found for %s" % disease)
	else:
		res = answerQ1(disease, directed=directed, max_path_len=max_path_len, verbose=verbose, use_json=use_json)
		if res == 1:
			if not use_json:
				print("Increasing path length and trying again...")
			res = answerQ1(disease, directed=directed, max_path_len=max_path_len + 1, verbose=verbose, use_json=use_json)
			if res == 1:
				if not use_json:
					print("Increasing path length and trying again...")
				res = answerQ1(disease, directed=directed, max_path_len=max_path_len + 2, verbose=verbose, use_json=use_json)

if __name__ == "__main__":
	main()
