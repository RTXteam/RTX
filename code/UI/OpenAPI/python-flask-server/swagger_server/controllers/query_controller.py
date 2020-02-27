import connexion
import six

from swagger_server.models.message import Message  # noqa: E501
from swagger_server.models.query import Query  # noqa: E501
from swagger_server import util
from ARAX_query import ARAXQuery


def query(body):  # noqa: E501
    """Query ARAX via one of several inputs

     # noqa: E501

    :param body: Query information to be submitted
    :type body: dict | bytes

    :rtype: Message
    """
    if connexion.request.is_json:
        query = connexion.request.get_json()
        araxq = ARAXQuery()
        message = araxq.query_return_message(query)
    return message
