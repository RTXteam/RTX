# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any
from typing_extensions import Annotated
from openapi_server.models.async_query_status_response import AsyncQueryStatusResponse


class BaseAsyncqueryStatusApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAsyncqueryStatusApi.subclasses = BaseAsyncqueryStatusApi.subclasses + (cls,)
    async def asyncquery_status(
        self,
        job_id: Annotated[StrictStr, Field(description="Identifier of the job for status request")],
    ) -> AsyncQueryStatusResponse:
        ...
