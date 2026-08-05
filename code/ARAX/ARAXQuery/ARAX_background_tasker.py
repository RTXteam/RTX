#!/usr/bin/env python3

import sys
import os
import time
import psutil
import datetime
import traceback
import pkgutil
from importlib.metadata import version

from ARAX_query_tracker import ARAXQueryTracker
from Expand.trapi_query_cacher import KPQueryCacher

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/Expand")
from kp_info_cacher import KPInfoCacher

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

FREQ_KP_INFO_CACHER_SEC = 3600
FREQ_META_KG_REFRESH_SEC = 3600  # 1 hour
FREQ_CHECK_ONGOING_SEC = 60


class ARAXBackgroundTasker:

    def __init__(self, parent_pid: int,
                 run_kp_info_cacher: bool = True,
                 run_meta_kg_refresh: bool = True):
        self.run_kp_info_cacher = run_kp_info_cacher
        self.run_meta_kg_refresh = run_meta_kg_refresh
        self.parent_pid = parent_pid
        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker created")

    def run_tasks(self):

        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker starting")

        # Set up the query tracker
        query_tracker = ARAXQueryTracker()

        if self.run_kp_info_cacher:
            kp_info_cacher = KPInfoCacher()
            kp_info_cacher_counter = 0

        if self.run_meta_kg_refresh:
            meta_kg_refresh_counter = 0

        # Clear the table of existing queries
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: Clearing any "
               "potential stale queries in ongoing query table")
        query_tracker.clear_ongoing_queries()

        # Print out our packages for debugging
        if False:  # set to true to print out the packages
            eprint("Installed packages:")
            for location, modname, flag in pkgutil.iter_modules():
                location = f"{location}"
                if 'RTX' not in location:
                    try:
                        version_str = version(modname)
                        eprint(f"    {modname} {version_str}")
                    except Exception:
                        eprint(f"    {modname} ???")
                else:
                    pass

        # #2585: Removed SQLite corruption check and database directory
        # listing -- NodeSynonymizer now uses SRI APIs instead of a
        # local SQLite file.

        #### Set up the KP Cacher to be used for periodic refreshing
        kp_cacher = KPQueryCacher(mode='BackgroundTasker')

        # Loop forever doing various things
        my_pid = os.getpid()
        while True:
            if not psutil.pid_exists(self.parent_pid):
                eprint("INFO: ARAXBackgroundTasker: parent process "
                       f"{self.parent_pid} has gone away; exiting")
                sys.exit(0)

            # Run the KP Info Cacher less frequently
            if self.run_kp_info_cacher:
                if kp_info_cacher_counter == 0:
                    timestamp = str(datetime.datetime.now().isoformat())
                    eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: Running "
                           "refresh_kp_info_caches()")
                    try:
                        kp_info_cacher.refresh_kp_info_caches()
                        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: "
                               "Completed refresh_kp_info_caches()")
                    except Exception as error:
                        e_type, e_value, e_traceback =\
                            sys.exc_info()
                        err_str = repr(traceback.format_exception(e_type,
                                                                  e_value,
                                                                  e_traceback))
                        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: "
                               "refresh_kp_info_caches() failed: "
                               f"{error}: {err_str}")
                kp_info_cacher_counter += 1
                if kp_info_cacher_counter * FREQ_CHECK_ONGOING_SEC > \
                   FREQ_KP_INFO_CACHER_SEC:
                    kp_info_cacher_counter = 0

            # Run the Meta KG Refresh less frequently
            if self.run_meta_kg_refresh:
                if meta_kg_refresh_counter == 0:
                    timestamp = str(datetime.datetime.now().isoformat())
                    eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: Running "
                           "meta knowledge graph refresh")
                    try:
                        # Import and run meta KG refresh using existing function
                        sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../KnowledgeSources")
                        from meta_kg_background_refresh import refresh_meta_kg
                        success = refresh_meta_kg()
                        if success:
                            eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: "
                                   "Completed meta KG refresh successfully")
                        else:
                            eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: "
                                   "meta KG refresh failed")
                    except Exception as error:
                        e_type, e_value, e_traceback =\
                            sys.exc_info()
                        err_str = repr(traceback.format_exception(e_type,
                                                                  e_value,
                                                                  e_traceback))
                        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: "
                               "meta KG refresh failed: "
                               f"{error}: {err_str}")
                meta_kg_refresh_counter += 1
                if meta_kg_refresh_counter * FREQ_CHECK_ONGOING_SEC > \
                   FREQ_META_KG_REFRESH_SEC:
                    meta_kg_refresh_counter = 0

            ongoing_queries_by_addr = query_tracker.check_ongoing_queries()
            n_ongoing_queries = 0
            n_clients = 0
            for client, n_queries in ongoing_queries_by_addr.items():
                n_clients += 1
                n_ongoing_queries += n_queries

            #### Refresh the KP cache
            start_time = time.time()
            kp_cacher.refresh_cache()
            elapsed_time = time.time() - start_time
            if elapsed_time < FREQ_CHECK_ONGOING_SEC - 1:
                time_to_sleep = FREQ_CHECK_ONGOING_SEC - round(elapsed_time)
            else:
                time_to_sleep = 2

            load_tuple = psutil.getloadavg()

            timestamp = str(datetime.datetime.now().isoformat())
            eprint(f"{timestamp}: INFO: ARAXBackgroundTasker "
                   f"(PID {my_pid}) status: waiting. Current "
                   f"load is {load_tuple}, n_clients={n_clients}, "
                   f"n_ongoing_queries={n_ongoing_queries}")
            time.sleep(time_to_sleep)


def main():
    background_tasker = ARAXBackgroundTasker(os.getpid(), run_kp_info_cacher=True, run_meta_kg_refresh=True)
    background_tasker.run_tasks()


if __name__ == "__main__":
    main()
