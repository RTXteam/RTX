import numpy as np
np.warnings.filterwarnings('ignore')
import os
import ReasoningUtilities as RU
import requests_cache
import re
#requests_cache.install_cache('orangeboard')
# specifiy the path of orangeboard database
tmppath = re.compile(".*/RTX/")
dbpath = tmppath.search(os.path.realpath(__file__)).group(0) + 'data/orangeboard'
requests_cache.install_cache(dbpath)
import argparse
from itertools import compress
import sys
import CustomExceptions
try:
	import QueryNCBIeUtils
except ImportError:
	sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../kg-construction')))  # Go up one level and look for it
	import QueryNCBIeUtils

QueryNCBIeUtils =QueryNCBIeUtils.QueryNCBIeUtils()

import FormatOutput
import networkx as nx


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


def answerQ2(drug_name, disease_name, k, use_json=False, max_gd=1):
	"""
	Find the clinical outcome pathway connecting the drug to the disease
	:param drug_name: a name of a drug (node.id in the KG)
	:param disease_name: a name of a disease (node.id in the KG, eg DOID:)
	:param k: Number of paths to return (int)
	:param use_json: if you want the answers as JSON.
	:param max_gd: maximum value for google distance
	:return: Text answer
	"""
	response = FormatOutput.FormatResponse(2)
	if not RU.node_exists_with_property(drug_name, 'id'):
		error_message = "Sorry, the drug %s is not yet in our knowledge graph." % drug_name
		error_code = "DrugNotFound"
		if not use_json:
			print(error_message)
			return 1
		else:
			response.add_error_message(error_code, error_message)
			response.print()
			return 1
	if not RU.node_exists_with_property(disease_name, 'id'):
		error_message = "Sorry, the disease %s is not yet in our knowledge graph." % disease_name
		error_code = "DiseaseNotFound"
		if not use_json:
			print(error_message)
			return 1
		else:
			response.add_error_message(error_code, error_message)
			response.print()
			return 1

	# TODO: could dynamically get the terminal node label as some are (drug, phenotype) pairs
	# get the relevant subgraph between the source and target nodes
	try:  # First look for COP's where the gene is associated to the disease
		#g = RU.return_subgraph_through_node_labels(drug_name, 'chemical_substance', disease_name, 'disease',
		#											['protein', 'anatomical_entity', 'phenotypic_feature'],
		#											with_rel=['protein', 'gene_associated_with_condition', 'disease'],
		#											directed=False)
		g = RU.return_subgraph_through_node_labels(drug_name, 'chemical_substance', disease_name, 'disease',
												   ['protein', 'anatomical_entity', 'phenotypic_feature'],
												   directed=False)
	except CustomExceptions.EmptyCypherError:
		try:  # Then look for any sort of COP
			g = RU.return_subgraph_through_node_labels(drug_name, 'chemical_substance', disease_name, 'disease',
													['protein', 'anatomical_entity', 'phenotypic_feature'],
													directed=False)
		except CustomExceptions.EmptyCypherError:
			try:  # Then look for any sort of connection between source and target
				g = RU.get_shortest_subgraph_between_nodes(drug_name, 'chemical_substance', disease_name, 'disease',
															max_path_len=4, limit=50, debug=False, directed=False)
			except CustomExceptions.EmptyCypherError:
				error_code = "NoPathsFound"
				try:
					error_message = "Sorry, I could not find any paths connecting %s to %s via protein, pathway, "\
						"tissue, and phenotype. The drug and/or disease may not be one of the entities I know about, or they "\
						"do not connect via a known pathway, tissue, and phenotype (understudied)" % (
						RU.get_node_property(drug_name, 'name'), RU.get_node_property(disease_name, 'name'))
				except:
					error_message = "Sorry, I could not find any paths connecting %s to %s via protein, pathway, "\
						"tissue, and phenotype. The drug and/or disease may not be one of the entities I know about, or they "\
						"do not connect via a known pathway, tissue, and phenotype (understudied)" % (RU.get_node_property(drug_name, 'name'), RU.get_node_property(disease_name, 'name'))
				if not use_json:
					print(error_message)
					return 1
				else:
					response.add_error_message(error_code, error_message)
					response.print()
					return 1
	# Decorate with normalized google distance
	disease_descr = RU.get_node_property(disease_name, 'name')
	# include context in the google distance TODO: this may not actually help things... need to test
	RU.weight_graph_with_google_distance(g, context_node_id=disease_name, context_node_descr=disease_descr, default_value=max_gd)

	# Decorate with drug binding probability (1-x since these will be multiplicatively merged)
	#RU.weight_graph_with_property(g, 'probability', transformation=lambda x: 1-x, default_value=2)
	max_prob_weight = 100
	RU.weight_graph_with_property(g, 'probability', transformation=lambda x: min(1/float(x), max_prob_weight), default_value=max_prob_weight)

	# Combine the properties
	RU.merge_graph_properties(g, ['gd_weight', 'probability'], 'merged', operation=lambda x,y: x*y)

	# Get the top k paths
	node_paths, edge_paths, weights = RU.get_top_shortest_paths(g, drug_name, disease_name, k, property='merged')
	actual_k = len(weights)  # since there may be less than k paths

	# For each of these paths, connect the protein to a pathway
	# First, grab the proteins and locations
	proteins_per_path = []
	proteins_per_path_locations = []
	for path in node_paths:
		for i, node in enumerate(path):
			if "protein" in node["labels"]:
				proteins_per_path.append(node)
				proteins_per_path_locations.append(i)
				break

	# Connect a reactome pathway to the proteins (only for the first seen protein in each path)
	pathways_per_path = []
	for protein in proteins_per_path:
		pathways = RU.get_one_hop_target('protein', protein['names'], 'pathway', 'participates_in')
		pathways_per_path.append(pathways)

	# Delete those elements that don't have a reactome pathway
	bad_paths = []
	for i, pathways in enumerate(pathways_per_path):
		if not pathways:
			bad_paths.append(i)
	for i in reversed(bad_paths):
		del node_paths[i]
		del edge_paths[i]
		del weights[i]
		del proteins_per_path[i]
		del proteins_per_path_locations[i]
		del pathways_per_path[i]

	# Look for the pathway that has both a small GD between protein and disease
	best_pathways_per_path = []
	best_pathways_per_path_gd = []
	disease_common_name = RU.get_node_property(disease_name, 'name', node_label='disease')
	for j, pathways in enumerate(pathways_per_path):
		smallest_gd = np.inf
		best_pathway = ""
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

	# Delete those elements that don't have a best reactome pathway
	bad_paths = []
	for i, pathways in enumerate(best_pathways_per_path):
		if not pathways:
			bad_paths.append(i)
	for i in reversed(bad_paths):
		del node_paths[i]
		del edge_paths[i]
		del weights[i]
		del proteins_per_path[i]
		del proteins_per_path_locations[i]
		del pathways_per_path[i]
		del best_pathways_per_path[i]
		del best_pathways_per_path_gd[i]

	# Insert the best pathway into the node_path
	for i in range(len(node_paths)):
		best_pathway = best_pathways_per_path[i]
		# Convert the pathway name to a graph and grab the resulting data
		graph = RU.get_node_as_graph(best_pathway)
		best_pathway_with_node_data = list(graph.nodes(data=True)).pop()[1]
		# same for the edge
		graph = RU.get_shortest_subgraph_between_nodes(proteins_per_path[i]["names"], "protein", best_pathway,
													   "pathway", max_path_len=1, limit=1, directed=False)
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
	if not use_json:
		print("The possible clinical outcome pathways include: ")
		for path_ind in range(len(node_paths)):
			node_path = node_paths[path_ind]
			edge_path = edge_paths[path_ind]
			to_print = ""
			for node_index in range(len(node_path)):
				to_print += " (" + str(node_path[node_index]['names']) + "," + str(node_path[node_index]['properties']['name']) + ")"
				if node_index < len(edge_path):
					to_print += " -[" + str(edge_path[node_index]['type']) + "]-"
			#to_print += ". Distance (smaller is better): %f." % weights[path_ind]
			to_print += ". Confidence (larger is better): %f." % (1-weights[path_ind]/float(len(edge_path)*max_gd*max_prob_weight))
			print(to_print)
	else:  # you want the result object model
		for path_ind in range(len(node_paths)):
			# Format the free text portion
			node_path = node_paths[path_ind]
			edge_path = edge_paths[path_ind]
			to_print = ""
			for node_index in range(len(node_path)):
				to_print += " " + str(node_path[node_index]['properties']['name'])
				if node_index < len(edge_path):
					to_print += " -" + str(edge_path[node_index]['type']) + "->"
			#to_print += ". Distance (smaller is better): %f." % weights[path_ind]
			conf = 1-weights[path_ind]/float(len(edge_path)*max_gd*max_prob_weight)
			to_print += ". Confidence (larger is better): %f." % conf
			# put the nodes/edges into a networkx graph
			g = nx.Graph()
			nodes_to_add = []
			edges_to_add = []
			for node in node_path:
				nodes_to_add.append((node['properties']['UUID'], node))
			for edge in edge_path:
				edges_to_add.append((edge['properties']['source_node_uuid'], edge['properties']['target_node_uuid'], edge))
			g.add_nodes_from(nodes_to_add)
			g.add_edges_from(edges_to_add)
			# populate the response. Quick hack to convert
			#response.add_subgraph(g.nodes(data=True), g.edges(data=True), to_print, 1-weights[path_ind]/float(max([len(x) for x in edge_paths])*max_gd))
			response.add_subgraph(g.nodes(data=True), g.edges(data=True), to_print, conf)
		response.add_neighborhood_graph(g.nodes(data=True), g.edges(data=True),	confidence=None)  # Adding the neighborhood graph
		response.print()


