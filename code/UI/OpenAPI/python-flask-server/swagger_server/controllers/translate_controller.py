import connexion
import six

from swagger_server.models.query import Query  # noqa: E501
from swagger_server.models.question import Question  # noqa: E501
from swagger_server import util


def translate(body):  # noqa: E501
    """Translate natural language question into a standardized query

     # noqa: E501

    :param body: Question object that needs to be translated
    :type body: dict | bytes

    :rtype: List[Query]
    """
    if connexion.request.is_json:
        body = Question.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
