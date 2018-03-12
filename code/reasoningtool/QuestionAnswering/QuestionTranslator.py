# An attempt at using rudimentary NLP for question translation
import sys
import os
import nltk
from nltk.corpus import stopwords
import string
import re
import datetime

# TODO: refactor this to comply with Eric's QuestionTranslator.py

# Import Wordnet Distance
try:
	from code.reasoningtool.QuestionAnswering import WordnetDistance as wd
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import WordnetDistance as wd

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

# Question examples
Q0_corpus = [
	"What is an",
	"What is a",
	"what is"
]

Q1_corpus = [
	"what genetic conditions might offer protection against",
	"what genetic conditions protect against",
	"what genetic diseases might protect against",
	"what genetic conditions offer protection against"
]

Q2_corpus = [
	"what is the clinical outcome pathway of for the treatment",
	"what is the clinical outcome pathway for the treatment of with",
	"what is the COP for the treatment of"
]

Q3_corpus = [
		"What proteins are the target of",
		"what proteins are targeted by",
		"what proteins are in the pathway",
		"what are the phenotypes of the disease",
		"What are the symptoms of the disease",
		"what micrornas control the expression of",
		"what proteins are expressed in",
		"what are the genes associated with",
		"what are the drugs that target",
		"what are the members of the pathway",
		"what proteins are expressed in",
		"what phenotype is associated with",
		"what proteins interact with"
]

Q_corpora = [Q0_corpus, Q1_corpus, Q2_corpus, Q3_corpus]

# get all the node names and descriptions
try:
	fid = open(os.path.abspath('../../data/KGmetadata/NodeNamesDescriptions.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/NodeNamesDescriptions.tsv'), 'r')
node_names = set()
node_descriptions = set()
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
	node_names.add(name)
	node_descriptions.add(descr)
	names2descrip[name] = descr
	descrip2names[descr] = name
fid.close()

# get the edge types
try:
	fid = open(os.path.abspath('../../data/KGmetadata/EdgeTypes.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/EdgeTypes.tsv'), 'r')
edge_types = list()
for line in fid.readlines():
	line = line.strip()
	edge_types.append(line)
fid.close()

# Get the node labels
try:
	fid = open(os.path.abspath('../../data/KGmetadata/NodeLabels.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/NodeLabels.tsv'), 'r')
node_labels = list()
for line in fid.readlines():
	line = line.strip()
	node_labels.append(line)
fid.close()


def restate_question(corpus_index, terms):
	"""
	Helper to restate question
	:param corpus_index:
	:param terms:
	:return:
	"""
	# TODO: this is ugly at the moment
	if corpus_index == 0:
		restated = "What is %s" % terms["term"]
	elif corpus_index == 1:
		restated = "What genetic conditions might offer protection against %s" % terms["disease_name"]
	elif corpus_index == 2:
		restated = "What is the clinical outcome pathway of %s for the treatment of %s" % (names2descrip[terms["drug_name"]], names2descrip[terms["disease_name"]])
	elif corpus_index == 3:
		restated = "What %s %s %s" % (" ".join(terms["target_label"].split("_")), " ".join(terms["relationship_type"].split("_")), names2descrip[terms["source_name"]])
	return restated


