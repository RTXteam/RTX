# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.example_questions_api_base import BaseExampleQuestionsApi
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
from typing import Any, Dict, List


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/exampleQuestions",
    responses={
        200: {"model": List[object], "description": "successful operation"},
    },
    tags=["exampleQuestions"],
    summary="Request a list of example questions that ARAX can answer",
    response_model_by_alias=True,
)
async def example_questions(
) -> List[object]:
    if not BaseExampleQuestionsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseExampleQuestionsApi.subclasses[0]().example_questions()
