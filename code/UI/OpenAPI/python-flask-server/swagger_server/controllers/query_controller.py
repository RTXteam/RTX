import connexion
from swagger_server.models.query import Query
from swagger_server.models.response import Response
from datetime import date, datetime
from typing import List, Dict
from six import iteritems
from ..util import deserialize_date, deserialize_datetime
from RTXQuery import RTXQuery

def query(body):
    """
    Query RTX using a predefined question type
    
    :param body: Query information to be submitted
    :type body: dict | bytes

    :rtype: List[Response]
    """

    result = None
    if connexion.request.is_json:
        #body = Query.from_dict(connexion.request.get_json())
        query = connexion.request.get_json()
        rtxq = RTXQuery()
        result = rtxq.query(query)
    return result
