import six
import os
import sys

from openapi_server import util
from ARAX_query_tracker import ARAXQueryTracker


def get_status(last_n_hours=None, id_=None, terminate_pid=None, authorization=None):  # noqa: E501
    """Obtain status information about the endpoint

     # noqa: E501

    :param last_n_hours: Limit results to the past N hours
    :type last_n_hours: int
    :param id: Identifier of the log entry
    :type id: int
    :param terminate_pid: PID of an ongoing query to terminate
    :type terminate_pid: int
    :param authorization: Authorization string required for certain calls to status
    :type authorization: str

    :rtype: object
    """

    query_tracker = ARAXQueryTracker()
    if terminate_pid is not None:
        status = query_tracker.terminate_job(terminate_pid, authorization)
    else:
        status = query_tracker.get_status(last_n_hours=last_n_hours, id_=id_)
    return status


def get_logs(mode=None):  # noqa: E501
    """Get log information from the server

     # noqa: E501

    :param mode: Specify the log sending mode
    :type mode: string

    :rtype: string
    """

    if mode is not None and mode == 'env':
        return str(os.environ)

    query_tracker = ARAXQueryTracker()
    status = query_tracker.get_logs(mode=mode)
    return status