def main():
	parser = argparse.ArgumentParser(description="Runs the reasoning tool on Question 2",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-r', '--drug', type=str, help="Input drug (name in the graph, eg. 'CHEMBL154' (naproxen))", default='ChEMBL:154')
	parser.add_argument('-d', '--disease', type=str, help="Input disease (Identifier in the graph, eg 'DOID:8398')", default='DOID:8398')
	parser.add_argument('-a', '--all', action="store_true", help="Flag indicating you want to run it on all Q2 drugs + diseases",
						default=False)
	parser.add_argument('-k', '--kpaths', type=int, help="Number of paths to return.", default=10)
	parser.add_argument('-j', '--json', action="store_true", help="Flag indicating you want the results in JSON format.", default=False)

	if '-h' in sys.argv or '--help' in sys.argv:
		RU.session.close()
		RU.driver.close()

	# Parse and check args
	args = parser.parse_args()
	drug = args.drug
	disease = args.disease
	all_d = args.all
	k = args.kpaths
	use_json = args.json

	if all_d:
		for i, drug in enumerate(list(drug_to_disease_doid.keys())):
			disease = drug_to_disease_doid[drug]  # doid
			disease_description = disease_doid_to_description[disease]  # disease description
			print("\n")
			print((drug, disease_description, disease))
			print(i)
			res = answerQ2(drug, disease, k, use_json)
	else:
		res = answerQ2(drug, disease, k, use_json)

if __name__ == "__main__":
	main()



