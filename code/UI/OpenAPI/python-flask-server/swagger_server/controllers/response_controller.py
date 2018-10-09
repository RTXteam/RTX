import connexion
import six

from swagger_server.models.response import Response  # noqa: E501
from swagger_server.models.response_envelope import ResponseEnvelope  # noqa: E501
from swagger_server.models.response_feedback import ResponseFeedback  # noqa: E501
from swagger_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../Feedback/")
from RTXFeedback import RTXFeedback


def get_response(response_id):  # noqa: E501
    """Request stored responses and results from RTX

     # noqa: E501

    :param response_id: Integer identifier of the response to return
    :type response_id: int

    :rtype: Response
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResponse(response_id)


def get_response_feedback(response_id):  # noqa: E501
    """Request stored feedback for this response from RTX

     # noqa: E501

    :param response_id: Integer identifier of the response to return
    :type response_id: int

    :rtype: ResponseFeedback
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResponseFeedback(response_id)


def post_response(body=None):  # noqa: E501
    """Process a Response object from somewhere else, controlled by options

     # noqa: E501

    :param body: Envelope for a Response that should be processed
    :type body: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        body = ResponseEnvelope.from_dict(connexion.request.get_json())  # noqa: E501
    rtxFeedback = RTXFeedback()
    return rtxFeedback.processExternalResponseEnvelope(body)

