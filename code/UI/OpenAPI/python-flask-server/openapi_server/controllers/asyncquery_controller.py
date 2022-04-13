import connexion
import six

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/ARAXQuery")
from ARAX_query import ARAXQuery


def asyncquery(request_body):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: Dict[str, ]

    :rtype: Response
    """

    # Note that we never even get here if the request_body is not schema-valid JSON

    query = connexion.request.get_json()

    #### Record the remote IP address in the query for now so it is available downstream
    try:
        query['remote_address'] = connexion.request.headers['x-forwarded-for']
    except:
        query['remote_address'] = '???'

    araxq = ARAXQuery()

    envelope = araxq.query_return_message(query, mode='asynchronous')
    http_status = 200
    if hasattr(envelope, 'http_status'):
        http_status = envelope.http_status
    return(envelope,http_status)


