# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.translate_api_base import BaseTranslateApi
import openapi_server.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from openapi_server.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field
from typing import Any, List
from typing_extensions import Annotated
from openapi_server.models.query import Query
from openapi_server.models.question import Question


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/translate",
    responses={
        200: {"model": List[Query], "description": "successful operation"},
        400: {"description": "Invalid status value"},
    },
    tags=["translate"],
    summary="Translate natural language question into a standardized query",
    response_model_by_alias=True,
)
async def translate(
    question: Annotated[Question, Field(description="Question information to be translated")] = Body(..., description="Question information to be translated")
,
) -> List[Query]:
    if not BaseTranslateApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTranslateApi.subclasses[0]().translate(question)
