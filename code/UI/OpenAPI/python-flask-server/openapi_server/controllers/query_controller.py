import connexion
import six
import ast

from openapi_server.models.message import Message  # noqa: E501
from openapi_server import util

from RTXQuery import RTXQuery


def query(request_body):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: dict | bytes

    :rtype: Message
    """
    if connexion.request.is_json:
        query = connexion.request.get_json()
        rtxq = RTXQuery()
        message = rtxq.query(query)
        return(ast.literal_eval(repr(message)))
    else:
        return( { "status": 502, "title": "body content not JSON", "detail": "Required body content is not JSON", "type": "about:blank" }, 502 )
