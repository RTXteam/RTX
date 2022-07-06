import connexion
import six

from openapi_server.models.response import Response  # noqa: E501
from openapi_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/ResponseCache")
from response_cache import ResponseCache


def get_response(response_id):  # noqa: E501
    """Request a previously stored response from the server

     # noqa: E501

    :param response_id: Identifier of the response to return
    :type response_id: str

    :rtype: Response
    """

    response_cache = ResponseCache()
    envelope = response_cache.get_response(response_id)
    return envelope


def post_response(body):  # noqa: E501
    """Annotate a response

     # noqa: E501

    :param body: Object that provides annotation information
    :type body: 

    :rtype: object
    """
    response_cache = ResponseCache()
    response_cache.store_callback(body)
    return 'received!'

