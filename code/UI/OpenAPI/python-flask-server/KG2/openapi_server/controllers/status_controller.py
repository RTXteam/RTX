import connexion
import six

from openapi_server import util


def get_status(last_n_hours=None, incomplete_only=None):  # noqa: E501
    """Obtain status information about the endpoint

     # noqa: E501

    :param last_n_hours: Limit results to the past N hours
    :type last_n_hours: int
    :param incomplete_only: Set to True if only incomplete queries should be returned
    :type incomplete_only: str

    :rtype: object
    """
    return 'do some magic!'
