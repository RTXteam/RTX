import connexion
import six

from openapi_server.models.entity_query import EntityQuery  # noqa: E501
from openapi_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/NodeSynonymizer")
from node_synonymizer import NodeSynonymizer


def get_entity(q):  # noqa: E501
    """Obtain CURIE and synonym information about a search term

     # noqa: E501

    :param q: A string to search by (name, abbreviation, CURIE, etc.). The parameter may be repeated for multiple search strings.
    :type q: List[str]

    :rtype: object
    """
    synonymizer = NodeSynonymizer()
    response = synonymizer.get_normalizer_results(q)

    return response


def post_entity(body):  # noqa: E501
    """Obtain CURIE and synonym information about search terms

     # noqa: E501

    :param body: List of terms to get information about
    :type body: 

    :rtype: EntityQuery
    """

    synonymizer = NodeSynonymizer()
    response = synonymizer.get_normalizer_results(body)

    return response

