import connexion
import six
import ast

from openapi_server.models.response import Response  # noqa: E501
from openapi_server import util

from RTXQuery import RTXQuery


def query(request_body, bypass_cache=None):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: dict | bytes
    :param bypass_cache: Set to true in order to bypass any possible cached response and try to answer the query over again 
    :type bypass_cache: bool

    :rtype: Response
    """
    if connexion.request.is_json:
        query = connexion.request.get_json()
        rtxq = RTXQuery()
        message = rtxq.query(query)
        return(ast.literal_eval(repr(message)))
    else:
        return( { "status": 502, "title": "body content not JSON", "detail": "Required body content is not JSON", "type": "about:blank" }, 502 )
