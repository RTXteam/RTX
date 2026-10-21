# coding: utf-8

"""
Implementation of the TRAPI /asyncquery_status/{job_id} endpoint, backed by the
ARAX query tracker (the same job_id that /asyncquery returns).
"""

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import Field, StrictStr
from starlette.concurrency import run_in_threadpool
from typing_extensions import Annotated

from openapi_server.apis.asyncquery_status_api_base import BaseAsyncqueryStatusApi
from openapi_server.models.async_query_status_response import AsyncQueryStatusResponse

from ARAX_query_tracker import ARAXQueryTracker  # pylint: disable=import-error,wrong-import-position


class ImplAsyncqueryStatusApi(BaseAsyncqueryStatusApi):

    async def asyncquery_status(
        self,
        job_id: Annotated[StrictStr, Field(description="Identifier of the job for status request")],
    ) -> AsyncQueryStatusResponse:
        """Return the tracker's current status for a previously submitted /asyncquery job"""

        status_response = await run_in_threadpool(ARAXQueryTracker().get_job_status, job_id)
        if status_response is None:
            return JSONResponse(content={"detail": "Query tracker is not available"}, status_code=500)
        if status_response.status == 'UnknownJobId':
            return JSONResponse(content=jsonable_encoder(status_response.to_dict()), status_code=404)
        return JSONResponse(content=jsonable_encoder(status_response.to_dict()), status_code=200)
