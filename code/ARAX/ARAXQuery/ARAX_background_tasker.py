#!/usr/bin/env python3

import sys
import os
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)
import time
import psutil
import datetime
import traceback
import pkgutil
from importlib.metadata import version

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration
from ARAX_query_tracker import ARAXQueryTracker

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/Expand")
from kp_info_cacher import KPInfoCacher


class ARAXBackgroundTasker:


    def __init__(self):
        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker created")
        self.rtxConfig = RTXConfiguration()


    def run_tasks(self, config):

        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker starting")

        #### Set up the query tracker
        query_tracker = ARAXQueryTracker()
        kp_info_cacher = KPInfoCacher()
        kp_info_cacher_counter = 0

        #### Clear the table of existing queries
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: Clearing any potential stale queries in ongoing query table")
        query_tracker.clear_ongoing_queries()

        #### Print out our packages for debugging
        if True:
            eprint("Installed packages:")
            for location, modname, flag in pkgutil.iter_modules():
                location = f"{location}"
                if 'RTX' not in location:
                    try:
                        version_str = version(modname)
                        eprint(f"    {modname} {version_str}")
                    except:
                        eprint(f"    {modname} ???")
                else:
                    pass
                    #eprint(f"    {modname}                  x {location}")

        while True:

            #### Run the KP Info Cacher less frequently
            timestamp = str(datetime.datetime.now().isoformat())
            if kp_info_cacher_counter == 0:
                eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: Running refresh_kp_info_caches()")
                try:
                    kp_info_cacher.refresh_kp_info_caches()
                    eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: Completed refresh_kp_info_caches()")
                except Exception as error:
                    exception_type, exception_value, exception_traceback = sys.exc_info()
                    eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: refresh_kp_info_caches() failed: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}")
            kp_info_cacher_counter += 1
            if kp_info_cacher_counter > ( 6 * 10 ):
                kp_info_cacher_counter = 0

            #### Check ongoing queries
            #eprint(f"{timestamp}: INFO: ARAXBackgroundTasker initiating query_tracker.check_ongoing_queries")
            timestamp = str(datetime.datetime.now().isoformat())
            if 'threading_lock' in config and config['threading_lock'] is not None:
                with config['threading_lock']:
                    ongoing_queries_by_remote_address = query_tracker.check_ongoing_queries()
            else:
                ongoing_queries_by_remote_address = query_tracker.check_ongoing_queries()
            n_ongoing_queries = 0
            n_clients = 0
            for client,n_queries in ongoing_queries_by_remote_address.items():
                n_clients += 1
                n_ongoing_queries += n_queries

            load_tuple = psutil.getloadavg()

            eprint(f"{timestamp}: INFO: ARAXBackgroundTasker status: waiting. Current load is {load_tuple}, n_clients={n_clients}, n_ongoing_queries={n_ongoing_queries}")
            time.sleep(10)



##################################################################################################
def main():

    background_tasker = ARAXBackgroundTasker()

    config = {}
    background_tasker.run_tasks( config )


if __name__ == "__main__":
    main()