def format_answer(results_dict):
	"""
	Format the results (of the term extraction) in struct form
	:param results_dict:
	:return:
	"""
	try:
		input_text = results_dict["input_text"]
		corpus_index = results_dict["corpus_index"]
		terms = results_dict["terms"]
		error_code = results_dict["error_code"]
		error_message = results_dict["error_message"]
	except KeyError:
		print("Error, answer dict is missing some terms:")
		print(results_dict)
		return None  # Raise exception?
	# Corpus index will be in the same order as the corpora.
	# If "not_understood", then the question isn't understood
	# If "illegal_char", then illegal characters in the question
	# If "missing_term", then missing terms
	# If "multiple_terms", then there were multiple terms that could satisfy the question parameters
	if error_code:
		# Then there is an error
		if error_code == "not_understood":
			query = [{"knownQueryTypeId": "", "message": "I do not understand the question '" + input_text + "'",
					  "restatedQuestion": "", "originalQuestion": input_text}]
			# self.logQuery("NotUnderstood", "-", input_text)  # TODO: get logging
			return query

		elif error_code == "illegal_char":
			query = [{"knownQueryTypeId": "", "message": "Illegal characters in the question '" + input_text + "'",
					  "restatedQuestion": "", "originalQuestion": input_text}]
			print(query)
			#self.logQuery("IllegalChars", "-", originalText)  # TODO: get logging
			return query

		elif error_code == "missing_term":
			query = [{"knownQueryTypeId": "Q%s" % corpus_index, "message": "%s" % error_message,
					  "restatedQuestion": "%s" % restate_question(corpus_index, terms), "originalQuestion": input_text}]
			# self.logQuery("MissingTerms", "-", originalText)  # TODO: get logging
			print(query)
			return query

		elif error_code == "multiple_terms":
			query = [{"knownQueryTypeId": "Q%s" % corpus_index, "message": "%s" % error_message,
					  "restatedQuestion": "%s" % restate_question(corpus_index, terms), "originalQuestion": input_text}]
			# self.logQuery("MultipleTerms", "-", originalText)  # TODO: get logging
			print(query)
			return query

	else:
		query = [{"knownQueryTypeId": "Q%s" % corpus_index, "terms": terms,
				  "restatedQuestion": "%s" % restate_question(corpus_index, terms), "originalQuestion": input_text}]
		# self.logQuery("OK", "Q%s" % corpus_index, originalText)  # TODO: get logging
		print(query)
	return query


# A variety of functions to help with term extraction
def find_source_node_name(string, names2descrip, descrip2names):
	"""
	Find an acutal Neo4j KG node name in the string
	:param string:
	:param names2descrip:
	:param descrip2names:
	:return:
	"""
	# exact match
	query = string
	res = None
	if query in names2descrip:
		res = query
	elif query in descrip2names:
		res = descrip2names[query]
	elif False:
		pass
		# TODO: put Arnabs ULMS metathesaurus lookup here
	else:
		res = None
	# Case insensitive match
	query_lower = string.lower()
	for name in names2descrip:
		if name.lower() == query_lower:
			res = name
	for descr in descrip2names:
		if descr.lower() == query_lower:
			res = descrip2names[descr]
	return res


def find_target_label(string, node_labels):
	"""
	Find target label (drug, disease, etc) in string
	:param string:
	:param node_labels:
	:return:
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


def find_edge_type(string, edge_types):
	"""
	Extract edge type from string
	:param string:
	:param edge_types:
	:return:
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


