# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field
from typing import Any, List
from typing_extensions import Annotated
from openapi_server.models.query import Query
from openapi_server.models.question import Question


class BaseTranslateApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseTranslateApi.subclasses = BaseTranslateApi.subclasses + (cls,)
    async def translate(
        self,
        question: Annotated[Question, Field(description="Question information to be translated")],
    ) -> List[Query]:
        ...
