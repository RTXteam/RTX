# This script will go through and run each one of the queries on randomly selected data
import ReasoningUtilities as RU
import ParseQuestion
import random
import os, sys
import argparse
import QuestionExamples
QuestionExamples = QuestionExamples.QuestionExamples()
p = ParseQuestion.ParseQuestion()


def run_question_examples(question_number, python_loc, res_loc, after=0):
	"""
	Run questions from QuestionExamples.tsv
	:param question_number: question number you want to test
	:return: none
	"""
	QuestionExamples.read_reference_file()
	for id_text_dict in QuestionExamples.questions:
		q_id = id_text_dict['query_type_id']
		if q_id == question_number or question_number == "a" and int(q_id.replace("Q", "")) > after:

			# template match it
			nat_lang_question = id_text_dict['question_text']
			matched_question, extracted_params, error_message, error_code = p.parse_question(nat_lang_question)

			# check for error
			error_found = False
			if error_message:
				print("ERROR on question: %s" % nat_lang_question)
				print(error_message)
				print(error_code)
				error_found = True
				#raise Exception

			# check for right query number matched
			if q_id != matched_question.query_type_id:
				print("WARNING: for the query: %s\n I matched to template %s while it should have been %s" % (
				nat_lang_question, matched_question.query_type_id, q_id))
				error_found = True

			# get the solution script
			#solution_script = matched_question.solution_script.safe_substitute(extracted_params)
			solution_script = p.get_execution_string(matched_question.known_query_type_id, extracted_params)

			# if no errors, then run the solution script
			if not error_found:
				try:
					print("Running: %s" % solution_script)
					print("%s" % nat_lang_question)
					os.system("%s %s > %s" % (python_loc, solution_script, res_loc))
				except:
					print("ERROR on question: %s" % nat_lang_question)
					print("Try running %s and see what went wrong." % solution_script)
					raise Exception
			else:
				raise Exception


def run_test_suite(question_number, python_loc, res_loc, after=0):
	p = ParseQuestion.ParseQuestion()

	# get a random selection of nodes
	property_to_nodes = dict()
	for label in RU.get_node_labels():
		nodes = RU.get_random_nodes(label, property="name")
		property_to_nodes[label] = nodes

	# Go through each of the questions and populate terms
	for question in ParseQuestion.question_templates:
		if question_number == "a" or question_number == question.query_type_id:
			# ignore "what is"
			if question.query_type_id != 'Q0':
				question_template = question.restated_question_template

				# populate the parameters
				params = dict()
				for label in question.parameter_names:
					params[label] = random.choice(property_to_nodes[label])
				for label in question.other_parameters.keys():
					params[label] = question.other_parameters[label]

				# form the question
				nat_lang_question = question.restated_question_template.safe_substitute(params)

				# template match it
				matched_question, extracted_params, error_message, error_code = p.parse_question(nat_lang_question)

				# look for error message
				error_found = False
				if error_message:
					print("ERROR on question: %s" % nat_lang_question)
					print(error_message)
					print(error_code)
					error_found = True
					#raise Exception

				# make sure the correct template was matched
				if question.query_type_id != matched_question.query_type_id:
					print("WARNING: for the query: %s\n I matched to template %s while it should have been %s" % (nat_lang_question, matched_question.query_type_id, question.query_type_id))

				# get the solution script
				solution_script = matched_question.solution_script.safe_substitute(extracted_params)

				# if no errors, then run the solution script
				if not error_found:
					try:
						print("Running: %s" % solution_script)
						print("%s" % nat_lang_question)
						os.system("%s %s > %s" % (python_loc, solution_script, res_loc))
					except:
						print("ERROR on question: %s" % nat_lang_question)
						print("Try running %s and see what went wrong." % solution_script)

def main():
	parser = argparse.ArgumentParser(description="Runs a test suite for the entire QuestionAnswering framework",
									formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-q', '--question', type=str, help="query ID (eg Q1 or Q23 or 'a' for all", default='a')
	parser.add_argument('-p', '--python', type=str, help="location of python", default='/home/dkoslicki/Dropbox/Repositories/RTX/VE3/bin/python3')
	parser.add_argument('-r', '--res_loc', type=str, help="Where to put the result",
						default='/dev/null')
	parser.add_argument('-e', '--example', action='store_true', help="Include this flag if pulling questions from QuestionExamples.tsv")
	parser.add_argument('-a', '--after', type=int, help="Only do question after the given int value", default=0)

	if '-h' in sys.argv or '--help' in sys.argv:
		RU.session.close()
		RU.driver.close()

	# Parse and check args
	args = parser.parse_args()
	question_id = args.question
	python_loc = args.python
	res_loc = args.res_loc
	is_example = args.example
	after = int(args.after)

	if not is_example:
		run_test_suite(question_id, python_loc, res_loc, after=after)
	else:
		run_question_examples(question_id, python_loc, res_loc, after=after)

if __name__ == "__main__":
	main()

