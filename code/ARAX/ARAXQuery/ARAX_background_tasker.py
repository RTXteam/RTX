#!/usr/bin/env python3

import sys
import os
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)
import time
import psutil
import subprocess
import datetime
import traceback
import pkgutil
from importlib.metadata import version

from ARAX_query_tracker import ARAXQueryTracker

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/Expand")
from kp_info_cacher import KPInfoCacher


class ARAXBackgroundTasker:


    def __init__(self):
        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker created")


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


        #### Check in on the NodeSynonymizer database, which sometimes gets corrupted
        node_synonymizer_path = os.path.dirname(os.path.abspath(__file__)) + "/../NodeSynonymizer"
        files = os.listdir(node_synonymizer_path)
        already_printed_header = False
        link_counter = 0
        file_counter = 0
        for file in files:
            if file.startswith('node_syn') and file.endswith('.sqlite'):
                file_counter += 1
                filepath = node_synonymizer_path + "/" + file
                fileinfo = '??'
                if os.path.islink(filepath):
                    fileinfo = '(symlink)'
                    link_counter += 1
                else:
                    fileinfo = os.path.getsize(filepath)
                if file_counter != 1 or link_counter != 1:
                    if not already_printed_header:
                        eprint("Strange files in NodeSynonymizer directory:")
                        already_printed_header = True
                    eprint(f"    {fileinfo}   {file}")
                    eprint(f"    Deleting file {filepath}")
                    try:
                        os.unlink(filepath)
                    except Exception as error:
                        eprint(f"ERROR: Unable to delete file with error {error}")

        if file_counter != 1 or link_counter != 1:
            eprint("ERROR: NodeSynonymizer state is weird. "
                   f"file_counter: {file_counter} "
                   f"link_counter: {link_counter} "
                   "Recommend running the database_manager and restarting")
            # try:
            #     subprocess.check_call( [ 'python3', node_synonymizer_path + "/../ARAXQuery/ARAX_database_manager.py" ] )
            # except Exception as error:
            #     eprint(f"ERROR: Attempt to run database manager failed with {error}")


        #### Check in on the databases directory
        node_synonymizer_path = os.path.dirname(os.path.abspath(__file__)) + "/../NodeSynonymizer"
        files = os.listdir(node_synonymizer_path)
        eprint("INFO: Current contents of the databases area:")

        for file in files:
            if file.startswith('node_syn') and file.endswith('.sqlite'):
                filepath = node_synonymizer_path + "/" + file
                eprint(f"  {filepath}")
                if os.path.islink(filepath):
                    resolved_path = os.path.dirname(os.readlink(filepath))
                    eprint(f"  {resolved_path}")
                    result = subprocess.run(['ls', '-l', resolved_path], stdout=subprocess.PIPE)
                    eprint(result.stdout.decode('utf-8'))
        eprint("INFO: End listing databases area contents")



        #### Loop forever doing various things
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
            # if 'threading_lock' in config and config['threading_lock'] is not None:
            #     with config['threading_lock']:
            #         ongoing_queries_by_remote_address = query_tracker.check_ongoing_queries()
            # else:
            ongoing_queries_by_remote_address = query_tracker.check_ongoing_queries()
            n_ongoing_queries = 0
            n_clients = 0
            for client, n_queries in ongoing_queries_by_remote_address.items():
                n_clients += 1
                n_ongoing_queries += n_queries

            load_tuple = psutil.getloadavg()

            timestamp = str(datetime.datetime.now().isoformat())
            eprint(f"{timestamp}: INFO: ARAXBackgroundTasker status: waiting. Current load is {load_tuple}, n_clients={n_clients}, n_ongoing_queries={n_ongoing_queries}")
            time.sleep(60)



##################################################################################################
def main():

    background_tasker = ARAXBackgroundTasker()

    config = {}
    background_tasker.run_tasks( config )


if __name__ == "__main__":
    main()
