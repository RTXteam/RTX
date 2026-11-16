# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing_extensions import Annotated
from openapi_server.models.async_query import AsyncQuery
from openapi_server.models.async_query_response import AsyncQueryResponse


class BaseAsyncqueryApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAsyncqueryApi.subclasses = BaseAsyncqueryApi.subclasses + (cls,)
    async def asyncquery_post(
        self,
        async_query: Annotated[AsyncQuery, Field(description="Query information to be submitted")],
    ) -> AsyncQueryResponse:
        """"""
        ...
