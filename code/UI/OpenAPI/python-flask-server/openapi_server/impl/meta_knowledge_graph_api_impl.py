# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictInt, StrictStr
from typing import Any, Dict, Optional
from typing_extensions import Annotated

from openapi_server.models.meta_knowledge_graph import MetaKnowledgeGraph

from openapi_server.apis.meta_knowledge_graph_api_base import BaseMetaKnowledgeGraphApi

from knowledge_source_metadata import KnowledgeSourceMetadata


def _drop_empty_containers(value: Any) -> Any:
    """Return a copy of value with empty lists/dicts left out of every nested dict.

    TRAPI 2.0 requires optional list fields in the meta KG (e.g. MetaEdge.qualifiers,
    MetaQualifier.applicable_values) to have at least one item or be left out.
    """
    if isinstance(value, dict):
        cleaned = {key: _drop_empty_containers(item) for key, item in value.items()}
        return {key: item for key, item in cleaned.items() if item != [] and item != {}}
    if isinstance(value, list):
        return [_drop_empty_containers(item) for item in value]
    return value


class BaseMetaKnowledgeGraphApi(BaseMetaKnowledgeGraphApi):

    async def meta_knowledge_graph(
        self,
        format: Annotated[Optional[StrictStr], Field(description="Set the format of the response")],
    ) -> MetaKnowledgeGraph:

        ksm = KnowledgeSourceMetadata()
        meta_kg_dict = ksm.get_meta_knowledge_graph(format_=format)
    
        if meta_kg_dict is None:
            return None

        # Top-level 'nodes' and 'edges' are required, so only clean inside them
        cleaned = dict(meta_kg_dict)
        for key in ('nodes', 'edges'):
            if key in cleaned:
                cleaned[key] = _drop_empty_containers(cleaned[key])
        return cleaned

