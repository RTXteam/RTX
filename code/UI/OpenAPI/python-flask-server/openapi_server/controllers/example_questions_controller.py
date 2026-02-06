import connexion
import six
import sys
import os

from openapi_server import util

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../../reasoningtool/QuestionAnswering")

from QuestionExamples import QuestionExamples


def example_questions():  # noqa: E501
    """Request a list of example questions that ARAX can answer

     # noqa: E501


    :rtype: List[object]
    """
    exampleQuestions = QuestionExamples()
    return(exampleQuestions.questions)
