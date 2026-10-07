# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.response_api_base import BaseResponseApi
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
from pydantic import Field, StrictStr
from typing import Any, Dict
from typing_extensions import Annotated

from openapi_server.models.response import Response


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/response",
    responses={
        200: {"model": object, "description": "successful operation"},
        400: {"description": "Invalid request"},
    },
    tags=["response"],
    summary="Annotate a response",
    response_model_by_alias=True,
)
async def post_response(
    body: Annotated[Dict[str, Any], Field(description="Object that provides annotation information")] = Body(..., description="Object that provides annotation information")
,
) -> object:
    if not BaseResponseApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResponseApi.subclasses[0]().post_response(body)


@router.get(
    "/response/{response_id}",
    responses={
        200: {"model": dict, "description": "successful operation"},
        404: {"description": "response_id not found"},
    },
    tags=["response"],
    summary="Request a previously stored response from the server",
    response_model_by_alias=True,
    response_model=None,
    )

async def get_response(
    response_id: Annotated[StrictStr, Field(description="Identifier of the response to return")] = Path(..., description="Identifier of the response to return")
,
) -> Response:
    if not BaseResponseApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResponseApi.subclasses[0]().get_response(response_id)
