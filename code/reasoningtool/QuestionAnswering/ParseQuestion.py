# This script will handle the parsing of a user input question

import Question
import os, sys
from importlib import reload
reload(Question)
import string
import WordnetDistance as wd
import CustomExceptions
import datetime

# get all the question templates we've made so far, import each as a Question class
question_templates = []
with open(os.path.join(os.path.dirname(__file__), 'Questions.tsv'), 'r') as fid:
	for line in fid.readlines():
		if line[0] == "#":
			pass
		else:
			question_templates.append(Question.Question(line))


class ParseQuestion:
	def __init__(self):
		self._question_templates = question_templates
		self._known_query_type_id_to_question = dict()
		for q in question_templates:
			self._known_query_type_id_to_question[q.known_query_type_id] = q

	def parse_question(self, input_question):
		"""
		Given an input query, find the parameters, if they can be found
		:param input_question: input user query
		:return: question (Question class, or None), parameters (dict or None), error_message (string or None), error_code (string or None)
		"""
		# first, compute the wordnet distance for each corpus
		wd_distances = []
		for question in self._question_templates:
			ind, val = wd.max_in_corpus(input_question, question.corpus)
			wd_distances.append(val)

		# Sort the indices based on wd_distance
		indicies = range(len(self._question_templates))
		sorted_indicies = [x for _, x in sorted(zip(wd_distances, indicies), key=lambda pair: pair[0], reverse=True)]

		# For each one of the questions, see if it can be fulfilled with the input_question
		error_message = None
		error_code = None
		fulfilled = False
		for ind in sorted_indicies[0:3]:  # only look at the top 3 similar questions
			question = self._question_templates[ind]
			if wd_distances[ind] < 0.25:  # don't even bother with these low quality matches
				break
			try:
				parameters = question.get_parameters(input_question)
			except CustomExceptions.MultipleTerms as e:  # If you run into an exception, return the error string
				error_message = "The most similar question I can answer is: " + question.restated_question_template.template
				error_message += " But I found: " + str(e)
				error_code = "multiple_terms"
				return question, {}, error_message, error_code
			# Otherwise, see if the parameters can be filled
			if not parameters and not question.parameter_names:
				fulfilled = True  # There was nothing to fulfill, so we're good
				break
			elif parameters and all([x is not None for x in parameters.values()]):
				fulfilled = True
				break  # Template parameters can be filled, so stop looking over questions

		if not fulfilled:
			# If the question was not fulfilled, get the question that was closest, try to fulfill it, and say what's missing
			question = self._question_templates[sorted_indicies[0]]
			parameters = question.get_parameters(input_question)
			error_message = "The most similar question I can answer is: " + question.restate_question(parameters)
			error_message += "\n But I was unable to fill the following parameters: " + str([key for key, value in parameters.items() if value is None])
			error_code = "missing_term"
			return question, parameters, error_message, error_code

		# Otherwise, you're all good
		question = self._question_templates[ind]
		parameters = question.get_parameters(input_question)
		return question, parameters, error_message, error_code

	def get_execution_string(self, known_query_type_id, parameters):
		"""
		Simple function for returning the command that will need to be run to answer the question
		:param known_query_type_id: str
		:param parameters: dict
		:return: string
		"""
		if known_query_type_id in self._known_query_type_id_to_question:
			q = self._known_query_type_id_to_question[known_query_type_id]
		else:
			raise Exception("Unknown query type id: %s" % known_query_type_id)
		execution_string = q.solution_script.safe_substitute(parameters)
		if "$" in execution_string:
			raise Exception("Unpopulated parameter: %s" % execution_string)
		return execution_string

	def log_query(self, code_string, id, original_text):
		date_time_string = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		log_dir = os.path.dirname(os.path.abspath(__file__)) + "/../../../code/UI/OpenAPI/python-flask-server"
		try:
			with open(os.path.join(log_dir, "RTXQuestions.log"), "a") as logfile:
				logfile.write(date_time_string + "\t" + code_string + "\t" + id + "\t" + original_text + "\n")
		except FileNotFoundError:
			log_dir = "/tmp"
			with open(os.path.join(log_dir, "RTXQuestions.log"), "a") as logfile:
				logfile.write(date_time_string + "\t" + code_string + "\t" + id + "\t" + original_text + "\n")

	def format_response(self, question_with_lang):
		"""
		Formats the response given an input query
		:param input_question: input query dict with keys 'language' and 'text'
		:return: dict
		"""
		if question_with_lang["language"] != "English":
			raise Exception("Sorry, we can't handle the language: %s" % question_with_lang["language"])

		input_question = question_with_lang["text"]
		response = dict()
		question, parameters, error_message, error_code = self.parse_question(input_question)
		if error_message is None:
			restated_question = question.restate_question(parameters)
			#execution_string = self.callout_string(question, parameters)
			response['restated_question'] = restated_question
			#response['execution_string'] = execution_string
			response['original_question'] = input_question
			#response['terms'] = list(parameters.values())
			response['terms'] = parameters
			#response['solution_script'] = question.solution_script.template.split()[0]
			response['known_query_type_id'] = question.known_query_type_id
			return response
		else:
			self.log_query(error_code, "-", error_message)
			if question and parameters:
				parameters_without_none = dict()
				for key, value in parameters.items():
					if value is not None:
						parameters_without_none[key] = value
				restated_question = question.restate_question(parameters_without_none)
				response['restated_question'] = restated_question
				response['known_query_type_id'] = question.known_query_type_id
			elif question:
				response['restated_question'] = question.restate_question({})
				response['known_query_type_id'] = question.known_query_type_id
			else:
				response['restated_question'] = None
				response['known_query_type_id'] = None
			response['original_question'] = input_question
			response['error_message'] = error_message
			response['error_code'] = error_code
			return response


