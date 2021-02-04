import connexion
import six

from openapi_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/NodeSynonymizer")
from node_synonymizer import NodeSynonymizer


def get_entity_by_string(search_string):  # noqa: E501
    """Obtain the CURIE and type of some entity by name

     # noqa: E501

    :param search_string: Some string to search by (name, abbreviation, CURIE, etc.)
    :type search_string: str

    :rtype: List[object]
    """
    synonymizer = NodeSynonymizer()
    if False:
        result = synonymizer.get_canonical_curies(curies=search_string,names=search_string)
        response = {}
        if result[search_string] is not None:
            response = { 'curie': result[search_string]['preferred_curie'], 'name': result[search_string]['preferred_name'], 'type': result[search_string]['preferred_type'] }
    else:
        response = synonymizer.get_normalizer_results([search_string],kg_name='KG2')

    return response

