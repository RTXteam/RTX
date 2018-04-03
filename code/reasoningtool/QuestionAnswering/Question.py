# This class will define each question type
from string import Template
import re


class Question:
	"""
	This class is a python representation of a question type/template
	"""
	def __init__(self, row):
		row_split = row.strip().split("\t")  # See Questions.tsv for the expected format
		self.restated_question_template = Template(row_split[0])  # this is a question template, such as "what is $entity"
		self.corpus = eval(row_split[1])
		self.types = eval(row_split[2])
		self.solution_script = row_split[3]
		# Go through the template and pull off the slot names
		self.parameter_names = []
		for match in Template.pattern.findall(self.restated_question_template.template):
			parameter_name = match[1]
			self.parameter_names.append(parameter_name)

	def restate_question(self, parameters):
		"""
		Restates a question.
		:param parameters: a dictionary with keys given by self.parameters.keys()
		:return:
		"""
		return self.restated_question_template.safe_substitute(parameters)

	def give_examples(self, parameters_list):
		"""
		Given a list of parameters, return a list of restated questions
		:param parameters_list: a list of dictionaries
		:return: a list of restated questions
		"""
		examples = []
		for parameters in parameters_list:
			examples.append(self.restate_question(parameters))
		return examples

	def extract_parameters(self, input_question):
		"""
		Given the input_question, try to extract the proper parameters
		:param input_question:
		:return:
		"""
		# The "what is a X?" questions are of a completely different form and are handled separately
		if self.parameter_names == ["term"]:
			# Next, see if it's a "what is" question
			term = None
			input_question = re.sub("\?", "", input_question)
			input_question = re.sub("^\s+", "", input_question)
			input_question = re.sub("\s+$", "", input_question)
			input_question = input_question.lower()
			match = re.match("what is\s*(a|an)?\s+(.+)", input_question, re.I)
			if match:
				term = match.group(2)
				term = re.sub("^\s+", "", term)
				term = re.sub("\s+$", "", term)
				return {"term":term}




