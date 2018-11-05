# solves the SME workflow #1: drug repurposing based on rare diseases

import os
import sys
import argparse
# PyCharm doesn't play well with relative imports + python console + terminal
try:
	from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import ReasoningUtilities as RU

import FormatOutput
import networkx as nx
try:
	from QueryCOHD import QueryCOHD
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	try:
		from QueryCOHD import QueryCOHD
	except ImportError:
		sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kg-construction'))
		from QueryCOHD import QueryCOHD

from COHDUtilities import COHDUtilities
import SimilarNodesInCommon
import CustomExceptions
import numpy as np
import fisher_exact
import NormGoogleDistance
NormGoogleDistance = NormGoogleDistance.NormGoogleDistance()
# TODO: Temp file path names etc
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLDrugRepurposing/FWPredictor'))
import predictor
p = predictor.predictor(model_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLDrugRepurposing/FWPredictor/LogModel.pkl'))
p.import_file(None, graph_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLDrugRepurposing/FWPredictor/rel_max.emb.gz'), map_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MLDrugRepurposing/FWPredictor/map.csv'))


class SMEDrugRepurposingFisher:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=25):

		num_input_disease_symptoms = 25  # number of representative symptoms of the disease to keep
		num_omim_keep = 25  # number of genetic conditions to keep
		num_protein_keep = 25  # number of implicated proteins to keep
		num_pathways_keep = 25  # number of pathways to keep
		num_pathway_proteins_selected = 25  # number of proteins enriched for the above pathways to select
		num_drugs_keep = num_show  # number of drugs that target those proteins to keep
		num_paths = 2  # number of paths to keep for each drug selected

		# Initialize the response class
		response = FormatOutput.FormatResponse(6)
		response.response.table_column_names = ["disease name", "disease ID", "drug name", "drug ID", "confidence"]

		# get the description of the disease
		disease_description = RU.get_node_property(disease_id, 'name')

		# Find symptoms of disease
		# symptoms = RU.get_one_hop_target("disease", disease_id, "phenotypic_feature", "has_phenotype")
		# symptoms_set = set(symptoms)
		(symptoms_dict, symptoms) = RU.top_n_fisher_exact([disease_id], "disease", "phenotypic_feature", rel_type="has_phenotype", n=num_input_disease_symptoms)
		symptoms_set = set(symptoms)
		# check for an error
		if not symptoms_set:
			error_message = "I found no phenotypic_features for %s." % disease_description
			if not use_json:
				print(error_message)
				return
			else:
				error_code = "NoPathsFound"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				response.print()
				return

		# Find diseases enriched for that phenotype
		path_type = ["gene_mutations_contribute_to", "protein", "participates_in", "pathway", "participates_in",
					 "protein", "physically_interacts_with", "chemical_substance"]
		(genetic_diseases_dict, genetic_diseases_selected) = RU.top_n_fisher_exact(symptoms, "phenotypic_feature",
																				   "disease", rel_type="has_phenotype",
																				   n=num_omim_keep, curie_prefix="OMIM",
																				   on_path=path_type,
																				   exclude=disease_id)

		if not genetic_diseases_selected:
			error_message = "I found no diseases connected to phenotypes of %s." % disease_description
			if not use_json:
				print(error_message)
				return
			else:
				error_code = "NoPathsFound"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				response.print()
				return

		# find the most representative proteins in these diseases
		path_type = ["participates_in", "pathway", "participates_in",
					 "protein", "physically_interacts_with", "chemical_substance"]
		(implicated_proteins_dict, implicated_proteins_selected) = RU.top_n_fisher_exact(genetic_diseases_selected,
																						 "disease", "protein",
																						 rel_type="gene_mutations_contribute_to",
																						 n=num_protein_keep,
																						 on_path=path_type)

		if not implicated_proteins_selected:
			error_message = "I found no proteins connected to diseases connected to phenotypes of %s." % disease_description
			if not use_json:
				print(error_message)
				return
			else:
				error_code = "NoPathsFound"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				response.print()
				return

		# find enriched pathways from those proteins
		path_type = ["participates_in", "protein", "physically_interacts_with", "chemical_substance"]
		(pathways_selected_dict, pathways_selected) = RU.top_n_fisher_exact(implicated_proteins_selected, "protein",
																			"pathway", rel_type="participates_in",
																			n=num_pathways_keep, on_path=path_type)

		if not pathways_selected:
			error_message = "I found no pathways connected to proteins connected to diseases connected to phenotypes of %s." % disease_description
			if not use_json:
				print(error_message)
				return
			else:
				error_code = "NoPathsFound"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				response.print()
				return

		# find proteins enriched for those pathways
		path_type = ["physically_interacts_with", "chemical_substance"]
		(pathway_proteins_dict, pathway_proteins_selected) = RU.top_n_fisher_exact(pathways_selected, "pathway",
																				   "protein",
																				   rel_type="participates_in",
																				   n=num_pathway_proteins_selected,
																				   on_path=path_type)

		if not pathway_proteins_selected:
			error_message = "I found no proteins connected to pathways connected to proteins connected to diseases connected to phenotypes of %s." % disease_description
			if not use_json:
				print(error_message)
				return
			else:
				error_code = "NoPathsFound"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				response.print()
				return

		# find drugs enriched for targeting those proteins
		(drugs_selected_dict, drugs_selected) = RU.top_n_fisher_exact(pathway_proteins_selected, "protein",
																	  "chemical_substance",
																	  rel_type="physically_interacts_with",
																	  n=num_drugs_keep)

		if not drugs_selected:
			error_message = "I found no drugs connected toproteins connected to pathways connected to proteins connected to diseases connected to phenotypes of %s." % disease_description
			if not use_json:
				print(error_message)
				return
			else:
				error_code = "NoPathsFound"
				response = FormatOutput.FormatResponse(3)
				response.add_error_message(error_code, error_message)
				response.print()
				return

		# Next, find the most likely paths
		# extract the relevant subgraph
		path_type = ["disease", "has_phenotype", "phenotypic_feature", "has_phenotype", "disease",
					 "gene_mutations_contribute_to", "protein", "participates_in", "pathway", "participates_in",
					 "protein", "physically_interacts_with", "chemical_substance"]
		g = RU.get_subgraph_through_node_sets_known_relationships(path_type,
																  [[disease_id], symptoms, genetic_diseases_selected,
																   implicated_proteins_selected, pathways_selected,
																   pathway_proteins_selected, drugs_selected])

		# decorate graph with fisher p-values
		# get dict of id to nx nodes
		nx_node_to_id = nx.get_node_attributes(g, "names")
		nx_id_to_node = dict()
		# reverse the dictionary
		for node in nx_node_to_id.keys():
			id = nx_node_to_id[node]
			nx_id_to_node[id] = node

		i = 0
		for u, v, d in g.edges(data=True):
			u_id = nx_node_to_id[u]
			v_id = nx_node_to_id[v]
			# decorate correct nodes
			# input disease to symptoms, decorated by symptom p-value
			if (u_id in symptoms_set and v_id == disease_id) or (v_id in symptoms_set and u_id == disease_id):
				try:
					d["p_value"] = symptoms_dict[v_id]
				except:
					d["p_value"] = symptoms_dict[u_id]
				continue
			# symptom to disease, decorated by disease p-value
			if (u_id in symptoms_set and v_id in genetic_diseases_dict) or (
					v_id in symptoms_set and u_id in genetic_diseases_dict):
				try:
					d["p_value"] = genetic_diseases_dict[v_id]
				except:
					d["p_value"] = genetic_diseases_dict[u_id]
				continue
			# disease to protein
			if (u_id in genetic_diseases_dict and v_id in implicated_proteins_dict) or (
					v_id in genetic_diseases_dict and u_id in implicated_proteins_dict):
				try:
					d["p_value"] = implicated_proteins_dict[v_id]
				except:
					d["p_value"] = implicated_proteins_dict[u_id]
				continue
			# protein to pathway
			if (u_id in implicated_proteins_dict and v_id in pathways_selected_dict) or (
					v_id in implicated_proteins_dict and u_id in pathways_selected_dict):
				try:
					d["p_value"] = pathways_selected_dict[v_id]
				except:
					d["p_value"] = pathways_selected_dict[u_id]
				continue
			# pathway to protein
			if (u_id in pathways_selected_dict and v_id in pathway_proteins_dict) or (
					v_id in pathways_selected_dict and u_id in pathway_proteins_dict):
				try:
					d["p_value"] = pathway_proteins_dict[v_id]
				except:
					d["p_value"] = pathway_proteins_dict[u_id]
				continue
			# protein to drug
			if (u_id in pathway_proteins_dict and v_id in drugs_selected_dict) or (
					v_id in pathway_proteins_dict and u_id in drugs_selected_dict):
				try:
					d["p_value"] = drugs_selected_dict[v_id]
				except:
					d["p_value"] = drugs_selected_dict[u_id]
				continue
			# otherwise, stick a p_value of 1
			d["p_value"] = 1

		# decorate with COHD data
		RU.weight_disease_phenotype_by_cohd(g, max_phenotype_oxo_dist=2,
											default_value=1)  # automatically pulls it out to top-level property

		# decorate with drug->target binding probability
		RU.weight_graph_with_property(g, "probability", default_value=1,
									  transformation=lambda x: x)  # pulls it out to top level property

		# transform the graph properties so they all point the same direction
		# will be finding shortest paths, so make 0=bad, 1=good transform to 0=good, 1=bad
		RU.transform_graph_weight(g, "cohd_freq", default_value=0,
								  transformation=lambda x: 1 / float(x + .001) - 1 / (1 + .001))
		RU.transform_graph_weight(g, "probability", default_value=0,
								  transformation=lambda x: 1 / float(x + .001) - 1 / (1 + .001))

		# merge the graph properties (additively)
		RU.merge_graph_properties(g, ["p_value", "cohd_freq", "probability"], "merged", operation=lambda x, y: x + y)

		graph_weight_tuples = []
		for drug in drugs_selected:
			decorated_paths, decorated_path_edges, path_lengths = RU.get_top_shortest_paths(g, disease_id, drug,
																							num_paths,
																							property='merged', num_nodes=7)  # we are looking for short paths with exactly 7 nodes in them: disease, symptom, disease, protein, pathway, protein, drug
			# TODO: this can return paths that don't go through all the node types we want (since it's just the shortest paths).
			# will need to return all the shortest paths, then pick the top k that go through the nodes we want
			for path_ind in range(len(decorated_paths)):
				g2 = nx.Graph()
				path = decorated_paths[path_ind]
				for node_prop in path:
					node_uuid = node_prop['properties']['UUID']
					g2.add_node(node_uuid, **node_prop)

				path = decorated_path_edges[path_ind]
				for edge_prop in path:
					source_uuid = edge_prop['properties']['source_node_uuid']
					target_uuid = edge_prop['properties']['target_node_uuid']
					g2.add_edge(source_uuid, target_uuid, **edge_prop)
				graph_weight_tuples.append((g2, path_lengths[path_ind], drug))

		# sort by the path weight
		graph_weight_tuples.sort(key=lambda x: x[1])

		# print out the results
		if not use_json:
			num_shown = 0
			for graph, weight, drug_id in graph_weight_tuples:
				num_shown += 1
				if num_shown > num_show:
					break
				drug_description = RU.get_node_property(drug_id, "name", node_label="chemical_substance")
				print("%s %f" % (drug_description, weight))
		else:
			# add the neighborhood graph
			response.add_neighborhood_graph(g.nodes(data=True), g.edges(data=True))
			response.response.table_column_names = ["disease name", "disease ID", "drug name", "drug ID", "path weight",
													"drug disease google distance",
													"ML probability drug treats disease"]
			num_shown = 0
			for graph, weight, drug_id in graph_weight_tuples:
				num_shown += 1
				if num_shown > num_show:
					break
				drug_description = RU.get_node_property(drug_id, "name", node_label="chemical_substance")
				drug_id_old_curie = drug_id.replace("CHEMBL.COMPOUND:CHEMBL", "ChEMBL:")
				# Machine learning probability of "treats"
				prob = p.prob_single(drug_id_old_curie, disease_id)
				if not prob:
					prob = -1
				else:
					prob = prob[0]
				confidence = prob
				# Google distance
				gd = NormGoogleDistance.get_ngd_for_all([drug_id, disease_id], [drug_description, disease_description])
				# populate the graph
				res = response.add_subgraph(graph.nodes(data=True), graph.edges(data=True),
											"The drug %s is predicted to treat %s." % (
												drug_description, disease_description), confidence,
											return_result=True)
				res.essence = "%s" % drug_description  # populate with essence of question result
				row_data = []  # initialize the row data
				row_data.append("%s" % disease_description)
				row_data.append("%s" % disease_id)
				row_data.append("%s" % drug_description)
				row_data.append("%s" % drug_id)
				row_data.append("%f" % weight)
				row_data.append("%f" % gd)
				row_data.append("%f" % prob)
				res.row_data = row_data
			response.print()

	@staticmethod
	def describe():
		output = "Answers questions of the form: 'What are some potential treatments for $disease?'" + "\n"
		# TODO: subsample disease nodes
		return output


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the form: 'What are some potential treatments for $disease?'",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-d', '--disease', type=str, help="disease curie ID", default="OMIM:603903")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
	parser.add_argument('--num_show', type=int, help='Maximum number of results to return', default=25)

	# Parse and check args
	args = parser.parse_args()
	disease_id = args.disease
	use_json = args.json
	describe_flag = args.describe
	num_show = args.num_show


	# Initialize the question class
	Q = SMEDrugRepurposingFisher()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		Q.answer(disease_id, use_json=use_json, num_show=num_show)


if __name__ == "__main__":
	main()
