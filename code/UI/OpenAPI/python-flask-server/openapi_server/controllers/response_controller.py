import connexion
import six

from openapi_server.models.response import Response  # noqa: E501
from openapi_server import util

from RTXFeedback import RTXFeedback


def get_response(response_id):  # noqa: E501
    """Request a previously stored response from the server

     # noqa: E501

    :param response_id: Integer identifier of the response to return
    :type response_id: int

    :rtype: Response
    """

    rtxFeedback = RTXFeedback()
    return rtxFeedback.getMessage(message_id)

