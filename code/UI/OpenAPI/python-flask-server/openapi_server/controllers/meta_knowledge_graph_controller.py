import connexion
import six
import os
import sys

from openapi_server.models.meta_knowledge_graph import MetaKnowledgeGraph  # noqa: E501
from openapi_server import util

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/KnowledgeSources")
from knowledge_source_metadata import KnowledgeSourceMetadata


def meta_knowledge_graph(format=None):  # noqa: E501
    """Meta knowledge graph representation of this TRAPI web service.

     # noqa: E501

    :param format: Provide meta_knowledge_graph information in a format other than the default. Default value is &#39;full&#39;. Also permitted is &#39;simple&#39;
    :type format: str

    :rtype: MetaKnowledgeGraph
    """
    ksm = KnowledgeSourceMetadata()
    return(ksm.get_meta_knowledge_graph(format=format))
