# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.status_api_base import BaseStatusApi
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
from pydantic import Field, StrictInt, StrictStr
from typing import Any, Dict, Optional
from typing_extensions import Annotated


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/status",
    responses={
        200: {"model": object, "description": "successful operation"},
        404: {"description": "Entity not found"},
    },
    tags=["status"],
    summary="Obtain status information about the endpoint",
    response_model_by_alias=True,
)
async def get_status(
    last_n_hours: Annotated[Optional[int], Field(description="Limit results to the past N hours")] = Query(None, description="Limit results to the past N hours", alias="last_n_hours")
,
    id: Annotated[Optional[int], Field(description="Identifier of the log entry")] = Query(None, description="Identifier of the log entry", alias="id")
,
    terminate_pid: Annotated[Optional[int], Field(description="PID of an ongoing query to terminate")] = Query(None, description="PID of an ongoing query to terminate", alias="terminate_pid")
,
    authorization: Annotated[Optional[StrictStr], Field(description="Authorization string required for certain calls to status")] = Query(None, description="Authorization string required for certain calls to status", alias="authorization")
,
    mode: Annotated[Optional[StrictStr], Field(description="Switch to control the type of returned status information Possible values are: activity: Show query activity on server [default] smartapi: Summarize Translator endpoints at SmartAPI")] = Query(None, description="Switch to control the type of returned status information Possible values are: activity: Show query activity on server [default] smartapi: Summarize Translator endpoints at SmartAPI", alias="mode")
,
) -> object:
    if not BaseStatusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseStatusApi.subclasses[0]().get_status(last_n_hours, id, terminate_pid, authorization, mode)


@router.get(
    "/status/logs",
    responses={
        200: {"model": str, "description": "successful operation"},
        404: {"description": "Logs not found"},
    },
    tags=["status"],
    summary="Get log information from the server",
    response_model_by_alias=True,
)
async def get_logs(
    mode: Annotated[Optional[StrictStr], Field(description="Specify the log sending mode")] = Query(None, description="Specify the log sending mode", alias="mode")
,
) -> str:
    if not BaseStatusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseStatusApi.subclasses[0]().get_logs(mode)
