# coding: utf-8

import os

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictInt, StrictStr
from typing import Any, Dict, Optional
from typing_extensions import Annotated

from openapi_server.apis.status_api_base import BaseStatusApi

from ARAX_query_tracker import ARAXQueryTracker
from Expand.smartapi import SmartAPI
from Expand.trapi_query_cacher import KPQueryCacher
from recent_uuid_manager import RecentUUIDManager
from RTXConfiguration import RTXConfiguration

class ImplStatusApi(BaseStatusApi):

    def __init__(cls, **kwargs):
        pass

    async def get_status(
        self,
        last_n_hours: Annotated[Optional[int], Field(description="Limit results to the past N hours")],
        id: Annotated[Optional[int], Field(description="Identifier of the log entry")],
        terminate_pid: Annotated[Optional[int], Field(description="PID of an ongoing query to terminate")],
        authorization: Annotated[Optional[StrictStr], Field(description="Authorization string required for certain calls to status")],
        mode: Annotated[Optional[StrictStr], Field(description="Switch to control the type of returned status information Possible values are: activity: Show query activity on server [default] smartapi: Summarize Translator endpoints at SmartAPI")],
    ) -> object:

        if mode is not None:
            if mode == 'kp_cache':
                cacher = KPQueryCacher()
                return cacher.list_cached_queries()

            if mode == 'recent_pks':
                manager = RecentUUIDManager()
                return manager.get_recent_uuids( ars_host=authorization, top_n_pks=last_n_hours )

            if mode == 'site_config':
                config = RTXConfiguration()
                return config.get_config_settings()

            if mode == 'system_load':
                query_tracker = ARAXQueryTracker()
                location = query_tracker.get_code_location()
                load_data = []
                with open(os.path.join(location, "ARAX_background_tasker_loadlog.txt"), "r") as infile:
                    for line in infile:
                        line = line.strip()
                        if line == "":
                            continue
                        parts = line.split("\t")
                        if len(parts) != 7:
                            continue
                        load_data.append({
                            "timestamp": parts[0],
                            "n_ongoing_queries": int(parts[1]),
                            "cpu_percent": float(parts[2]),
                            "available_gb": float(parts[3]),
                            "total_gb": float(parts[4]),
                            "n_cpus": int(parts[5]),
                            "n_child_processes": int(parts[6])
                        })
                return load_data


        if authorization is not None and authorization == 'smartapi':
            smartapi = SmartAPI()
            return smartapi.get_trapi_endpoints()

        query_tracker = ARAXQueryTracker()
        if terminate_pid is not None:
            status = query_tracker.terminate_job(terminate_pid, authorization)
        else:
            status = query_tracker.get_status(last_n_hours=last_n_hours, mode=mode, id_=id)
        return status




    async def get_logs(
        self,
        mode: Annotated[Optional[StrictStr], Field(description="Specify the log sending mode")],
    ) -> str:

        query_tracker = ARAXQueryTracker()
        status = query_tracker.get_logs(mode=mode)
        return status

