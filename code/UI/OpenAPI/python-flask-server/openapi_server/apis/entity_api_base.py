# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Dict, List
from typing_extensions import Annotated
from openapi_server.models.entity_query import EntityQuery


class BaseEntityApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseEntityApi.subclasses = BaseEntityApi.subclasses + (cls,)
    async def get_entity(
        self,
        q: Annotated[List[StrictStr], Field(description="A string to search by (name, abbreviation, CURIE, etc.). The parameter may be repeated for multiple search strings.")],
    ) -> object:
        ...


    async def post_entity(
        self,
        body: Annotated[Dict[str, Any], Field(description="List of terms to get information about")],
    ) -> EntityQuery:
        ...
