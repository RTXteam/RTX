import connexion
import six

from openapi_server.models.message import Message  # noqa: E501
from openapi_server.models.message_feedback import MessageFeedback  # noqa: E501
from openapi_server import util

from RTXFeedback import RTXFeedback


def get_message(message_id):  # noqa: E501
    """Request stored messages and results from reasoner

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: Message
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getMessage(message_id)


def get_message_feedback(message_id):  # noqa: E501
    """Request stored feedback for this message from reasoner

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: MessageFeedback
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getMessageFeedback(message_id)
