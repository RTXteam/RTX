import connexion
import six

from openapi_server.models.expertise_levels import ExpertiseLevels  # noqa: E501
from openapi_server.models.feedback import Feedback  # noqa: E501
from openapi_server.models.ratings import Ratings  # noqa: E501
from openapi_server import util


def get_feedback_all():  # noqa: E501
    """Request a list of all feedback provided thus far

     # noqa: E501


    :rtype: List[Feedback]
    """
    return 'do some magic!'


def get_feedback_expertise_levels():  # noqa: E501
    """Request a list of allowable expertise levels

     # noqa: E501


    :rtype: ExpertiseLevels
    """
    return 'do some magic!'


def get_feedback_ratings():  # noqa: E501
    """Request a list of allowable ratings

     # noqa: E501


    :rtype: Ratings
    """
    return 'do some magic!'
