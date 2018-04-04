# This script will handle the parsing of a user input question

import Question
import os, sys
from importlib import reload
reload(Question)
import string
import WordnetDistance as wd
import CustomExceptions

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
		self.question_templates = question_templates

	def parse_question(self, input_question):
		# first, compute the wordnet distance for each corpus
		wd_distances = []
		for question in self.question_templates:
			ind, val = wd.max_in_corpus(input_question, question.corpus)
			wd_distances.append(val)

		# Sort the indices based on wd_distance
		indicies = range(len(self.question_templates))
		sorted_indicies = [x for _,x in sorted(zip(wd_distances, indicies), key=lambda pair: pair[0],reverse=True)]

		# For each one of the questions, see if it can be fulfilled with the input_question
		error_message = None
		fulfilled = False
		for ind in sorted_indicies:
			try:
				parameters = self.question_templates[ind].get_parameters(input_question)
			except Exception as e:
				error_message = str(e)
				return None, None, error_message
			# Otherwise, see if the parameters can be filled
			if all([x is not None for x in parameters.values()]):
				fulfilled = True
				break  # Template parameters can be filled, so stop looking over questions

		if not fulfilled:
			# If the question was not fulfilled, get the question that was closest, try to fulfill it, and say what's missing
			question = self.question_templates[sorted_indicies[0]]
			parameters = question.get_parameters(input_question)
			error_message = "Unable to fill the following parameters" + str([key for key,value in parameters.items() if value is None])
			return question, parameters, error_message

		# Otherwise, you're all good
		question = self.question_templates[ind]
		return question, parameters, error_message

	def callout_string(self, input_question):
		"""
		Simple function for returning the command that will need to be run to answer the question
		:param input_question:
		:return:
		"""
		question, parameters, error_message = self.parse_question(input_question)
		if error_message is None:
			return question.solution_script.safe_substitute(parameters)
		else:
			return error_message