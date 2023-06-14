#!/usr/bin/env python3

import sys
import os
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)
import time
import psutil
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration
from ARAX_query_tracker import ARAXQueryTracker

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

        while True:

            timestamp = str(datetime.datetime.now().isoformat())

            #### Check ongoing queries
            #eprint(f"{timestamp}: INFO: ARAXBackgroundTasker initiating query_tracker.check_ongoing_queries")
            with config['threading_lock']:
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

    background_tasker.run_tasks()


if __name__ == "__main__":
    main()
