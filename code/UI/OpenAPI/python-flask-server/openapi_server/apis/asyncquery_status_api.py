# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.asyncquery_status_api_base import BaseAsyncqueryStatusApi
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
from openapi_server.models.async_query_status_response import AsyncQueryStatusResponse


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/asyncquery_status/{job_id}",
    responses={
        200: {"model": AsyncQueryStatusResponse, "description": "Returns the status and current logs of a previously submitted asyncquery."},
        404: {"description": "job_id not found"},
        501: {"model": str, "description": "Return code 501 indicates that this endpoint has not been implemented at this site. Sites that implement /asyncquery MUST implement /asyncquery_status/{job_id}, but those that do not implement /asyncquery SHOULD NOT implement /asyncquery_status."},
    },
    tags=["asyncquery_status"],
    summary="Retrieve the current status of a previously submitted asyncquery given its job_id",
    response_model_by_alias=True,
)
async def asyncquery_status(
    job_id: Annotated[StrictStr, Field(description="Identifier of the job for status request")] = Path(..., description="Identifier of the job for status request")
,
) -> AsyncQueryStatusResponse:
    if not BaseAsyncqueryStatusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAsyncqueryStatusApi.subclasses[0]().asyncquery_status(job_id)
