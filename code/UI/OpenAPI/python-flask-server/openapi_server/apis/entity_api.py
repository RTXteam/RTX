# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.entity_api_base import BaseEntityApi
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
from typing import Any, Dict, List
from typing_extensions import Annotated
from openapi_server.models.entity_query import EntityQuery


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/entity",
    responses={
        200: {"model": object, "description": "successful operation"},
        404: {"description": "Entity not found"},
    },
    tags=["entity"],
    summary="Obtain CURIE and synonym information about a search term",
    response_model_by_alias=True,
)
async def get_entity(
    q: Annotated[List[StrictStr], Field(description="A string to search by (name, abbreviation, CURIE, etc.). The parameter may be repeated for multiple search strings.")] = Query(..., description="A string to search by (name, abbreviation, CURIE, etc.). The parameter may be repeated for multiple search strings.", alias="q")
,
) -> object:
    if not BaseEntityApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseEntityApi.subclasses[0]().get_entity(q)


@router.post(
    "/entity",
    responses={
        200: {"model": EntityQuery, "description": "successful operation"},
        404: {"description": "Entity not found"},
    },
    tags=["entity"],
    summary="Obtain CURIE and synonym information about search terms",
    response_model_by_alias=True,
)
async def post_entity(
    body: Annotated[Dict[str, Any], Field(description="List of terms to get information about")] = Body(..., description="List of terms to get information about")
,
) -> EntityQuery:
    if not BaseEntityApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseEntityApi.subclasses[0]().post_entity(body)
