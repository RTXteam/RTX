import connexion
import six

from swagger_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../reasoningtool/kg-construction")
from KGNodeIndex import KGNodeIndex

def get_entity_by_string(search_string):  # noqa: E501
    """Obtain the CURIE and type of some entity by name

     # noqa: E501

    :param search_string: Some string to search by (name, abbreviation, CURIE, etc.)
    :type search_string: str

    :rtype: List[object]
    """
    kGNodeIndex = KGNodeIndex()
    return kGNodeIndex.get_curies_and_types_and_names(search_string, kg_name='KG1')

