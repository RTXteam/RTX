import connexion
import flask
import json

import os
import sys
from typing import Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../../ARAX/ARAXQuery")
from ARAX_query import ARAXQuery


def asyncquery(request_body: dict[str, Any]):  # noqa: E501
    """Initiate a query with a callback to receive the response

    :param request_body: Query information to be submitted
    :type request_body: dict[str, Any]

    :rtype: AsyncQueryResponse
    """

    # Note that we never even get here if the request_body is not schema-valid JSON

    query = connexion.request.get_json()

    #### Record the remote IP address in the query for now so it is available downstream
    try:
        query['remote_address'] = connexion.request.headers['x-forwarded-for']
    except KeyError:
        query['remote_address'] = '???'

    araxq = ARAXQuery()

    envelope = araxq.query_return_message(query, mode='asynchronous')
    envelope_dict = envelope.to_dict()
    http_status = getattr(envelope, 'http_status', 200)
    response_serialized_str = json.dumps(envelope_dict, sort_keys=True, allow_nan=False) + "\n"
    resp_obj = flask.Response(response_serialized_str)
    return (resp_obj, http_status)