def main():
	p = ParseQuestion()
	texts = ["What is the clinical outcome pathway of physostigmine for treatment of glaucoma",
			 "What is the clinical outcome pathway of dicumarol for treatment of coagulation",
			 "What is the clinical outcome pathway of naproxen for treatment of Osteoarthritis",
			 "What is the clinical outcome pathway of beano for treatment of Osteoarthritis",
			 "What is the clinical outcome pathway of physostigmine for treatment of glaucoma in dogs",
			 "What is the clinical outcome pathway of glaucoma for treatment of physostigmine",
			 "What is the COP of physostigmine for treatment of glaucoma",
			 "what genetic conditions might offer protection against malaria",
			 "Which genetic conditions might offer protection against hypertension",
			 "what genetic conditions might offer protection against naproxen",
			 "what genetic conditions might offer protection against asdfasdf",
			 "what is lovastatin",
			 "what are adenoids",
			 "what is an iPhone",
			 "What proteins does acetaminophen target?",
			 "What proteins are in the glycosylation pathway?",
			 "What proteins are expressed in liver?",
			 "What diseases are similar to malaria?",
			 "what diseases are associated with naproxen",
			 "what phenotypes are associated with naproxen",
			 "what drugs have similar protein targets to ibuprofen",
			 ]
	for text in texts:
		question = {"language": "English", "text": text}
		res = p.format_response(question)
		print("Question is: " + text)
		print("Result is:")
		print(res)
		print("=====")

	# Example of how to get the query string
	text = "What are the protein targets of naproxen"
	print("Getting execution string for: %s" % text)
	question = {"language": "English", "text": text}
	res = p.format_response(question)
	execution_string = p.get_execution_string(res["known_query_type_id"], res["terms"])
	print(execution_string)


def tests():
	txltr = ParseQuestion()
	# No question should match
	question = "what proteins are four score and seven years ago, our fathers..."
	question = {"language": "English", "text": question}
	results_dict = txltr.format_response(question)
	assert results_dict["error_message"] is not None

	question = "what genetic conditions may offer protection against malaria osteoarthritis"
	question = {"language": "English", "text": question}
	results_dict = txltr.format_response(question)
	assert results_dict['error_message'] is not None
	assert results_dict['error_code'] == 'multiple_terms'

	question = "what genetic conditions may offer protection against"
	question = {"language": "English", "text": question}
	results_dict = txltr.format_response(question)
	assert results_dict['error_message'] is not None
	assert results_dict['error_code'] == 'missing_term'

	question = "what diseases are similar to naproxen"
	q, params, error_message, error_code = txltr.parse_question(question)
	assert error_code == "missing_term"
	res = txltr.format_response({"language": "English", "text": question})
	assert "error_message" in res
	assert isinstance(res["error_message"], str)

	question = "what diseases are similar to malaria"
	q, params, error_message, error_code = txltr.parse_question(question)
	assert error_message is None
	assert q.solution_script.template.split()[0] == "SimilarityQuestionSolution.py"
	assert "disont_disease" in params
	assert params["disont_disease"] == "DOID:12365"
	res = txltr.format_response({"language": "English", "text": question})
	assert "error_message" not in res
	assert 'terms' in res
	assert 'DOID:12365' in res['terms'].values()
	assert res['known_query_type_id'] == 'Q13'

	question = "what diseases are similar to cerebral malaria"
	q, params, error_message, error_code = txltr.parse_question(question)
	assert error_message is None
	assert q.solution_script.template.split()[0] == "SimilarityQuestionSolution.py"
	assert "disont_disease" in params
	assert params["disont_disease"] == "DOID:14069"
	res = txltr.format_response({"language": "English", "text": question})
	assert "error_message" not in res
	assert 'terms' in res
	assert 'DOID:14069' in res['terms'].values()
	assert res['known_query_type_id'] == 'Q13'
	#assert 'execution_string' in res
	#assert 'solution_script' in res
	#assert res['solution_script'] == 'SimilarityQuestionSolution.py'

	question = "what drugs target proteins associated with osteoarthritis"
	q, params, error_message, error_code = txltr.parse_question(question)
	assert error_message is None
	assert q.solution_script.template.split()[0] == "SimilarityQuestionSolution.py"
	assert "disont_disease" in params
	assert params["disont_disease"] == "DOID:8398"
	assert params["association"] == "uniprot_protein"
	assert params["target"] == "pharos_drug"
	res = txltr.format_response({"language": "English", "text": question})
	assert "error_message" not in res
	assert 'terms' in res
	assert 'DOID:8398' in res['terms'].values()
	assert res['known_query_type_id'] == 'Q23'
	#assert 'execution_string' in res
	#assert 'solution_script' in res
	#assert res['solution_script'] == 'SimilarityQuestionSolution.py'


	# Test the exectution string function
	text = "What are the protein targets of naproxen"
	question = {"language": "English", "text": text}
	res = txltr.format_response(question)
	known_query_type_id = res['known_query_type_id']
	parameters = res['terms']
	execution_string = txltr.get_execution_string(known_query_type_id, parameters)
	assert execution_string == "Q3Solution.py -s 'naproxen' -t 'uniprot_protein' -r 'targets' -j"

	return
	######################################################################
	# No real need for a ton more tests any more. See the auto-tests of Question.test_correct_question
	######################################################################

if __name__ == "__main__":
	main()
