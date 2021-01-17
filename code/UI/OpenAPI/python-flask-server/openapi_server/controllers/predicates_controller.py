import connexion
import six
import os
import sys

from openapi_server import util

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/KnowledgeSources")
from knowledge_source_metadata import KnowledgeSourceMetadata


def predicates_get():  # noqa: E501
    """Get supported relationships by source and target

     # noqa: E501


    :rtype: Dict[str, Dict[str, List[str]]]
    """
    ksm = KnowledgeSourceMetadata()
    return(ksm.get_kg_predicates(kg_name='KG2'))