def find_question_parameters(question, Q_corpora):
	"""
	NLP-lite canned query matching, then term extraction (for passing to QX.py parameters)
	:param question:
	:param Q_corpora:
	:return:
	"""
	results_dict = dict()
	results_dict["input_text"] = question
	# First, remove trailing punctuation
	question = question.strip(string.punctuation)

	# Try to pattern match to one of the known queries
	(corpus_index, similarity) = wd.find_corpus(question, Q_corpora)

	if similarity < .25:
		# Unable to match to one of the templates
		results_dict["corpus_index"] = None
		results_dict["terms"] = None
		results_dict["error_code"] = "not_understood"
		results_dict[
			"error_message"] = "Sorry, I was unable to interpret your question. The nearest similar question I can answer is:\n %s" % \
							   Q_corpora[corpus_index][wd.max_in_corpus(question, Q_corpora[corpus_index])[0]]
		return results_dict

	# get every contiguous sub-block in the query
	blocks = []
	question_tokenized = nltk.word_tokenize(question, "english")
	for block_size in range(1, len(question_tokenized)):
		for i in range(len(question_tokenized) - block_size + 1):
			block = " ".join(question_tokenized[i:(i + block_size)])
			blocks.append(block)
	blocks = list(reversed(blocks))  # go bigger to smaller since "is_assoc_with" \subst "gene_assoc_with" after stopword deletion

	# for each block, look for the associated terms in a greedy fashion
	if corpus_index == 3:  # Q4
		source_name = None
		target_label = None
		relationship_type = None
		for block in blocks:
			if source_name is None:
				source_name = find_source_node_name(block, names2descrip, descrip2names)
			if target_label is None:
				target_label = find_target_label(block, node_labels)
			if relationship_type is None:
				relationship_type = find_edge_type(block, edge_types)
			if all(item is not None for item in [source_name, target_label, relationship_type]):
				break

		# Check if all terms were correctly populated, return terms
		if any(item is None for item in [source_name, target_label, relationship_type]):
			error_message = "Sorry, I was unable to find the appropriate terms to answer your question. Missing term(s):\n"
			if source_name is None:
				error_message += "Entity/node name (eg. malaria, acetaminophen, NAIF1, tongue, etc.)\n"
			if target_label is None:
				error_message += "Target node label (eg. %s)\n" % [x.split("_")[1] for x in node_labels]
			if relationship_type is None:
				error_message += "Relationship type (eg. %s)\n" % [" ".join(x.split("_")) for x in edge_types]
			#raise Exception(error_message)
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"source_name": source_name, "target_label": target_label,
									 "relationship_type": relationship_type}
			results_dict["error_code"] = "missing_term"
			results_dict["error_message"] = error_message
			return results_dict
		else:
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"source_name": source_name, "target_label": target_label,
									 "relationship_type": relationship_type}
			results_dict["error_code"] = None
			results_dict["error_message"] = None
			return results_dict

	elif corpus_index == 2:  # Q2 COP question
		drug_name = None
		disease_name = None
		candidate_node_names = []
		# Look for anything that could be a node name
		for block in blocks:
			node = find_source_node_name(block, names2descrip, descrip2names)
			if node is not None:
				candidate_node_names.append(node)

		# Get the node labels
		candidate_node_labels = []
		for node in candidate_node_names:
			node_label = RU.get_node_property(node, "label")  # TODO: Arnab's UMLS lookup
			candidate_node_labels.append(node_label)

		# Check if a drug and a disease were named
		if "pharos_drug" not in candidate_node_labels or "disont_disease" not in candidate_node_labels:
			error_message = "Sorry, I was unable to find the appropriate terms to answer your question. Missing term(s):\n"
			if "pharos_drug" not in candidate_node_labels:
				error_message += "A pharos drug name (eg. acetaminophen, glycamil, tranilast, etc.)"
			if "disont_disease" not in candidate_node_labels:
				error_message += "A disease (eg. diphtheritic cystitis, pancreatic endocrine carcinoma, malaria, clear cell sarcoma, etc.)"
			for i in range(len(candidate_node_labels)):
				label = candidate_node_labels[i]
				if label == "pharos_drug":
					drug_name = candidate_node_names[i]
				if label == "disont_disease":
					disease_name = candidate_node_names[i]
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"drug_name": drug_name, "disease_name": disease_name}
			results_dict["error_code"] = "missing_term"
			results_dict["error_message"] = error_message
			return results_dict

		# Look for the locations of the drugs and diseases
		num_drug = 0
		drug_loc = []
		num_disease = 0
		disease_loc = []
		for i in range(len(candidate_node_labels)):
			label = candidate_node_labels[i]
			if label == "pharos_drug":
				num_drug += 1
				drug_loc.append(i)
			if label == "disont_disease":
				num_disease += 1
				disease_loc.append(i)

		# Throw an error if there are multiple drugs or diseases
		if num_drug > 1 or num_disease > 1:
			error_message = "There seem to be multiple names, this question requires only one drug term and one disease term. Repeats include:"
			if num_drug > 1:
				error_message += "\nDrugs detected: "
				for loc in drug_loc:
					error_message += "%s, " % candidate_node_names[loc]
			if num_disease > 1:
				error_message += "\nDiseases detected: "
				for loc in disease_loc:
					error_message += "%s, " % candidate_node_names[loc]
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"drug_name": drug_name, "disease_name": disease_name}
			results_dict["error_code"] = "multiple_terms"
			results_dict["error_message"] = error_message
			return results_dict

		# Otherwise, everything is in order and return the results
		else:
			drug_name = candidate_node_names[drug_loc[0]]
			disease_name = candidate_node_names[disease_loc[0]]
			#return drug_name, disease_name
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"drug_name": drug_name, "disease_name": disease_name}
			results_dict["error_code"] = None
			results_dict["error_message"] = None
			return results_dict

	elif corpus_index == 1:  # Q1
		disease_name = None
		# Look for a node name, break once one is found (greedy)
		for block in blocks:
			node = find_source_node_name(block, names2descrip, descrip2names)
			if node is not None:
				disease_name = node
				break

		# Get the node label
		node_label = RU.get_node_property(disease_name, "label")  # TODO: Arnab's UMLS lookup
		if node_label != "disont_disease":
			error_message = "This question requires a disease name, I got a %s with the name %s" %(node_label, disease_name)
			#raise Exception(error_message)
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"disease_name": disease_name}
			results_dict["error_code"] = "missing_term"
			results_dict["error_message"] = error_message
			return results_dict
		else:
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"disease_name": disease_name}
			results_dict["error_code"] = None
			results_dict["error_message"] = None
			return results_dict

	elif corpus_index == 0:  # Q0
		# Next, see if it's a "what is" question
		term = None
		text = question
		text = re.sub("\?", "", text)
		text = re.sub("^\s+", "", text)
		text = re.sub("\s+$", "", text)
		text = text.lower()
		match = re.match("what is\s*(a|an)?\s+(.+)", text, re.I)
		if match:
			term = match.group(2)
			term = re.sub("^\s+", "", term)
			term = re.sub("\s+$", "", term)
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"term": term}
			results_dict["error_code"] = None
			results_dict["error_message"] = None
			return results_dict
		else:
			results_dict["corpus_index"] = corpus_index
			results_dict["terms"] = {"term": term}
			results_dict["error_code"] = "missing_term"
			results_dict["error_message"] = "This question type requires an entity name (such as heart, ibuprofen, mixed malaria, etc.)."
			return results_dict


