import connexion
import six
from flask import stream_with_context, request, Response

from swagger_server.models.message import Message  # noqa: E501
from swagger_server.models.query import Query  # noqa: E501
from swagger_server import util
from ARAX_query import ARAXQuery


def query(body):  # noqa: E501
    """Query ARAX via one of several inputs

     # noqa: E501

    :param body: Query information to be submitted
    :type body: dict | bytes

    :rtype: Message
    """
    if connexion.request.is_json:
        query = connexion.request.get_json()
        araxq = ARAXQuery()

        if "asynchronous" in query and query['asynchronous'].lower() == 'stream':
            # Return a stream of data to let the client know what's going on
            return Response(araxq.query_return_stream(query),mimetype='text/plain')
        else:
            message = araxq.query_return_message(query)
            return message

