# This script will handle the parsing of a user input question

import os
import sys


class QuestionExamples:
	def __init__(self):
		self.read_reference_file()

	#### Define attribute questions
	@property
	def questions(self) -> str:
		return self._questions

	@questions.setter
	def questions(self, questions: list):
		self._questions = questions

	def read_reference_file(self):
		with open(os.path.join(os.path.dirname(__file__), 'QuestionExamples.tsv'), 'r') as fid:
			questions = []
			for line in fid.readlines():
				if line[0] == "#":
					pass
				else:
					columns = line.strip("\n").split("\t")
					if columns[1] == "true":
						question = { "query_type_id": columns[0], "question_text": columns[2] }
						questions.append(question)
			self._questions = questions


def main():
	questions = QuestionExamples()
	print(questions.questions)

def tests():
	questions = QuestionExamples()
	assert questions is not None
	return

if __name__ == "__main__":
	main()