def translate(question):
	"""
	Do the actual translation
	:param question:
	:return:
	"""
	results_dict = find_question_parameters(question, Q_corpora)
	return format_answer(results_dict)

def test_find_question_parameters():
	# No question should match
	question = "what proteins are four score and seven years ago, our fathers..."
	results_dict = find_question_parameters(question, Q_corpora)
	assert results_dict["error_code"] is not None

	# Q4 tests
	question = "what are the protein targets of acetaminophen?"
	results_dict = find_question_parameters(question, Q_corpora)
	source_name = results_dict["terms"]["source_name"]
	target_label = results_dict["terms"]["target_label"]
	relationship_type = results_dict["terms"]["relationship_type"]
	assert source_name == "acetaminophen"
	assert target_label == "uniprot_protein"
	assert relationship_type == "targets"

	question = "what proteins does acetaminophen target"
	results_dict = find_question_parameters(question, Q_corpora)
	source_name = results_dict["terms"]["source_name"]
	target_label = results_dict["terms"]["target_label"]
	relationship_type = results_dict["terms"]["relationship_type"]
	assert source_name == "acetaminophen"
	assert target_label == "uniprot_protein"
	assert relationship_type == "targets"

	question = "what are the phenotypes associated with malaria?"
	results_dict = find_question_parameters(question, Q_corpora)
	source_name = results_dict["terms"]["source_name"]
	target_label = results_dict["terms"]["target_label"]
	relationship_type = results_dict["terms"]["relationship_type"]
	assert source_name == "DOID:12365"
	assert target_label == "phenont_phenotype"
	assert relationship_type == "phenotype_assoc_with"

	question = "what proteins are members of Aflatoxin activation and detoxification"
	results_dict = find_question_parameters(question, Q_corpora)
	source_name = results_dict["terms"]["source_name"]
	target_label = results_dict["terms"]["target_label"]
	relationship_type = results_dict["terms"]["relationship_type"]
	assert source_name == "R-HSA-5423646"
	assert target_label == "uniprot_protein"
	assert relationship_type == "is_member_of"

	question = "MIR4426 controls the expression of which proteins?"
	results_dict = find_question_parameters(question, Q_corpora)
	source_name = results_dict["terms"]["source_name"]
	target_label = results_dict["terms"]["target_label"]
	relationship_type = results_dict["terms"]["relationship_type"]
	assert source_name == "NCBIGene:100616345"
	assert target_label == "uniprot_protein"
	assert relationship_type == "controls_expression_of"

	# Q2 tests
	question = "What is the clinical outcome pathway of physostigmine for treatment of glaucoma"
	results_dict = find_question_parameters(question, Q_corpora)
	drug = results_dict["terms"]["drug_name"]
	disease = results_dict["terms"]["disease_name"]
	assert drug == "physostigmine"
	assert disease == "DOID:1686"

	question = "What is the clinical outcome pathway for the treatment of lactic acidosis by benzilonium"
	results_dict = find_question_parameters(question, Q_corpora)
	drug = results_dict["terms"]["drug_name"]
	disease = results_dict["terms"]["disease_name"]
	assert drug == "benzilonium"
	assert disease == "DOID:3650"

	question = "What is the clinical outcome pathway for the treatment of alcohol abuse by ACAMPROSATE"
	results_dict = find_question_parameters(question, Q_corpora)
	drug = results_dict["terms"]["drug_name"]
	disease = results_dict["terms"]["disease_name"]
	assert drug == "acamprosate"
	assert disease == "DOID:1574"

	question = "What is the COP for the treatment of ISOETHARINE by ISOETHARINE?"
	results_dict = find_question_parameters(question, Q_corpora)
	assert results_dict["error_code"] is not None


	question = "What is the COP for the treatment of Bronchitis by ISOETHARINE"
	results_dict = find_question_parameters(question, Q_corpora)
	drug = results_dict["terms"]["drug_name"]
	disease = results_dict["terms"]["disease_name"]
	assert drug == "isoetharine"
	assert disease == "DOID:6132"

	# Q1 Questions
	question = "what genetic conditions might protect against malaria?"
	results_dict = find_question_parameters(question, Q_corpora)
	disease = results_dict["terms"]["disease_name"]
	assert disease == 'DOID:12365'

	question = "what genetic conditions might protect against mixed malaria?"
	results_dict = find_question_parameters(question, Q_corpora)
	disease = results_dict["terms"]["disease_name"]
	assert disease == 'DOID:14325'

	question = "what genetic conditions might protect against bone marrow cancer?"
	results_dict = find_question_parameters(question, Q_corpora)
	disease = results_dict["terms"]["disease_name"]
	assert disease == 'DOID:4960'

	question = "what genetic conditions might protect against cerebral sarcoidosis?"
	results_dict = find_question_parameters(question, Q_corpora)
	disease = results_dict["terms"]["disease_name"]
	assert disease == 'DOID:13403'

	# Q0 Questions
	question = "What is Creutzfeldt Jakob disease, subtype I"
	results_dict = find_question_parameters(question, Q_corpora)
	term = results_dict["terms"]["term"]
	assert term == "creutzfeldt jakob disease, subtype i"

	question = "What is a dog"
	results_dict = find_question_parameters(question, Q_corpora)
	term = results_dict["terms"]["term"]
	assert term == "dog"

	question = "What is an otolith"
	results_dict = find_question_parameters(question, Q_corpora)
	term = results_dict["terms"]["term"]
	assert term == "otolith"




