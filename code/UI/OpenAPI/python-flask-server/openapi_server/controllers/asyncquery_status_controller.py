import connexion
import six

from openapi_server.models.async_query_status_response import AsyncQueryStatusResponse  # noqa: E501
from openapi_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/ARAXQuery")
from ARAX_query_tracker import ARAXQueryTracker


def asyncquery_status(job_id):  # noqa: E501
    """Retrieve the current status of a previously submitted asyncquery given its job_id

     # noqa: E501

    :param job_id: Identifier of the job for status request
    :type job_id: str

    :rtype: AsyncQueryStatusResponse
    """

    query_tracker = ARAXQueryTracker()

    response = query_tracker.get_job_status(job_id)

    if response.status == 'UnknownJobId':
        return( { "status": 404, "title": "Job id not found", "detail": response, "type": "about:blank" }, 404 )

    return response

