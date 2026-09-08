import six
import os
import sys

from openapi_server import util
from ARAX_query_tracker import ARAXQueryTracker
from Expand.smartapi import SmartAPI
from Expand.trapi_query_cacher import KPQueryCacher
from recent_uuid_manager import RecentUUIDManager
from RTXConfiguration import RTXConfiguration


def get_status(last_n_hours=None, id_=None, terminate_pid=None, authorization=None, mode=None):  # noqa: E501
    """Obtain status information about the endpoint

     # noqa: E501

    :param last_n_hours: Limit results to the past N hours
    :type last_n_hours: int
    :param id: Identifier of the log entry
    :type id: int
    :param terminate_pid: PID of an ongoing query to terminate
    :type terminate_pid: int
    :param authorization: Authorization string required for certain calls to status
    :type authorization: str
    :param mode: Switch to control the type of returned status information Possible values are: activity: Show query activity on server [default] smartapi: Summarize Translator endpoints at SmartAPI
    :type mode: str

    :rtype: object
    """

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
        status = query_tracker.get_status(last_n_hours=last_n_hours, mode=mode, id_=id_)
    return status


def get_logs(mode=None):  # noqa: E501
    """Get log information from the server

     # noqa: E501

    :param mode: Specify the log sending mode
    :type mode: string

    :rtype: string
    """

    query_tracker = ARAXQueryTracker()
    status = query_tracker.get_logs(mode=mode)
    return status
