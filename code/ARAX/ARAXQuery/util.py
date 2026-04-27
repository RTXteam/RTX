import heapq
import os
import sys
from typing import Iterable

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.edge import Edge


def summarize_set_elements(x: Iterable[str],
                           max_elem: int = 10) -> str:
    """
    Return a comma-delimited representation of the first max_elem elements of Iterable[str].

    - If the iterable has fewer than max_elem + 1 elements, return all elements.
    - Otherwise return the first max_elem elements in lexicographic order followed by an ellipsis.
    """
    sorted_x = heapq.nsmallest(max_elem + 1, x)
    if len(sorted_x) <= max_elem:
        return "[" + ", ".join(sorted_x) + "]"
    return "[" + ", ".join(sorted_x[:max_elem]) + ", ... ]"


def get_arax_edge_key(edge: Edge) -> str:
    """
    Build the canonical ARAX edge key for a TRAPI Edge.

    The key must stay byte-identical to the value written into the
    `arax_edge_key` column of the tier0-info-for-overlay sqlite by
    KnowledgeSources/generate_sqlite.py, otherwise lookups will miss.
    """
    qualifiers_dict = (
        {q.qualifier_type_id: q.qualifier_value for q in edge.qualifiers}
        if edge.qualifiers else {}
    )
    qualified_predicate = qualifiers_dict.get("biolink:qualified_predicate", "")
    object_direction_qualifier = qualifiers_dict.get("biolink:object_direction_qualifier", "")
    object_aspect_qualifier = qualifiers_dict.get("biolink:object_aspect_qualifier", "")

    primary_ks_sources = (
        [s.resource_id for s in edge.sources if s.resource_role == "primary_knowledge_source"]
        if edge.sources else []
    )
    primary_knowledge_source = primary_ks_sources[0] if primary_ks_sources else ""

    qualified_portion = f"{qualified_predicate}--{object_direction_qualifier}--{object_aspect_qualifier}"
    return f"{edge.subject}--{edge.predicate}--{qualified_portion}--{edge.object}--{primary_knowledge_source}"

