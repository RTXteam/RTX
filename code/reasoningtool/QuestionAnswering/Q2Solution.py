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
try:
	import QueryNCBIeUtils
except ImportError:
	sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Go up one level and look for it
	import QueryNCBIeUtils
QueryNCBIeUtils = QueryNCBIeUtils.QueryNCBIeUtils()

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
	node_paths, edge_paths, weights = RU.get_top_shortest_paths(g, drug_name, disease_name, k)
	actual_k = len(weights)  # since there may be less than k paths

	# For each of these paths, connect the protein to a pathway
	# First, grab the proteins and locations
	proteins_per_path = []
	proteins_per_path_locations = []
	for path in node_paths:
		for i, node in enumerate(path):
			if "uniprot_protein" in node["labels"]:
				proteins_per_path.append(node)
				proteins_per_path_locations.append(i)
				break

	# Connect a reactome pathway to the proteins (only for the first seen protein in each path)
	pathways_per_path = []
	for protein in proteins_per_path:
		pathways = RU.get_one_hop_target('uniprot_protein', protein['names'], 'reactome_pathway', 'is_member_of')
		pathways_per_path.append(pathways)

	# Delete those elements that don't have a reactome pathway
	for i, pathways in enumerate(pathways_per_path):
		if not pathways:
			del node_paths[i]
			del edge_paths[i]
			del weights[i]
			del proteins_per_path[i]
			del proteins_per_path_locations[i]
			del pathways_per_path[i]

	# Look for the pathway that has both a small GD between protein and disease
	max_gd = 10
	best_pathways_per_path = []
	best_pathways_per_path_gd = []
	disease_common_name = RU.get_node_property(disease_name, 'description', node_label='disont_disease')
	for j, pathways in enumerate(pathways_per_path):
		smallest_gd = np.inf
		best_pathway = ""  # TODO: sometimes there is no best pathway? ('fesoterodine', 'Urinary Bladder, Overactive')
		for pathway in pathways:
			protein_pathway_gd = QueryNCBIeUtils.normalized_google_distance(
				QueryNCBIeUtils.get_uniprot_names(proteins_per_path[j]['names']),
				QueryNCBIeUtils.get_reactome_names(pathway),
				mesh1=False, mesh2=False)
			if np.isnan(protein_pathway_gd):
				protein_pathway_gd = max_gd

			pathway_disease_gd = QueryNCBIeUtils.normalized_google_distance(disease_common_name,
																			QueryNCBIeUtils.get_reactome_names(pathway),
																			mesh1=True, mesh2=False)
			if np.isnan(pathway_disease_gd):
				pathway_disease_gd = max_gd

			if protein_pathway_gd + pathway_disease_gd < smallest_gd:
				smallest_gd = protein_pathway_gd + pathway_disease_gd
				best_pathway = pathway
		best_pathways_per_path.append(best_pathway)
		best_pathways_per_path_gd.append(smallest_gd)

	# Insert the best pathway into the node_path
	for i in range(len(node_paths)):
		best_pathway = best_pathways_per_path[i]
		# Convert the pathway name to a graph and grab the resulting data
		graph = RU.get_node_as_graph(best_pathway)
		best_pathway_with_node_data = list(graph.nodes(data=True)).pop()[1]
		# same for the edge
		graph = RU.get_shortest_subgraph_between_nodes(proteins_per_path[i]["names"], "uniprot_protein", best_pathway,
													   "reactome_pathway", max_path_len=1, limit=1, directed=False)
		edge_data = list(graph.edges(data=True)).pop()[2]
		best_pathway_gd = best_pathways_per_path_gd[i]
		protein_location = proteins_per_path_locations[i]
		node_paths[i].insert(protein_location + 1, best_pathway_with_node_data)
		edge_paths[i].insert(protein_location, edge_data)
		weights[i] += best_pathway_gd

	# resort the paths
	node_paths = [x for _, x in sorted(zip(weights, node_paths), key=lambda pair: pair[0])]
	edge_paths = [x for _, x in sorted(zip(weights, edge_paths), key=lambda pair: pair[0])]
	weights.sort()

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
		to_print += ". Distance (smaller is better): %f." % weights[path_ind]
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



