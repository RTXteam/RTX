# This script will handle the parsing of a user input question

import os
import sys


class QuestionExamples:
	def __init__(self):
		self.read_reference_file()


	def read_reference_file(self)
		with open(os.path.join(os.path.dirname(__file__), 'QuestionExamples.tsv'), 'r') as fid:
			questions = []
			for line in fid.readlines():
				if line[0] == "#":
					pass
				else:
					questions.append(line)
			self._questions = questions


	def get_questions(self)
		pass

def main():
	questions = QuestionExamples()


def tests():
	questions = QuestionExamples()
	assert questions is not None
	return

if __name__ == "__main__":
	main()
