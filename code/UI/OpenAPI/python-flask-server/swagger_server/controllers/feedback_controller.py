import connexion
import six

from swagger_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../Feedback/")
from RTXFeedback import RTXFeedback


def get_feedback_all():  # noqa: E501
    """Request a list of all feedback provided thus far

     # noqa: E501


    :rtype: None
    """
    return( { "status": 501, "title": "EndpointNotImplemented", "detail": "This endpoint is no longer implemented", "type": "about:blank" }, 501 )


def get_feedback_expertise_levels():  # noqa: E501
    """Request a list of allowable expertise levels

     # noqa: E501


    :rtype: None
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getExpertiseLevels()


def get_feedback_ratings():  # noqa: E501
    """Request a list of allowable ratings

     # noqa: E501


    :rtype: None
    """
    rtxFeedback = RTXFeedback()
    return rtxFeedback.getRatings()
