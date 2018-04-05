# This class will define each question type
from string import Template
import sys
import os
import nltk
from nltk.corpus import stopwords
import string
import re
import datetime
import CustomExceptions
import random
# Import reasoning utilities
try:
	from code.reasoningtool import ReasoningUtilities as RU
except ImportError:
	# noinspection PyUnboundLocalVariable
	try:
		sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
		import ReasoningUtilities as RU
	except ImportError:
		sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Go up one level and look for it
		import ReasoningUtilities as RU
try:
	from code.reasoningtool.QuestionAnswering import WordnetDistance as wd
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import WordnetDistance as wd


#################################################
# Required data about the knowledge graph
################################################
# get all the node names and descriptions
fid = open(os.path.dirname(os.path.abspath(__file__))+'/../../../data/KGmetadata/NodeNamesDescriptions.tsv', 'r')
names2descrip = dict()
descrip2names = dict()  # TODO: this assumes that descriptions are unique, and this may change soon
for line in fid.readlines():
	line = line.strip()
	line_split = line.split('\t')
	name = line_split[0]
	try:
		descr = line_split[1]
	except IndexError:
		descr = "N/A"
	names2descrip[name] = descr
	descrip2names[descr] = name
fid.close()

# TODO: replace this stuff with the RU.get_node_property (along with RU.node_exists_with_property)
# get the edge types
try:
	fid = open(os.path.dirname(os.path.abspath(__file__))+'/../../../data/KGmetadata/EdgeTypes.tsv', 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/EdgeTypes.tsv'), 'r')
edge_types = list()
for line in fid.readlines():
	line = line.strip()
	edge_types.append(line)
fid.close()

# Get the node labels
try:
	fid = open(os.path.dirname(os.path.abspath(__file__))+'/../../../data/KGmetadata/NodeLabels.tsv', 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/NodeLabels.tsv'), 'r')
node_labels = list()
for line in fid.readlines():
	line = line.strip()
	node_labels.append(line)
fid.close()

#################################################
# Helper functions for the extraction of terms
#################################################
# A variety of functions to help with term extraction
def find_node_name(string):
	"""
	Find an acutal Neo4j KG node name in the string
	:param string: input string (chunk of text)
	:param names2descrip: dictionary containing the names and descriptions of the nodes (see dumpdata.py)
	:param descrip2names: reversed names2descrip dictionary
	:return: one of the node names (key (string) of names2descrip)
	"""
	# exact match
	query = string
	res_list = []
	if query in names2descrip:
		res = query
		res_list.append(res)
	elif query in descrip2names:
		res = descrip2names[query]
		res_list.append(res)
	elif False:
		pass
	# TODO: put Arnabs ULMS metathesaurus lookup here
	# Case insensitive match
	query_lower = string.lower()
	for name in names2descrip:
		if name.lower() == query_lower:
			res = name
			res_list.append(res)
	for descr in descrip2names:
		if descr.lower() == query_lower:
			res = descrip2names[descr]
			res_list.append(res)
	return res_list

def find_target_label(string):
	"""
	Find target label (drug, disease, etc) in string
	:param string: input string (chunck of text)
	:param node_labels: node labels in the KG (see input dumpdata.py)
	:return: one of the node labels
	"""
	# drop any "s" endings
	p = nltk.stem.snowball.SnowballStemmer("english")
	query = p.stem(string)
	node_labels_space = []
	# replace underscore with space
	for label in node_labels:
		label = label.replace('_', ' ')
		node_labels_space.append(label)
	query = query.lower()
	res = None
	for i in range(len(node_labels)):
		label = node_labels_space[i]
		if query in label:
			res = node_labels[i]
	if res is None:
		if query == "gene":
			res = "uniprot_protein"
		if query == "condit":
			res = "omim_disease"
	# TODO: Arnab's UMLS lookup for synonyms
	return res

def find_edge_type(string):
	"""
	Extract edge type from string
	:param string: input string (chunck of text)
	:param edge_types: edge types in the KG (see dumpdata.py)
	:return: one of the edge types
	"""
	p = nltk.stem.snowball.SnowballStemmer("english")
	st_words = set(stopwords.words('english'))
	res = None
	# remove underscores
	edge_types_space = []
	for et in edge_types:
		edge_types_space.append(et.replace('_', ' '))
	# standarize the string by making it lowercase and removing stop words
	query = string.lower()
	query_tokens = nltk.word_tokenize(query, "english")
	query_no_stop = [w for w in query_tokens if w not in st_words]
	query_clean = ""
	for word in query_no_stop:
		query_clean += p.stem(word) + " "
	# see if it matches any of the standardized edge types
	for i in range(len(edge_types_space)):
		et = edge_types_space[i]
		et_tokens = nltk.word_tokenize(et)
		et_no_stop = [w for w in et_tokens if w not in st_words]
		et_clean = ""
		for word in et_no_stop:
			if word == "assoc":
				word = "associated"
			et_clean += p.stem(word) + " "
		if query_clean == et_clean:
			res = edge_types[i]
	return res

################################################
# The Question class to store the question templates
################################################
class Question:
	"""
	This class is a python representation of a question type/template
	"""
	def __init__(self, row):
		#print(row)
		row_split = row.strip().split("\t")  # See Questions.tsv for the expected format
		self.restated_question_template = Template(row_split[0])  # this is a question template, such as "what is $entity"
		self.corpus = eval(row_split[1])
		self.types = eval(row_split[2])
		self.solution_script = Template(row_split[3])
		self.other_parameters = eval(row_split[4])
		# Go through the template and pull off the slot names
		self.parameter_names = []
		for match in Template.pattern.findall(self.restated_question_template.template):
			parameter_name = match[1]
			self.parameter_names.append(parameter_name)

	def restate_question(self, parameters):
		"""
		Restates a question.
		:param parameters: a dictionary with keys given by self.parameters.keys()
		:return: string
		"""
		parameters_as_descriptions = dict()
		if parameters:
			for parameter in parameters:
				try:
					description = RU.get_node_property(parameters[parameter], 'description')
				except:
					description = parameters[parameter]
				parameters_as_descriptions[parameter] = description
		if parameters_as_descriptions:
			restated = self.restated_question_template.safe_substitute(parameters_as_descriptions)
		else:
			restated = self.restated_question_template.safe_substitute({})
		return restated

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

	def get_parameters(self, input_question):
		"""
		Given the input_question, try to extract the proper parameters
		:param input_question: plain text input question
		:return: a dictionary (with keys self.parameter_names), values either None or the KG node names
		"""
		parameters = dict()
		for parameter in self.parameter_names:
			parameters[parameter] = None

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
				parameters["term"] = term
				return parameters
			match = re.match("what are (.+)", input_question, re.I)
			if match:
				term = match.group(1)
				term = re.sub("^\s+", "", term)
				term = re.sub("\s+$", "", term)
				parameters["term"] = term
				return parameters
			else:
				return parameters
		else:  # Otherwise, it's a standard question template
			# get all n-tuples of words in the question (largest to smallest)
			blocks = []
			question_tokenized = nltk.word_tokenize(input_question, "english")
			for block_size in range(1, len(question_tokenized)):
				for i in range(len(question_tokenized) - block_size + 1):
					block = " ".join(question_tokenized[i:(i + block_size)])
					blocks.append(block)
			blocks = list(reversed(blocks))

			# Look for anything that could be a node name
			candidate_node_names = []
			found_blocks = []  # keep track of the already found blocks TODO: this will cause problems when you ask something like "how are malaria and mixed malaria different?"
			for block in blocks:
				nodes = find_node_name(block)
				if nodes:
					if all([block not in b for b in found_blocks]):  # only add it if it's not a proper subset of an already found block
						candidate_node_names.extend(nodes)
						found_blocks.append(block)
						#print(block)

			# Get the node labels for the found nodes
			candidate_node_names_labels = set()  # set automatically deduplicates for me
			for node in candidate_node_names:
				node_label = RU.get_node_property(node, "label")  # TODO: Arnab's UMLS lookup
				candidate_node_names_labels.add((node, node_label))

			# turn it back into a set for indexing
			candidate_node_names_labels = list(candidate_node_names_labels)

			# For each of the parameter names, make sure it only shows up once, and if so, populate it
			for parameter_name in self.parameter_names:
				parameter_name_positions = []
				pos = 0
				for node, node_label in candidate_node_names_labels:
					if node_label == parameter_name:
						parameter_name_positions.append(pos)
					pos += 1
				if len(parameter_name_positions) > 1:
					raise CustomExceptions.MultipleTerms(parameter_name, [candidate_node_names_labels[pos][0] for pos in parameter_name_positions])
				elif len(parameter_name_positions) == 0:
					pass
				else:  # There's exactly one term
					pos = parameter_name_positions.pop()
					parameters[parameter_name] = candidate_node_names_labels[pos][0]

			# Throw in the extra parameters
			for key, value in self.other_parameters.items():
				parameters[key] = value
			return parameters


def test_get_parameters():
	questions = []
	with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Questions.tsv'), 'r') as fid:
		for line in fid.readlines():
			if line[0] == "#":
				pass
			else:
				questions.append(Question(line))

	for question in questions:
		print(question.restate_question({}))

	# Q0 tests
	input_question = "What is Creutzfeldt Jakob disease, subtype I"
	parameters = questions[0].get_parameters(input_question)
	assert "term" in parameters
	assert isinstance(parameters["term"], str)
	assert parameters["term"] == "creutzfeldt jakob disease, subtype i"

	input_question = "What is a dog"
	parameters = questions[0].get_parameters(input_question)
	assert "term" in parameters
	assert isinstance(parameters["term"], str)
	assert parameters["term"] == "dog"

	input_question = "What is an otolith"
	parameters = questions[0].get_parameters(input_question)
	assert "term" in parameters
	assert isinstance(parameters["term"], str)
	assert parameters["term"] == "otolith"

	# Q1 tests
	input_question = "what genetic conditions might protect against malaria?"
	parameters = questions[1].get_parameters(input_question)
	assert "disont_disease" in parameters
	assert isinstance(parameters["disont_disease"], str)
	assert parameters["disont_disease"] == "DOID:12365"

	input_question = "what genetic conditions might protect against mixed malaria?"
	parameters = questions[1].get_parameters(input_question)
	assert "disont_disease" in parameters
	assert isinstance(parameters["disont_disease"], str)
	assert parameters["disont_disease"] == "DOID:14325"

	input_question = "what genetic conditions might protect against bone marrow cancer?"
	parameters = questions[1].get_parameters(input_question)
	assert "disont_disease" in parameters
	assert isinstance(parameters["disont_disease"], str)
	assert parameters["disont_disease"] == "DOID:4960"

	input_question = "what genetic conditions might protect against cerebral sarcoidosis?"
	parameters = questions[1].get_parameters(input_question)
	assert "disont_disease" in parameters
	assert isinstance(parameters["disont_disease"], str)
	assert parameters["disont_disease"] == "DOID:13403"

def test_correct_question():
	"""
	Point of this test is to form a bunch of sentences, match them against all queries, and make sure the correct
	question template is matched
	:return: None
	"""
	# get a random selection of nodes
	property_to_nodes = dict()
	for label in RU.get_node_labels():
		nodes = RU.get_random_nodes(label, property="description")
		property_to_nodes[label] = nodes

	# import the questions
	questions = []
	with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Questions.tsv'), 'r') as fid:
		for line in fid.readlines():
			if line[0] == "#":
				pass
			else:
				questions.append(Question(line))

	# form the corpora
	corpora = [q.corpus for q in questions]

	for q in questions:
		# populate the sentence template
		parameters = dict()

		# ignore the what is question
		if q.parameter_names[0] != "term":
			for label in q.parameter_names:
				node = random.choice(property_to_nodes[label])
				parameters[label] = node
			input_sentence = q.restate_question(parameters)
			input_sentence = input_sentence.strip(string.punctuation)

			# Run it against all the questions
			(corpus_index, similarity) = wd.find_corpus(input_sentence, corpora)
			if questions[corpus_index].restated_question_template.template != q.restated_question_template.template:
				temp_parameters = questions[corpus_index].get_parameters(input_sentence)
				# test if the parameters were populated
				if all([val is not None for val in temp_parameters.values()]):
					print("Bad classification! input: %s\n matched template: %s" % (input_sentence, questions[corpus_index].restated_question_template.template))
					print(questions[corpus_index].get_parameters(input_sentence))

# TODO: It appears that I could make this better by first finding the node name, removing it from the sentence, and *then* doing the find in corpus

