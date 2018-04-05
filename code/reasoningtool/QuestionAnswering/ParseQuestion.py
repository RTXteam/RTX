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
		sorted_indicies = [x for _,x in sorted(zip(wd_distances, indicies), key=lambda pair: pair[0],reverse=True)]

		# For each one of the questions, see if it can be fulfilled with the input_question
		error_message = None
		error_code = None
		fulfilled = False
		for ind in sorted_indicies[0:3]:  # only look at the top 3 similar questions
			if wd_distances[ind] < 0.25:  # don't even bother with these low quality matches
				break
			try:
				parameters = self._question_templates[ind].get_parameters(input_question)
			except CustomExceptions.MultipleTerms as e:  # If you run into an exception, return the error string
				error_message = "The most similar question I can answer is: " + self._question_templates[ind].restated_question_template.template
				error_message += " But I found: " + str(e)
				error_code = "multiple_terms"
				return self._question_templates[ind], {}, error_message, error_code
			# Otherwise, see if the parameters can be filled
			if parameters and all([x is not None for x in parameters.values()]):
				fulfilled = True
				break  # Template parameters can be filled, so stop looking over questions

		if not fulfilled:
			# If the question was not fulfilled, get the question that was closest, try to fulfill it, and say what's missing
			question = self._question_templates[sorted_indicies[0]]
			parameters = question.get_parameters(input_question)
			error_message = "The most similar question I can answer is: " + question.restate_question(parameters)
			error_message += "\n But I was unable to fill the following parameters: " + str([key for key,value in parameters.items() if value is None])
			error_code = "missing_term"
			return question, parameters, error_message, error_code

		# Otherwise, you're all good
		question = self._question_templates[ind]
		return question, parameters, error_message, error_code

	def callout_string(self, question, parameters):
		"""
		Simple function for returning the command that will need to be run to answer the question
		:param input_question: input user query
		:return: str
		"""
		return question.solution_script.safe_substitute(parameters)

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

	def format_response(self, input_question):
		"""
		Formats the response given an input query
		:param input_question: input query
		:return: dict
		"""
		response = dict()
		question, parameters, error_message, error_code = self.parse_question(input_question)
		if error_message is None:
			restated_question = question.restate_question(parameters)
			execution_string = self.callout_string(question, parameters)
			response['restatedQuestion'] = restated_question
			response['executionString'] = execution_string
			response['originalQuestion'] = input_question
			return response
		else:
			self.log_query(error_code, "-", error_message)
			if question and parameters:
				parameters_without_none = dict()
				for key, value in parameters.items():
					if value is not None:
						parameters_without_none[key] = value
				restated_question = question.restate_question(parameters_without_none)
				response['restatedQuestion'] = restated_question
			elif question:
				response['restatedQuestion'] = question.restate_question({})
			response['originalQuestion'] = input_question
			response['errorMessage'] = error_message
			return response


def main():
	p = ParseQuestion()
	question = "What genetic conditions may offer protection against malaria"
	print(p.format_response(question))


if __name__ == "__main__":
	main()
