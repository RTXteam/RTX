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

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../KnowledgeSources")
from meta_kg_background_refresh import refresh_meta_kg

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


def log_error(message: str):
    """Log an ERROR line with the current traceback, so tasker failures are easy to find (#2908)."""
    timestamp = str(datetime.datetime.now().isoformat())
    eprint(f"{timestamp}: ERROR: ARAXBackgroundTasker: {message}")
    eprint(traceback.format_exc())

FREQ_KP_INFO_CACHER_SEC = 3600
FREQ_META_KG_REFRESH_SEC = 3600  # 1 hour
FREQ_CHECK_ONGOING_SEC = 60
DUMP_PACKAGE_VERSIONS_ON_START = False

class ARAXBackgroundTasker:

    def __init__(self, parent_pid: int,
                 run_kp_info_cacher: bool = True,
                 run_meta_kg_refresh: bool = True,
                 first_start: bool = True):
        self.run_kp_info_cacher = run_kp_info_cacher
        self.run_meta_kg_refresh = run_meta_kg_refresh
        self.parent_pid = parent_pid
        # False when the tasker is restarted after a crash (#2908); then the
        # server may be running queries, so skip the one-time startup cleanup
        self.first_start = first_start
        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker created")


    def _create_query_tracker(self):
        """The query tracker (MySQL), or None if it can't be set up right now (#2908)."""
        try:
            return ARAXQueryTracker()
        except Exception:
            log_error("could not set up the query tracker (MySQL); will try again on the next pass")
            return None


    def _create_kp_query_cacher(self, mode):
        """The KP query cache, or None if it can't be set up right now (#2908)."""
        try:
            return KPQueryCacher(mode=mode)
        except Exception:
            log_error("could not set up the KP query cache; will try again on the next pass")
            return None


    def run_tasks(self):

        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: ARAXBackgroundTasker starting")

        # Set up the query tracker. It and the KP query cache are not needed to
        # refresh the KP info caches, so if one of them can't be set up (for
        # example MySQL is down), keep going and try again on the next pass (#2908)
        query_tracker = self._create_query_tracker()

        if self.run_kp_info_cacher:
            kp_info_cacher = KPInfoCacher()
            kp_info_cacher_counter = 0

        if self.run_meta_kg_refresh:
            meta_kg_refresh_counter = 0

        load_file_path = os.path.dirname(os.path.abspath(__file__))+"/ARAX_background_tasker_loadlog.txt"

        # Clear the table of existing queries, only when the application starts
        if self.first_start and query_tracker is not None:
            eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: Clearing any "
                   "potential stale queries in ongoing query table")
            try:
                query_tracker.clear_ongoing_queries()
            except Exception:
                log_error("clear_ongoing_queries() failed")

        # Print out our package versions on start for troubleshooting
        if DUMP_PACKAGE_VERSIONS_ON_START:
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

        #### Set up the KP Cacher to be used for periodic refreshing.
        #### mode='BackgroundTasker' clears the KP query cache, so only on the first start
        kp_cacher = self._create_kp_query_cacher(mode='BackgroundTasker' if self.first_start else None)

        # Loop forever performing various background tasks
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
                        e_type, e_value, e_traceback = sys.exc_info()
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

                try:
                    lines = []
                    with open(load_file_path) as outfile:
                        for line in outfile:
                            lines.append(line.strip())
                    if len(lines) > 60 * 24:
                        with open(load_file_path, "w") as outfile:
                            iline = len(lines) - 60 * 24
                            while iline < len(lines):
                                print(lines[iline], file=outfile)
                                iline += 1
                except Exception as error:
                    eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: "
                        f"Failed to trim {load_file_path}: "
                        f"{error}")

            # Check on the ongoing queries table to see how many we have
            if query_tracker is None:
                query_tracker = self._create_query_tracker()
            ongoing_queries_by_addr = {}
            if query_tracker is not None:
                try:
                    ongoing_queries_by_addr = query_tracker.check_ongoing_queries() or {}
                except Exception as error:
                    eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: failed check_ongoing_queries with error {error}")
            n_ongoing_queries = 0
            n_clients = 0
            for client, n_queries in ongoing_queries_by_addr.items():
                n_clients += 1
                n_ongoing_queries += n_queries

            #### Refresh the KP cache (never clear it here: the server is running)
            if kp_cacher is None:
                kp_cacher = self._create_kp_query_cacher(mode=None)
            start_time = time.time()
            if kp_cacher is not None:
                try:
                    kp_cacher.refresh_cache()
                except Exception as error:
                    eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: failed to_refresh_cache with error {error}")
            elapsed_time = time.time() - start_time
            if elapsed_time < FREQ_CHECK_ONGOING_SEC - 1:
                time_to_sleep = FREQ_CHECK_ONGOING_SEC - round(elapsed_time)
            else:
                time_to_sleep = 2

            # Collect current system load information. Defaults first, so a
            # failure here can't leave the names below unset or a minute old
            load_tuple = cpu_percent = cpu_count = available_gb = total_gb = None
            matching_processes = []
            try:
                load_tuple = psutil.getloadavg()
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                system_memory = psutil.virtual_memory()
                available_gb = round(system_memory.available / (1024 ** 3),1)
                total_gb = system_memory.total / (1024 ** 3)
                timestamp = str(datetime.datetime.now().isoformat())

                matching_processes = []
                for proc in psutil.process_iter(attrs=['cmdline']):
                    if proc.info['cmdline'] is not None:
                        for arg in proc.info['cmdline']:
                            if 'child' in arg:
                                matching_processes.append(proc)
            except Exception as error:
                eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: failed get system load information with error {error}")

            try:
                eprint(f"{timestamp}: INFO: ARAXBackgroundTasker "
                    f"(PID {my_pid}) status: waiting. Current "
                    f"load is {load_tuple}, n_clients={n_clients}, "
                    f"n_ongoing_queries={n_ongoing_queries}")
                with open(load_file_path, "a") as outfile:
                    print(f"{timestamp}\t{n_ongoing_queries}\t{cpu_percent}\t"
                          f"{available_gb}\t{total_gb}\t{cpu_count}\t{len(matching_processes)}", file=outfile)
            except Exception as error:
                eprint(f"{timestamp}: INFO: ARAXBackgroundTasker: "
                       f"Failed to write info to {load_file_path}: "
                       f"{error}")

            time.sleep(time_to_sleep)


def main():
    background_tasker = ARAXBackgroundTasker(os.getpid(), run_kp_info_cacher=True, run_meta_kg_refresh=True)
    background_tasker.run_tasks()


if __name__ == "__main__":
    main()
