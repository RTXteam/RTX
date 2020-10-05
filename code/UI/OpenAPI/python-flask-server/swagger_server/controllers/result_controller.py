import connexion
import six

from swagger_server.models.feedback import Feedback  # noqa: E501
from swagger_server.models.result import Result  # noqa: E501
from swagger_server.models.result_feedback import ResultFeedback  # noqa: E501
from swagger_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../Feedback/")
from RTXFeedback import RTXFeedback


def get_result(result_id):  # noqa: E501
    """Request stored result

     # noqa: E501

    :param result_id: Integer identifier of the result to return
    :type result_id: int

    :rtype: Result
    """
    return( { "status": 501, "title": "EndpointNotImplemented", "detail": "This endpoint is no longer implemented", "type": "about:blank" }, 501 )


def get_result_feedback(result_id):  # noqa: E501
    """Request stored feedback for this result

     # noqa: E501

    :param result_id: Integer identifier of the result to return
    :type result_id: int

    :rtype: ResultFeedback
    """
    return( { "status": 501, "title": "EndpointNotImplemented", "detail": "This endpoint is no longer implemented", "type": "about:blank" }, 501 )

def post_result_feedback(result_id, body):  # noqa: E501
    """Store feedback for a particular result

     # noqa: E501

    :param result_id: Integer identifier of the result to return
    :type result_id: int
    :param body: Comment information
    :type body: dict | bytes

    :rtype: None
    """
    return( { "status": 501, "title": "EndpointNotImplemented", "detail": "This endpoint is no longer implemented", "type": "about:blank" }, 501 )

