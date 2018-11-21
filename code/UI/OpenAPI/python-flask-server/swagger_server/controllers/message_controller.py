import connexion
import six

from swagger_server.models.message import Message  # noqa: E501
from swagger_server.models.message_feedback import MessageFeedback  # noqa: E501
from swagger_server import util


def get_message(message_id):  # noqa: E501
    """Request stored messages and results from RTX

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: Message
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResponse(response_id)


def get_message_feedback(message_id):  # noqa: E501
    """Request stored feedback for this message from RTX

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: MessageFeedback
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getResponseFeedback(response_id)

