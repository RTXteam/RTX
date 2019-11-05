import connexion
import six

from openapi_server.models.feedback import Feedback  # noqa: E501
from openapi_server.models.feedback_response import FeedbackResponse  # noqa: E501
from openapi_server.models.result import Result  # noqa: E501
from openapi_server.models.result_feedback import ResultFeedback  # noqa: E501
from openapi_server import util

from RTXFeedback import RTXFeedback


def get_result(result_id):  # noqa: E501
    """Request stored result

     # noqa: E501

    :param result_id: Integer identifier of the result to return
    :type result_id: int

    :rtype: Result
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResult(result_id)


def get_result_feedback(result_id):  # noqa: E501
    """Request stored feedback for this result

     # noqa: E501

    :param result_id: Integer identifier of the result to return
    :type result_id: int

    :rtype: ResultFeedback
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResultFeedback(result_id)


def post_result_feedback(result_id, feedback):  # noqa: E501
    """Store feedback for a particular result

     # noqa: E501

    :param result_id: Integer identifier of the result to return
    :type result_id: int
    :param feedback: Comment information
    :type feedback: dict | bytes

    :rtype: FeedbackResponse
    """
    if connexion.request.is_json:
        #feedback = Feedback.from_dict(connexion.request.get_json())  # noqa: E501

        ratingData = connexion.request.get_json()
        rtxFeedback = RTXFeedback()
        response = rtxFeedback.addNewResultRating(result_id, ratingData)
        return(response)
    else:
        return( { "status": 502, "title": "body content not JSON", "detail": "Required body content is not JSON", "type": "about:blank" }, 502 )
