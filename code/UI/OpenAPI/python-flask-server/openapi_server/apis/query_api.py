# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.query_api_base import BaseQueryApi
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
from typing_extensions import Annotated
from openapi_server.models.query import Query
from openapi_server.models.response import Response


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/query",
    responses={
        200: {"model": Response, "description": "OK. There may or may not be results. Note that some of the provided identifiers may not have been recognized."},
        400: {"model": str, "description": "Bad request. The request is invalid according to this OpenAPI schema OR a specific identifier is believed to be invalid somehow (not just unrecognized)."},
        409: {"model": str, "description": "There is a conflict between client-given TRAPI parameters and server capabilities. The response body may contain additional details about the conflict."},
        413: {"model": str, "description": "Payload too large. Indicates that batch size was over the limit specified in x-trapi."},
        429: {"model": str, "description": "Too many requests. Indicates that the client issued requests that exceed the rate limit specified in x-trapi."},
        500: {"model": str, "description": "Internal server error."},
        501: {"model": str, "description": "Not implemented."},
    },
    tags=["query"],
    summary="Initiate a query and wait to receive a Response",
    response_model_by_alias=True,
)
async def query(
    query: Annotated[Query, Field(description="Query information to be submitted")] = Body(..., description="Query information to be submitted")
,
) -> Response:
    """"""
    if not BaseQueryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseQueryApi.subclasses[0]().query(query)
