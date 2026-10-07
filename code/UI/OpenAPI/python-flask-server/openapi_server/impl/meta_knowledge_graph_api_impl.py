# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictInt, StrictStr
from typing import Any, Dict, Optional
from typing_extensions import Annotated

from openapi_server.models.meta_knowledge_graph import MetaKnowledgeGraph

from openapi_server.apis.meta_knowledge_graph_api_base import BaseMetaKnowledgeGraphApi

from knowledge_source_metadata import KnowledgeSourceMetadata


class BaseMetaKnowledgeGraphApi(BaseMetaKnowledgeGraphApi):

    async def meta_knowledge_graph(
        self,
        format: Annotated[Optional[StrictStr], Field(description="Set the format of the response")],
    ) -> MetaKnowledgeGraph:

        ksm = KnowledgeSourceMetadata()
        meta_kg_dict = ksm.get_meta_knowledge_graph(format_=format)
    
        if meta_kg_dict is None:
            return None
    
        return meta_kg_dict

