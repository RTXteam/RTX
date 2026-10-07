# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.meta_knowledge_graph_api_base import BaseMetaKnowledgeGraphApi
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
from typing import Optional
from typing_extensions import Annotated
from openapi_server.models.meta_knowledge_graph import MetaKnowledgeGraph


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/meta_knowledge_graph",
    responses={
        200: {"model": dict, "description": "Returns meta knowledge graph representation of this TRAPI web service."},
    },
    tags=["meta_knowledge_graph"],
    summary="Meta knowledge graph representation of this TRAPI web service.",
    response_model=None,
    response_model_by_alias=True,
)
async def meta_knowledge_graph(
    format: Annotated[Optional[StrictStr], Field(description="Set the format of the response")] = Query(None, description="Set the format of the response", alias="format")
,
) -> MetaKnowledgeGraph:
    if not BaseMetaKnowledgeGraphApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseMetaKnowledgeGraphApi.subclasses[0]().meta_knowledge_graph(format)
