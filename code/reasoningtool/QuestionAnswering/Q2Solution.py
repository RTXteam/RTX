import numpy as np
np.warnings.filterwarnings('ignore')
import os
import ReasoningUtilities as RU
import requests_cache
requests_cache.install_cache('orangeboard')
import argparse
from itertools import compress
import sys
import CustomExceptions

drug_to_disease_doid = dict()
disease_doid_to_description = dict()
with open(os.path.abspath('../../../data/q2/q2-drugandcondition-list-mapped.txt'), 'r') as fid:
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


def answerQ2(drug_name, disease_name, k):
	"""
	Find the clinical outcome pathway connecting the drug to the disease
	:param drug_name: a name of a drug (node.name in the KG)
	:param disease_name: a name of a disease (node.name in the KG, eg DOID:)
	:param k: Number of paths to return (int)
	:return: Text answer
	"""


	# get the relevant subgraph between the source and target nodes
	try:  # First look for COP's where the gene is associated to the disease
		g = RU.return_subgraph_through_node_labels(drug_name, 'pharos_drug', disease_name, 'disont_disease',
													['uniprot_protein', 'anatont_anatomy', 'phenont_phenotype'],
													with_rel=['uniprot_protein', 'gene_assoc_with', 'disont_disease'],
													directed=False)
	except CustomExceptions.EmptyCypherError:
		try:  # Then look for any sort of COP
			g = RU.return_subgraph_through_node_labels(drug_name, 'pharos_drug', disease_name, 'disont_disease',
													['uniprot_protein', 'anatont_anatomy', 'phenont_phenotype'],
													directed=False)
		except CustomExceptions.EmptyCypherError:
			try:  # Then look for any sort of connection between source and target
				g = RU.get_shortest_subgraph_between_nodes(drug_name, 'pharos_drug', disease_name, 'disont_disease',
															max_path_len=4, limit=50, debug=False, directed=False)
			except CustomExceptions.EmptyCypherError:
				print(
					"Sorry, I could not find any paths connecting %s to %s via protein, pathway, tissue, and phenotype. "
					"The drug and/or disease may not be one of the entities I know about, or they do not connect via a known "
					"pathway, tissue, and phenotype (understudied)" %
					(drug_name, RU.get_node_property(disease_name, 'description')))
				return 1
	# Decorate with normalized google distance
	RU.weight_graph_with_google_distance(g)

	# Get the top k paths
	node_paths, edge_paths, lengths = RU.get_top_shortest_paths(g, drug_name, disease_name, k)
	actual_k = len(lengths)  # since there may be less than k paths

	# TODO: For each of these paths, connect the protein to a pathway

	# Then display the results....
	print("The possible clinical outcome pathways include: ")
	for path_ind in range(len(node_paths)):
		node_path = node_paths[path_ind]
		edge_path = edge_paths[path_ind]
		to_print = ""
		for node_index in range(len(node_path)):
			to_print += " " + str(node_path[node_index]['description'])
			if node_index < len(edge_path):
				to_print += " -" + str(edge_path[node_index]['type']) +"->"
		print(to_print)


def main():
	parser = argparse.ArgumentParser(description="Runs the reasoning tool on Question 2",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-r', '--drug', type=str, help="Input drug (name in the graph, eg. 'naproxen')")
	parser.add_argument('-d', '--disease', type=str, help="Input disease (Identifier in the graph, eg 'DOID:8398')")
	parser.add_argument('-a', '--all', action="store_true", help="Flag indicating you want to run it on all Q2 drugs + diseases",
						default=False)
	parser.add_argument('-k', '--kpaths', type=int, help="Number of paths to return.", default=10)

	if '-h' in sys.argv or '--help' in sys.argv:
		RU.session.close()
		RU.driver.close()

	# Parse and check args
	args = parser.parse_args()
	drug = args.drug
	disease = args.disease
	all_d = args.all
	k = args.kpaths

	if all_d:
		for drug in list(drug_to_disease_doid.keys()):
			disease = drug_to_disease_doid[drug]  # doid
			disease_description = disease_doid_to_description[disease]  # disease description
			print("\n")
			print((drug, disease_description))
			res = answerQ2(drug, disease, k)
	else:
		res = answerQ2(drug, disease, k)

if __name__ == "__main__":
	main()



