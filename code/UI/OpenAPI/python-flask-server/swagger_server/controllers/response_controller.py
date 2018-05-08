import connexion
import six

from swagger_server.models.query import Query  # noqa: E501
from swagger_server.models.response import Response  # noqa: E501
from swagger_server.models.response_feedback import ResponseFeedback  # noqa: E501
from swagger_server.models.result import Result  # noqa: E501
from swagger_server.models.result_feedback import ResultFeedback  # noqa: E501
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
    return 'do some magic!'


def get_response_feedback(response_id):  # noqa: E501
    """Request stored feedback for this response from RTX

     # noqa: E501

    :param response_id: Integer identifier of the response to return
    :type response_id: int

    :rtype: ResponseFeedback
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResponseFeedback(response_id)


def get_result(response_id, result_id):  # noqa: E501
    """Request stored responses and results from RTX

     # noqa: E501

    :param response_id: Integer identifier of the response to return
    :type response_id: int
    :param result_id: Integer identifier of the result to return
    :type result_id: int

    :rtype: Result
    """
    return 'do some magic!'


def get_result_feedback(response_id, result_id):  # noqa: E501
    """Request stored feedback for this result from RTX

     # noqa: E501

    :param response_id: Integer identifier of the response to return
    :type response_id: int
    :param result_id: Integer identifier of the result to return
    :type result_id: int

    :rtype: ResultFeedback
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResultFeedback(response_id, result_id)


def post_result_feedback(response_id, result_id, body):  # noqa: E501
    """Store feedback for a particular result

     # noqa: E501

    :param response_id: Integer identifier of the response to return
    :type response_id: int
    :param result_id: Integer identifier of the result to return
    :type result_id: int
    :param body: Feedback information to be submitted
    :type body: dict | bytes

    :rtype: Response
    """
    if connexion.request.is_json:
        ratingData = connexion.request.get_json()  # noqa: E501
        rtxFeedback = RTXFeedback()
        response = rtxFeedback.addNewResultRating(result_id, ratingData)
        return(response)
    return( { "status": 502, "title": "body content not JSON", "detail": "Required body content is not JSON", "type": "about:blank" }, 502 )

