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

		num_input_disease_symptoms = 50  # number of representative symptoms of the disease to keep
		num_omim_keep = 50  # number of genetic conditions to keep
		num_protein_keep = 50  # number of implicated proteins to keep
		num_pathways_keep = 50  # number of pathways to keep
		num_pathway_proteins_selected = 50  # number of proteins enriched for the above pathways to select
		num_drugs_keep = 2*num_show  # number of drugs that target those proteins to keep
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

		path_type = ["disease", "has_phenotype", "phenotypic_feature", "has_phenotype", "disease",
					 "gene_mutations_contribute_to", "protein", "participates_in", "pathway", "participates_in",
					 "protein", "physically_interacts_with", "chemical_substance"]
		g = RU.get_subgraph_through_node_sets_known_relationships(path_type,
																  [[disease_id], symptoms, genetic_diseases_selected,
																   implicated_proteins_selected, pathways_selected,
																   pathway_proteins_selected, drugs_selected],
																  directed=True)


		graph_weight_tuples = []
		for drug in drugs_selected:
			# get the relevant subgraph from this drug back to the input disease
			node_types = ["disease", "phenotypic_feature", "disease", "protein", "pathway", "protein",
						  "chemical_substance"]
			drug_pathway_protein_neighbors = RU.one_hope_neighbors_of_type(g, drug, 'protein', 'R')
			drug_pathway_neighbors = set()
			for protein in drug_pathway_protein_neighbors:
				drug_pathway_neighbors.update(RU.one_hope_neighbors_of_type(g, protein, 'pathway', 'R'))
			drug_protein_neighbors = set()
			for pathway in drug_pathway_neighbors:
				drug_protein_neighbors.update(RU.one_hope_neighbors_of_type(g, pathway, 'protein', 'L'))
			drug_disease_neighbors = set()
			for protein in drug_protein_neighbors:
				drug_disease_neighbors.update(RU.one_hope_neighbors_of_type(g, protein, 'disease', 'R'))
			drug_phenotype = set()
			for disease in drug_disease_neighbors:
				drug_phenotype.update(RU.one_hope_neighbors_of_type(g, disease, 'phenotypic_feature', 'R'))
			g2 = RU.get_subgraph_through_node_sets_known_relationships(path_type,
																	   [[disease_id], drug_phenotype,
																		drug_disease_neighbors,
																		drug_protein_neighbors, drug_pathway_neighbors,
																		drug_pathway_protein_neighbors, [drug]],
																	   directed=False)
			drug_id_old_curie = drug.replace("CHEMBL.COMPOUND:CHEMBL", "ChEMBL:")
			# Machine learning probability of "treats"
			prob = p.prob_single(drug_id_old_curie, disease_id)
			if not prob:
				prob = -1
			else:
				prob = prob[0]
			graph_weight_tuples.append((g, prob, drug))

		# sort by the path weight
		graph_weight_tuples.sort(key=lambda x: x[1], reverse=True)

		# print out the results
		if not use_json:
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
				print("%s %f %f" % (drug_description, weight, prob))
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
