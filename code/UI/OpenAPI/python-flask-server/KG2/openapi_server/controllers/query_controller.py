import connexion
import six

# Import to allow streaming of progress information
from flask import stream_with_context, request, Response

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../../ARAX/ARAXQuery")
from ARAX_query import ARAXQuery


def query(request_body, bypass_cache=None):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: dict | bytes
    :param bypass_cache: Set to true in order to bypass any possible cached response and try to answer the query over again 
    :type bypass_cache: bool

    :rtype: Response
    """

    # Note that we never even get here if the request_body is not schema-valid JSON

    query = connexion.request.get_json()
    araxq = ARAXQuery()

    if "asynchronous" in query and query['asynchronous'].lower() == 'stream':
        # Return a stream of data to let the client know what's going on
        return Response(araxq.query_return_stream(query, mode='RTXKG2'),mimetype='text/plain')

    # Else perform the query and return the result
    else:
        envelope = araxq.query_return_message(query, mode='RTXKG2')
        return envelope
