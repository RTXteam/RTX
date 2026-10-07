# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.asyncquery_api_base import BaseAsyncqueryApi
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
from openapi_server.models.async_query import AsyncQuery
from openapi_server.models.async_query_response import AsyncQueryResponse


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/asyncquery",
    responses={
        200: {"model": AsyncQueryResponse, "description": "The query is accepted for processing and the Response will be sent to the callback url when complete."},
        400: {"model": str, "description": "Bad request. The request is invalid according to this OpenAPI schema OR a specific identifier is believed to be invalid somehow (not just unrecognized)."},
        409: {"model": str, "description": "There is a conflict between client-given TRAPI parameters and server capabilities. The response body may contain additional details about the conflict."},
        413: {"model": str, "description": "Payload too large. Indicates that batch size was over the limit specified in x-trapi."},
        429: {"model": str, "description": "Too many requests. Indicates that the client issued requests that exceed the rate limit specified in x-trapi."},
        500: {"model": str, "description": "Internal server error."},
        501: {"model": str, "description": "Not implemented."},
    },
    tags=["asyncquery"],
    summary="Initiate a query with a callback to receive the response",
    response_model_by_alias=True,
)
async def asyncquery_post(
    async_query: Annotated[AsyncQuery, Field(description="Query information to be submitted")] = Body(..., description="Query information to be submitted")
,
) -> AsyncQueryResponse:
    """"""
    if not BaseAsyncqueryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAsyncqueryApi.subclasses[0]().asyncquery_post(async_query)
