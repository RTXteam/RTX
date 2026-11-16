# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing_extensions import Annotated
from openapi_server.models.query import Query
from openapi_server.models.response import Response


class BaseQueryApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseQueryApi.subclasses = BaseQueryApi.subclasses + (cls,)
    async def query(
        self,
        query: Annotated[Query, Field(description="Query information to be submitted")],
    ) -> Response:
        """"""
        ...
