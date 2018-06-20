# This script will return X that are similar to Y based on high Jaccard index of common one-hop nodes Z (X<->Z<->Y)

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


class SMEDrugRepurposing:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=20):

		# Initialize the response class
		response = FormatOutput.FormatResponse(6)

		# get the description of the disease
		disease_description = RU.get_node_property(disease_id, 'name')

		# What are the defining symptoms of the disease?
		# get diseases that have many raw symptoms in common
		# select top N of them
		# get subraph of these with the input disease
		# weight by COHD data
		# pick diseases with maximal (since frequency) average distance i.e. maximal expected graph distance

		# get disease that have many raw symptoms in common
		similar_nodes_in_common = SimilarNodesInCommon.SimilarNodesInCommon()
		node_jaccard_tuples_sorted, error_code, error_message = similar_nodes_in_common.get_similar_nodes_in_common_source_target_association(
			disease_id, "disease", "phenotypic_feature", 0)
		# select top N of them
		num_diseases_to_select = 100
		diseases_selected = []
		for n, j in node_jaccard_tuples_sorted[0:num_diseases_to_select]:
			diseases_selected.append(n)

		# get subgraph of these with the input disease
		# get all symptoms of input disease
		all_symptoms = RU.get_one_hop_target("disease", disease_id, "phenotypic_feature", "has_phenotype")
		g = RU.get_graph_from_nodes(all_symptoms + diseases_selected + [disease_id], edges=True)

		# weight by COHD data
		node_properties = nx.get_node_attributes(g, 'properties')
		node_ids = dict()
		node_labels = dict()
		for node in node_properties.keys():
			node_ids[node] = node_properties[node]['id']
			node_labels[node] = node_properties[node]['category']
		for u, v, d in g.edges(data=True):
			source_id = node_ids[u]
			source_label = node_labels[u]
			target_id = node_ids[v]
			target_label = node_labels[v]
			if {source_label, target_label} != {"disease", "phenotypic_feature"}:
				d['cohd_freq'] = 0
				continue
			else:
				if source_label == "disease":
					disease_id = source_id
					symptom_id = target_id
				else:
					disease_id = target_id
					symptom_id = source_id
			# look up these in COHD
			# disease
			disease_omop_id = None
			for distance in [1, 2, 3]:
				xref = QueryCOHD.get_xref_to_OMOP(disease_id, distance=distance)
				for ref in xref:
					if ref['omop_domain_id'] == "Condition":
						disease_omop_id = str(ref["omop_standard_concept_id"])
						break
				if disease_omop_id:
					break
			# symptom, loop over them all and take the largest
			if not disease_omop_id:
				d['cohd_freq'] = 0
			else:
				xrefs = QueryCOHD.get_xref_to_OMOP(symptom_id, distance=3)
				freq = 0
				for xref in xrefs:
					symptom_omop_id = str(xref['omop_standard_concept_id'])
					res = QueryCOHD.get_paired_concept_freq(disease_omop_id, symptom_omop_id)
					if res:
						temp_freq = res['concept_frequency']
						if temp_freq > freq:
							freq = temp_freq
				d['cohd_freq'] = freq


	@staticmethod
	def describe():
		output = "Answers questions of the form: 'What are some potential treatments for $disease?'" + "\n"
		# TODO: subsample disease nodes
		return output


def main():
	parser = argparse.ArgumentParser(description="Answers questions of the form: 'What are some potential treatments for $disease?'",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-d', '--disease', type=str, help="disease curie ID", default="DOID:8398")
	parser.add_argument('-j', '--json', action='store_true', help='Flag specifying that results should be printed in JSON format (to stdout)', default=False)
	parser.add_argument('--describe', action='store_true', help='Print a description of the question to stdout and quit', default=False)
	parser.add_argument('--num_show', type=int, help='Maximum number of results to return', default=20)

	# Parse and check args
	args = parser.parse_args()
	disease_id = args.disease
	use_json = args.json
	describe_flag = args.describe
	num_show = args.num_show


	# Initialize the question class
	Q = SMEDrugRepurposing()

	if describe_flag:
		res = Q.describe()
		print(res)
	else:
		Q.answer(disease_id, use_json=use_json, num_show=num_show)


if __name__ == "__main__":
	main()
