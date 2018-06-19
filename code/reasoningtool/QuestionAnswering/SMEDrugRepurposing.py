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

import CustomExceptions


class SMEDrugRepurposing:

	def __init__(self):
		None

	@staticmethod
	def answer(disease_id, use_json=False, num_show=20):

		# Initialize the response class
		response = FormatOutput.FormatResponse(6)

		# get the description
		disease_description = RU.get_node_property(disease_id, 'name')



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
