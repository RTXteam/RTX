import Question
import os
from importlib import reload
reload(Question)

questions = []
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Questions.tsv'), "r") as fid:
	for line in fid.readlines():
		if line[0] == "#":
			pass
		else:
			questions.append(Question.Question(line))

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
