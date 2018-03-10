from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet as wn


def penn_to_wn(tag):
	""" Convert between a Penn Treebank tag to a simplified Wordnet tag """
	if tag.startswith('N'):
		return 'n'

	if tag.startswith('V'):
		return 'v'

	if tag.startswith('J'):
		return 'a'

	if tag.startswith('R'):
		return 'r'

	return None


def tagged_to_synset(word, tag):
	"""
	Get the wordnet set from a word and it's part of speech tag
	:param word: string
	:param tag: string representing part of speech
	:return: wordnet synset
	"""
	wn_tag = penn_to_wn(tag)
	if wn_tag is None:
		return None
	try:
		syn = wn.synsets(word, wn_tag)
		if not syn:
			syn = wn.synsets(word)[0]  # Make a random guess about the part of speech
		else:
			syn = syn[0]
		return syn
	except:
		return None


def sentence_similarity(sentence1, sentence2):
	"""
	Copute sentence similarity based on wordnet
	:param sentence1: input string
	:param sentence2: input string
	:return: float between 0 and 1 giving similarity of sentences
	"""
	# Tokenize and tag
	sentence1_tagged = pos_tag(word_tokenize(sentence1))
	sentence2_tagged = pos_tag(word_tokenize(sentence2))

	# Get the synsets for the tagged words
	synsets1 = [tagged_to_synset(*tagged_word) for tagged_word in sentence1_tagged]
	synsets2 = [tagged_to_synset(*tagged_word) for tagged_word in sentence2_tagged]

	# Filter out the Nones
	synsets1 = [ss for ss in synsets1 if ss]
	synsets2 = [ss for ss in synsets2 if ss]

	score, count = 0.0, 0

	# For each word in the first sentence
	for synset in synsets1:
		# Get the similarity value of the most similar word in the other sentence
		vals = [synset.path_similarity(ss) for ss in synsets2]
		best_score = -1
		# Take max ignoring None's
		for val in vals:
			if val:
				if val > best_score:
					best_score = val
		if best_score == -1:
			best_score = None

		# Check that the similarity could have been computed
		if best_score is not None:
			score += best_score
			count += 1

	# Average the values
	if count != 0:
		score /= count
		#score /= (len(sentence1) + len(sentence2)) / 2.0  # divide by the mean sentence length
	else:
		score = 0.0

	# If the number of synset's is small, no confidence in similarity
	if count <= 3:
		sentence1_set = set([i.lower() for i in word_tokenize(sentence1)])
		sentence2_set = set([i.lower() for i in word_tokenize(sentence2)])
		jaccard = len(sentence1_set.intersection(sentence2_set)) / float(len(sentence1_set.union(sentence2_set)))
		score = jaccard
	#return max(score, jaccard)
	return score


def symmetric_sentence_similarity(sentence1, sentence2):
	"""
	Compute symmetric sentence similarity based on word net
	:param sentence1: input string
	:param sentence2: input string
	:return: float between 0 and 1 representing sentence similarity
	"""
	# TODO: see if taking max is better
	return (sentence_similarity(sentence1, sentence2) + sentence_similarity(sentence2, sentence1)) / 2


def wordnet_max_corpus(sentence, corpus):
	return max([symmetric_sentence_similarity(sentence, s) for s in corpus])


def wordnet_find_corpus(sentence, corpus_list):
	"""
	From a list of corpora (a corpus is a list of example questions), find the one that gives the largest
	wordnet distance.
	:param sentence: input sentence
	:param corpus_list: list of list of strings
	:return: tuple: tup[0] is location of max, tup[1] is the maximum value
	"""
	max_val = 0
	max_index = -1
	for i in range(len(corpus_list)):
		dist = wordnet_max_corpus(sentence, corpus_list[i])
		if dist > max_val:
			max_val = dist
			max_index = i
	if max_index == -1:
		raise Exception("All wordnet distances where 0.")
	else:
		return (max_index, max_val)


def test():
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
	]

	Q2_corpus = [
		"what is the clinical outcome pathway of for the treatment",
		"what is the clinical outcome pathway for the treatment of with ",
		"what is the COP for the treatment of "
	]

	question = "what are the protein targets of ibuprofen"
	res = wordnet_find_corpus(question, [Q2_corpus, Q4_corpus])
	assert res[0] == 1

	question = "What is the clinical outcome pathway of physostigmine for treatment of glaucoma?"
	res = wordnet_find_corpus(question, [Q2_corpus, Q4_corpus])
	assert res[0] == 0




# Make a custom corpus from plaintext
#my_sent_tokenizer = nltk.RegexpTokenizer('[^.!?]+')
#my_genesis = nltk.corpus.PlaintextCorpusReader('/home/dkoslicki/Downloads/Genesis', '.*\.txt', sent_tokenizer=my_sent_tokenizer)
#print(my_genesis.sents('GenesisERV.txt')[0])
# Now make the custom wordnet corpus
#test_ic = wn.ic(my_genesis)

# Holy crap! Check that out!!
#wn.synsets('glaucoma')[0].path_similarity(wn.synsets('physostigmine')[0])
