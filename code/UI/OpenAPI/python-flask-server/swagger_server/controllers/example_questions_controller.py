import connexion
import six

from swagger_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../reasoningtool/QuestionAnswering/")
from QuestionExamples import QuestionExamples


def example_questions():  # noqa: E501
    """Request a list of example questions that RTX can answer

     # noqa: E501


    :rtype: None
    """
    exampleQuestions = QuestionExamples()
    return(exampleQuestions.questions)
