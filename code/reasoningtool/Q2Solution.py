import numpy as np
np.warnings.filterwarnings('ignore')
import os
import Q2Utils
import requests_cache
requests_cache.install_cache('orangeboard')
import sys
import argparse

#TODO: After having access to training data, re-write this to use the Markov chain approach. This will be much more
# extensible (not to mention faster)

# Import the Q2 drugs and conditions
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


#disease = 'DOID:1686'
#disease_description = 'glaucoma'
#drug = 'physostigmine'

#disease = "DOID:10652"
#disease_description = "Alzheimer Disease"
#drug = "MEMANTINE".lower()


def answerQ2(drug, disease_description):
	disease = drug_to_disease_doid[drug]  # doid
	if Q2Utils.has_disease(disease):
		is_disont = True
	else:
		is_disont = False

	# get shortest paths between drug and disease
	paths = []
	i = 2
	while not paths:
		paths = Q2Utils.node_name_and_label_in_path(drug, disease, max_path_len=i, debug=False, disont=is_disont)
		i += 1
		if i > 4:
			break

	if not paths:
		print("a Sorry, I could not find any paths connecting %s to %s via protein, pathway, tissue, and phenotype." % (drug, disease_description))
		return 1

	# delete those that go through other drugs or diseases
	paths = Q2Utils.delete_paths_through_other_drugs_diseases(paths, drug, disease)
	if not paths:
		print("b Sorry, I could not find any paths connecting %s to %s via protein, pathway, tissue, and phenotype." % (drug, disease_description))
		return 1

	# Get: 1. Number of distinct node labels in each path, 2. if the path has a reactome pathway in it and
	# 3. If the path has an anatomy node in it
	num_labels, has_prot_and_path, has_prot_and_anat = Q2Utils.look_for_pathway_and_anat(paths)

	# Location of paths with pathway and anatomy
	pathway_indicies = np.where(np.array(has_prot_and_path))[0]  # paths that have reactome pathway
	anat_indicies = np.where(np.array(has_prot_and_anat))[0]  # paths that have anatomy/tissue in it

	# TODO: See if we can shortcircuit the rest if we have a single path with anatomy and pathway inside it
	# Could also ignore since there's no reason the anatomy is the right one
	# See if we get lucky and we have anatomy and pathway in a single path
	#found_single_path = False
	#pathway_and_anat_indicies = set(pathway_indicies).intersection(set(anat_indicies))
	#if pathway_and_anat_indicies:
	#	#print("RETURN THIS RESULT: " + str(paths[list(pathway_and_anat_indicies)[0]]))
	#	found_single_path = True

	# Otherwise, try to connect them up
	# get the names of the found pathway entities
	proteins_in_both, found_anat_names = Q2Utils.get_proteins_in_both(paths, pathway_indicies, anat_indicies)

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

	# Prioritize the anatomy based on google distance
	anat_name_google_distance = Q2Utils.prioritize_on_gd(found_anat_names, disease_description)

	# Get the top three
	anat_name_google_distance_sorted = sorted(anat_name_google_distance, key=lambda tup: tup[1])
	num_select = min(3, len(anat_name_google_distance_sorted))
	best_anat = dict()
	for i in range(num_select):
		anat_name = anat_name_google_distance_sorted[i][0]
		anat_gd = anat_name_google_distance_sorted[i][1]
		best_anat[anat_name] = anat_gd

	# Now, for these anatomy, get the relevant paths
	best_anat_paths = []
	best_anat_probs = dict()
	for path in paths:
		for node in path:
			if node[1] == "anatont_anatomy":
				if node[0] in best_anat.keys():
					best_anat_paths.append(path)
					best_anat_probs[tuple(path)] = best_anat[node[0]]
					#print(path)

	# get confidences (based on google distances)
	gds = np.array([i[1] for i in anat_name_google_distance_sorted])
	num_non_inf = np.count_nonzero(~np.isinf(gds))
	if num_non_inf == 0 or gds == []:
		print("c Sorry, I could not find any paths connecting %s to %s via protein, pathway, tissue, and phenotype." % (
		drug, disease_description))
		return 1
	else:
		gd_max = np.ma.masked_invalid(gds).max()

	# Sort the results
	best_anat_paths = sorted(best_anat_paths, key=lambda key: best_anat_probs[tuple(key)])

	# Then display the results....
	print("The possible clinical outcome pathways include: ")
	#if not found_single_path:
	for i in range(len(best_anat_paths)):
		print("%d. " % (i+1))
		Q2Utils.print_results(best_anat_paths[i], pathway_near_intersection_names, best_anat, gd_max, drug, disease_description)




#i = 1
#drug = list(drug_to_disease_doid.keys())[i]  # drug name
#disease = drug_to_disease_doid[drug]  # doid
#disease_description = disease_doid_to_description[disease]  # disease description
#drug = "fleroxacin"
#disease = "DOID:874"
#disease_description = "Pneumonia, Bacterial"
#print("%s %s %s" % (drug, disease, disease_description))
#answerQ2(drug, disease_description)

def main():
	parser = argparse.ArgumentParser(description="Runs the reasoning tool on Question 2",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-r', '--drug', type=str, help="Input drug")
	parser.add_argument('-d', '--disease', type=str, help="Input disease (description)")
	parser.add_argument('-a', '--all', action="store_true", help="Flag indicating you want to run it on all Q2 drugs + diseases",
						default=False)
	# Parse and check args
	args = parser.parse_args()
	drug = args.drug
	disease_description = args.disease
	all_d = args.all

	if all_d:
		for drug in list(drug_to_disease_doid.keys()):
			disease = drug_to_disease_doid[drug]  # doid
			disease_description = disease_doid_to_description[disease]  # disease description
			print("\n")
			print((drug, disease_description))
			res = answerQ2(drug, disease_description)
	else:
		res = answerQ2(drug, disease_description)

if __name__ == "__main__":
	main()



disease = 'DOID:1686'
disease_description = 'glaucoma'
drug = 'physostigmine'