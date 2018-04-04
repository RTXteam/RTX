import Question
import os, sys
from importlib import reload
reload(Question)
import string
import WordnetDistance as wd


questions = []
try:
	fid = open('/home/dkoslicki/Dropbox/Repositories/RTX/code/reasoningtool/QuestionAnswering/Questions.tsv', "r")
except FileNotFoundError:
	try:
		fid = open('/home/dkoslicki/Desktop/RTX/code/reasoningtool/QuestionAnswering/Questions.tsv', "r")
	except FileNotFoundError:
		fid = open(os.path.join(os.path.dirname(__file__), 'Questions.tsv'), 'r')
i = 0
for line in fid.readlines():
	if line[0] == "#":
		pass
	else:
		print(i, line)
		i += 1
		questions.append(Question.Question(line))
fid.close()

# The list Questions has elements given by the Question class
# for example, can print the templates
for q in questions:
	print(q.restate_question({}))

# Get the question parameters
print(questions[0].get_parameters("what is dog"))
print(questions[1].get_parameters("What genetic conditions may protect against malaria?"))

# See what happens when it can't extract parameters
print(questions[1].get_parameters("What genetic conditions may protect against asdfasdf?"))

# See how it can restate a question
parameters = questions[1].get_parameters("What genetic conditions may protect against mixed malaria?")
print(questions[1].restate_question(parameters))

# Do the semantic matching, extract the parameters, return the restated question
input_question = "What genetic conditions might offer protection against malaria?"
corpora = [q.corpus for q in questions]
input_question = input_question.strip(string.punctuation)
# Try to pattern match to one of the known queries
(corpus_index, similarity) = wd.find_corpus(input_question, corpora)
parameters = questions[corpus_index].get_parameters(input_question)
print(questions[corpus_index].restate_question(parameters))

# Look at the similarity of restated questions with other templates (just return the running max)
max = 0
for q1 in questions:
	for q2 in questions:
		if q1.restated_question_template.template != q2.restated_question_template.template:
			for sentence in q2.corpus:
				(index, similarity) = wd.find_corpus(sentence, [q1.corpus])
				#print("sentence: %s \t corpus %s \t %f" % (sentence, q1.restated_question_template.template,similarity))
				#print(similarity)
				if similarity >= max:
					max = similarity
					#print(max)
					print("sentence: %s \t corpus %s \t %f" % (sentence, q1.restated_question_template.template, similarity))
