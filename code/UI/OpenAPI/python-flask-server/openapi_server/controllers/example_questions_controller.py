import connexion
import six

from openapi_server import util

from QuestionExamples import QuestionExamples


def example_questions():  # noqa: E501
    """Request a list of example questions that ARAX can answer

     # noqa: E501


    :rtype: List[object]
    """
    exampleQuestions = QuestionExamples()
    return(exampleQuestions.questions)
