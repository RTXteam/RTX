import connexion
import six

from swagger_server.models.query import Query  # noqa: E501
from swagger_server.models.response import Response  # noqa: E501
from swagger_server import util
from RTXQuery import RTXQuery


def query(body):  # noqa: E501
    """Query RTX using a predefined question type

     # noqa: E501

    :param body: Query information to be submitted
    :type body: dict | bytes

    :rtype: Response
    """
    if connexion.request.is_json:
        query = connexion.request.get_json()
        rtxq = RTXQuery()
        result = rtxq.query(query)
    return result
