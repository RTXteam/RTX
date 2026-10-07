# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from openapi_server.models.meta_knowledge_graph import MetaKnowledgeGraph


class BaseMetaKnowledgeGraphApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseMetaKnowledgeGraphApi.subclasses = BaseMetaKnowledgeGraphApi.subclasses + (cls,)
    async def meta_knowledge_graph(
        self,
        format: Annotated[Optional[StrictStr], Field(description="Set the format of the response")],
    ) -> MetaKnowledgeGraph:
        ...
