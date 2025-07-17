#!/usr/bin/env python3

import sys
import os
import time
import psutil
import subprocess
import datetime
import traceback
import pkgutil
from importlib.metadata import version

from ARAX_query_tracker import ARAXQueryTracker

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/Expand")
from kp_info_cacher import KPInfoCacher

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

FREQ_KP_INFO_CACHER_SEC = 3600
FREQ_CHECK_ONGOING_SEC = 60


class ARAXBackgroundTasker:

    def __init__(self, parent_pid: int,
                 run_kp_info_cacher: bool = True):
        self.run_kp_info_cacher = run_kp_info_cacher
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

        # Check in on the NodeSynonymizer database, which sometimes gets
        # corrupted
        node_synonymizer_path = os.path.dirname(os.path.abspath(__file__)) + \
            "/../NodeSynonymizer"
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
                    rtxc = RTXConfiguration()
                    eprint(f"rtxc.domain: {rtxc.domain}")
                    # if we are running in ITRB ARAX, delete the file to try to heal ARAX:
                    if rtxc.domain.endswith(".transltr.io"):
                        eprint(f"    Deleting file {filepath}")
                        try:
                            os.unlink(filepath)
                        except Exception as error:
                            eprint("ERROR: Unable to delete file with error "
                                   f"{error}")
                            
        if file_counter != 1 or link_counter != 1:
            eprint("ERROR: NodeSynonymizer state is weird. "
                   f"file_counter: {file_counter} "
                   f"link_counter: {link_counter} "
                   "Recommend restarting, which will rerun the database "
                   "manager")

        # Check in on the databases directory
        node_synonymizer_path = os.path.dirname(os.path.abspath(__file__)) + \
            "/../NodeSynonymizer"
        files = os.listdir(node_synonymizer_path)
        eprint("INFO: Current contents of the databases area:")
        for file in files:
            if file.startswith('node_syn') and file.endswith('.sqlite'):
                filepath = node_synonymizer_path + "/" + file
                eprint(f"  {filepath}")
                if os.path.islink(filepath):
                    resolved_path = os.path.dirname(os.readlink(filepath))
                    eprint(f"  {resolved_path}")
                    result = subprocess.run(['ls', '-l', resolved_path],
                                            stdout=subprocess.PIPE)
                    eprint(result.stdout.decode('utf-8'))
        eprint("INFO: End listing databases area contents")

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

            ongoing_queries_by_addr = query_tracker.check_ongoing_queries()
            n_ongoing_queries = 0
            n_clients = 0
            for client, n_queries in ongoing_queries_by_addr.items():
                n_clients += 1
                n_ongoing_queries += n_queries

            load_tuple = psutil.getloadavg()

            timestamp = str(datetime.datetime.now().isoformat())
            eprint(f"{timestamp}: INFO: ARAXBackgroundTasker "
                   f"(PID {my_pid}) status: waiting. Current "
                   f"load is {load_tuple}, n_clients={n_clients}, "
                   f"n_ongoing_queries={n_ongoing_queries}")
            time.sleep(FREQ_CHECK_ONGOING_SEC)


def main():
    background_tasker = ARAXBackgroundTasker(os.getpid())
    background_tasker.run_tasks()


if __name__ == "__main__":
    main()
