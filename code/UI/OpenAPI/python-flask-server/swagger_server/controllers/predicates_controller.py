import connexion
import six
import os
import sys

from swagger_server import util

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../reasoningtool/QuestionAnswering")
import ReasoningUtilities as RU


def predicates():  # noqa: E501
    """Get all supported relationships in the knowledge graph, organized by source and target

     # noqa: E501


    :rtype: Dict[str, Dict[str, List[str]]]
    """
    return(RU.get_full_meta_graph())
