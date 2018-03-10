# An attempt at using rudimentary NLP for question translation
import sys
import os
try:
	from code.reasoningtool.QuestionAnswering import WordnetDistance as wd
except ImportError:
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	import WordnetDistance as wd

# get all the node names and descriptions
try:
	fid = open(os.path.abspath('../../../data/KGmetadata/NodeNamesDescriptions.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/NodeNamesDescriptions.tsv'), 'r')
node_names = set()
node_descriptions = set()
names2descrip = dict()
for line in fid.readlines():
	line = line.strip()
	line_split = line.split('\t')
	name = line_split[0]
	descr = line_split[1]
	node_names.add(name)
	node_descriptions.add(descr)
	names2descrip[name] = descr
fid.close()

# get the edge types
try:
	fid = open(os.path.abspath('../../../data/KGmetadata/EdgeTypes.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/EdgeTypes.tsv'), 'r')
edge_types = list()
for line in fid.readlines():
	line = line.split()
	edge_types.append(line)
fid.close()

# Get the node labels
try:
	fid = open(os.path.abspath('../../../data/KGmetadata/NodeLabels.tsv'), 'r')
except FileNotFoundError:
	fid = open(os.path.abspath('data/KGmetadata/NodeLabels.tsv'), 'r')
node_labels = list()
for line in fid.readlines():
	line = line.split()
	node_labels.append(line)
fid.close()


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
	"what is the COP for the treatment of "
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
]

# source_name, target_label, relationship_type



def find_source_node_name(string):


Q_corpora = [Q0_corpus, Q1_corpus, Q2_corpus, Q4_corpus]
question = "what are the protein targets of acetaminophen"

(corpus_index, similarity) = wd.find_corpus(question, Q_corpora)
