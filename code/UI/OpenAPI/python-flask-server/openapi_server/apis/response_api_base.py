# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Dict
from typing_extensions import Annotated

from openapi_server.models.response import Response


class BaseResponseApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseResponseApi.subclasses = BaseResponseApi.subclasses + (cls,)
    async def post_response(
        self,
        body: Annotated[Dict[str, Any], Field(description="Object that provides annotation information")],
    ) -> object:
        ...


    async def get_response(
        self,
        response_id: Annotated[StrictStr, Field(description="Identifier of the response to return")],
    ) -> Response:
        ...
