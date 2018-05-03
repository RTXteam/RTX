# This will be a fun little script that pulls random info from the graph and fills in the question templates
# demonstrating what questions can be answered. It also serves as a test for Questions.tsv to make sure there are
# no types in any of the names

import ParseQuestion
import ReasoningUtilities as RU
import numpy as np
import random
import os
import argparse
import FormatOutput

python_loc = "/home/dkoslicki/Dropbox/Repositories/RTX/VE3/bin/python3 "
script_loc = "/home/dkoslicki/Dropbox/Repositories/RTX/code/reasoningtool/QuestionAnswering/"

PQ = ParseQuestion.ParseQuestion()


def display_n_questions(n, use_json=False):
	# Initialize output formatter
	response = FormatOutput.FormatResponse(3)

	# Get all the question templates
	questions = ParseQuestion.question_templates

	# Don't select more than questions I have
	if n > len(questions):
		n = len(questions)

	# get a random selection of nodes
	label_to_nodes = dict()
	for label in RU.get_node_labels():
		nodes = RU.get_random_nodes(label, property="name")
		label_to_nodes[label] = nodes

	# pick n of the questions to spit back
	questions_subset = np.random.choice(questions, size=n, replace=False)
	#print([x.restated_question_template.template for x in questions_subset])

	# Now for each one of the questions, populate the correct fields
	for question in questions_subset:
		parameters = dict()
		for label, nodes in label_to_nodes.items():
			parameters[label] = random.choice(nodes)
		if not use_json:
			print(question.restate_question(parameters))
		else:
			response.add_text(question.restate_question(parameters))
	return response

def shell_out_n_questions(n, execute=False, use_json=False):
	if use_json:
		raise Exception("You can't use json and call out stuff at the same time (no control of error handling)")
	# Get all the question templates
	questions = ParseQuestion.question_templates
	# Don't select more than questions I have
	if n > len(questions):
		n = len(questions)

	# get a random selection of nodes
	label_to_nodes = dict()
	for label in RU.get_node_labels():
		nodes = RU.get_random_nodes(label, property="name")
		label_to_nodes[label] = nodes

	# pick n of the questions to spit back
	questions_subset = np.random.choice(questions, size=n, replace=False)

	# Now for each one of the questions, populate the correct fields, send it back to the parser, then call the script command
	for question in questions_subset:
		parameters = dict()
		for label, nodes in label_to_nodes.items():
			parameters[label] = random.choice(nodes)
		restated_question = question.restate_question(parameters)
		res = PQ.format_response({"language": "English", "text": restated_question})
		if 'executionString' in res:
			print("input_question: %s" % restated_question)
			print("result: %s" % str(res))
			print(res['executionString'])
			print("")
			if execute is True:
				os.system(python_loc + script_loc + res['executionString'])
		else:
			print("Something went wrong!")
			print("input_question: %s" % restated_question)
			print("result: %s" % str(res))
			print("")

def main():
	parser = argparse.ArgumentParser(description="Gives examples of questions RTX can answer.",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-n', '--number_of_questions', type=int, help="Number of questions to return.", default=5)
	parser.add_argument('-r', '--replicates', type=int, help="Number of replicates to do.", default=1)
	parser.add_argument('--execute', action='store_true', help="If you want to actually execute these questions.")
	parser.add_argument('-j', '--json', action='store_true', help="If you want the output in JSON.")

	# Parse and check args
	args = parser.parse_args()
	number_of_questions = args.number_of_questions
	replicates = args.replicates
	execute = args.execute
	use_json = args.json

	# Do it
	for i in range(replicates):
		if execute is True:
			shell_out_n_questions(number_of_questions, execute=execute, use_json=use_json)
		else:
			res = display_n_questions(number_of_questions, use_json=use_json)
			if use_json:
				res.print()


if __name__ == "__main__":
	main()



