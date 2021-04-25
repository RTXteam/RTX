import connexion
import six
import os
import sys

from openapi_server.models.meta_knowledge_graph import MetaKnowledgeGraph  # noqa: E501
from openapi_server import util

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../../ARAX/KnowledgeSources")
from knowledge_source_metadata import KnowledgeSourceMetadata


def meta_knowledge_graph():  # noqa: E501
    """Meta knowledge graph representation of this TRAPI web service.

     # noqa: E501


    :rtype: MetaKnowledgeGraph
    """
    ksm = KnowledgeSourceMetadata()
    return(ksm.get_meta_knowledge_graph())
