import connexion
import six

from openapi_server.models.query import Query  # noqa: E501
from openapi_server import util


def translate(request_body):  # noqa: E501
    """Translate natural language question into a standardized query

     # noqa: E501

    :param request_body: Question information to be translated
    :type request_body: dict | bytes

    :rtype: List[Query]
    """
    return 'do some magic!'
