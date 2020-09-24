import connexion
import six

from swagger_server.models.message import Message  # noqa: E501
from swagger_server.models.message_feedback import MessageFeedback  # noqa: E501
from swagger_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../Feedback/")
from RTXFeedback import RTXFeedback


def get_message(message_id):  # noqa: E501
    """Request stored messages and results from RTX

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: Message
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getMessage(message_id)


def get_message_feedback(message_id):  # noqa: E501
    """Request stored feedback for this message from RTX

     # noqa: E501

    :param message_id: Integer identifier of the message to return
    :type message_id: int

    :rtype: MessageFeedback
    """
    return( { "status": 501, "title": "EndpointNotImplemented", "detail": "This endpoint is no longer implemented", "type": "about:blank" }, 501 )

