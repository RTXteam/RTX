# An attempt at using rudimentary NLP for question translation
import sys
import os
import re
import nltk
from nltk.corpus import stopwords

try:
	from code.reasoningtool.QuestionAnswering import WordnetDistance as wd
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import WordnetDistance as wd

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

Q4_corpus = [
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

# get all the node names and descriptions
try:
	fid = open(os.path.abspath('../../../data/KGmetadata/NodeNamesDescriptions.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/NodeNamesDescriptions.tsv'), 'r')
node_names = set()
node_descriptions = set()
names2descrip = dict()
descrip2names = dict()  # TODO: this assumes that descriptions are unique, and this will change soon
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
	fid = open(os.path.abspath('../../../data/KGmetadata/EdgeTypes.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/EdgeTypes.tsv'), 'r')
edge_types = list()
for line in fid.readlines():
	line = line.strip()
	edge_types.append(line)
fid.close()

# Get the node labels
try:
	fid = open(os.path.abspath('../../../data/KGmetadata/NodeLabels.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/NodeLabels.tsv'), 'r')
node_labels = list()
for line in fid.readlines():
	line = line.strip()
	node_labels.append(line)
fid.close()


def find_source_node_name(string, names2descrip, descrip2names):
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
	# drop any "s" endings
	p = nltk.stem.snowball.SnowballStemmer("english")  # TODO: "conditions"->"condit"
	query = p.stem(string)
	node_labels_space = []
	# replace underscore with space
	for label in node_labels:
		label = label.replace('_',' ')
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
	p = nltk.stem.snowball.SnowballStemmer("english")
	res = None
	# remove underscores
	edge_types_space = []
	for et in edge_types:
		edge_types_space.append(et.replace('_', ' '))
	# standarize the string by making it lowercase and removing stop words
	query = string.lower()
	query_tokens = nltk.word_tokenize(query, "english")
	query_no_stop = set(query_tokens).difference(set(stopwords.words('english')))
	query_clean = ""
	for word in query_no_stop:
		query_clean += p.stem(word) + " "
	# see if it matches any of the standardized edge types
	for i in range(len(edge_types_space)):
		et = edge_types_space[i]
		et_tokens = nltk.word_tokenize(et)
		et_no_stop = set(et_tokens).difference(set(stopwords.words('english')))
		et_clean = ""
		for word in et_no_stop:
			et_clean += p.stem(word) + " "
		if query_clean == et_clean:
			res = edge_types[i]
	return res

Q_corpora = [Q0_corpus, Q1_corpus, Q2_corpus, Q4_corpus]
question = "what are the protein targets of acetaminophen"
question = "what proteins does acetaminophen target"

(corpus_index, similarity) = wd.find_corpus(question, Q_corpora)

# source_name, target_label, relationship_type
# get every contiguous sub-block in the query
blocks = []
question_tokenized = nltk.word_tokenize(question, "english")
for block_size in range(1,len(question_tokenized)):
	for i in range(len(question_tokenized) - block_size + 1):
		block = " ".join(question_tokenized[i:(i + block_size)])
		blocks.append(block)

# 'what are the protein targets of acetaminophen'
# for each block, look for the associated terms in a greedy fashion
if corpus_index == 3:  #Q4
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
	print(source_name)
	print(target_label)
	print(relationship_type)

# then go ahead an call Q4
from Q4 import Q4
Q = Q4()
Q.answer(source_name, target_label, relationship_type)



