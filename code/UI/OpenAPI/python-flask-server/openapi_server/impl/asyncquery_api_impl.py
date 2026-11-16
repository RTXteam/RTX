# coding: utf-8

"""
Implementation of the TRAPI /asyncquery endpoint.

ARAXQuery already knows how to answer asynchronously: in 'asynchronous' mode it
validates the query, forks, and the parent returns straight away while the
child finishes the query, POSTs the Response to the callback URL and exits.
This class just hands the query to that code and turns what the parent returns
into a TRAPI 2.0 AsyncQueryResponse carrying the job_id.
"""

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from fastapi.responses import JSONResponse
from pydantic import Field
from starlette.concurrency import run_in_threadpool
from typing_extensions import Annotated

from openapi_server.apis.asyncquery_api_base import BaseAsyncqueryApi
from openapi_server.models.async_query import AsyncQuery
from openapi_server.models.async_query_response import AsyncQueryResponse
from openapi_server.request_context import get_remote_address

import ARAX_query  # pylint: disable=import-error,wrong-import-position


class ImplAsyncqueryApi(BaseAsyncqueryApi):

    async def asyncquery_post(
        self,
        async_query: Annotated[AsyncQuery, Field(description="Query information to be submitted")],
    ) -> AsyncQueryResponse:
        """Accept a query for asynchronous processing; the Response is sent to the callback when done"""

        query = dict(async_query)

        #### Record the remote IP address in the query for now so it is available downstream
        query['remote_address'] = get_remote_address()

        # ARAX forks inside query_return_message, so run it off the event loop (as /query does);
        # the forked child finishes the query and calls os._exit(), so only the parent returns here
        araxq = ARAX_query.ARAXQuery()
        envelope = await run_in_threadpool(araxq.query_return_message, query, 'asynchronous')

        job_id = getattr(araxq.response, 'job_id', None)
        http_status = getattr(envelope, '_http_status', 200)
        async_response = AsyncQueryResponse(status=envelope.status,
                                            description=envelope.description,
                                            job_id=str(job_id) if job_id is not None else "")
        return JSONResponse(content=async_response.to_dict(), status_code=http_status)
