import Question
from importlib import reload
reload(Question)



questions = []
with open("/home/dkoslicki/Dropbox/Repositories/RTX/code/reasoningtool/QuestionAnswering/Questions.tsv", "r") as fid:
	for line in fid.readlines():
		if line[0] == "#":
			pass
		else:
			questions.append(Question.Question(line))

# The list Questions has elements given by the Question class
# for example, can print the templates
for q in questions:
	print(q.restate_question({}))
