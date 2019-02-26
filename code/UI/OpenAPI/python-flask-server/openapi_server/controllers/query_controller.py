import connexion
import six

from openapi_server.models.message import Message  # noqa: E501
from openapi_server import util


def query(request_body):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: dict | bytes

    :rtype: Message
    """
    return 'do some magic!'
