import connexion
import six

from openapi_server.models.message import Message  # noqa: E501
from openapi_server.models.message_feedback import MessageFeedback  # noqa: E501
from openapi_server import util


def get_message(message_id):  # noqa: E501
    """Request stored messages and results from reasoner

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: Message
    """
    return 'do some magic!'


def get_message_feedback(message_id):  # noqa: E501
    """Request stored feedback for this message from reasoner

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: MessageFeedback
    """
    return 'do some magic!'
