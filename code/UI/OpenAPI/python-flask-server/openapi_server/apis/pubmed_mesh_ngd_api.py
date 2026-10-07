# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.pubmed_mesh_ngd_api_base import BasePubmedMeshNgdApi
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
from typing import Any
from typing_extensions import Annotated
from openapi_server.models.mesh_ngd_response import MeshNgdResponse


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/PubmedMeshNgd/{term1}/{term2}",
    responses={
        200: {"model": MeshNgdResponse, "description": "successful operation"},
        400: {"description": "Invalid terms"},
    },
    tags=["PubmedMeshNgd"],
    summary="Query to get the Normalized Google Distance between two MeSH terms based on co-occurrence in all PubMed article annotations",
    response_model_by_alias=True,
)
async def pubmed_mesh_ngd(
    term1: Annotated[StrictStr, Field(description="First of two terms. Order not important.")] = Path(..., description="First of two terms. Order not important.")
,
    term2: Annotated[StrictStr, Field(description="Second of two terms. Order not important.")] = Path(..., description="Second of two terms. Order not important.")
,
) -> MeshNgdResponse:
    if not BasePubmedMeshNgdApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePubmedMeshNgdApi.subclasses[0]().pubmed_mesh_ngd(term1, term2)
