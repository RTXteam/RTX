#!/usr/bin/env python3

import connexion
import flask_cors
import json
import openapi_server.encoder
import os
import sys
import signal
import atexit
import traceback
import setproctitle


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

sys.path.append(os.path.dirname(os.path.abspath(__file__)) +
                "/../../../../../ARAX/ARAXQuery")

from ARAX_background_tasker import ARAXBackgroundTasker
from ARAX_database_manager import ARAXDatabaseManager

sys.path.append(os.path.dirname(os.path.abspath(__file__)) +
                "/../../../..")
from RTXConfiguration import RTXConfiguration

child_pid = None


def receive_sigterm(signal_number, frame):
    if signal_number == signal.SIGTERM:
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                eprint(f"child process {child_pid} is already gone; "
                       "exiting now")
            sys.exit(0)
        else:
            assert False, "should not ever have child_pid be None here"


@atexit.register
def ignore_sigchld():
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)


def receive_sigchld(signal_number, frame):
    if signal_number == signal.SIGCHLD:
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                eprint(f"PID returned from call to os.waitpid: {pid}")
                if pid == 0:
                    break
            except ChildProcessError as e:
                eprint(repr(e) +
                       "; this is expected if there are "
                       "no more child processes to reap")
                break


def receive_sigpipe(signal_number, frame):
    if signal_number == signal.SIGPIPE:
        eprint("pipe error")


def main():
    app = connexion.App(__name__, specification_dir='./openapi/')
    app.app.json_encoder = openapi_server.encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'RTX KG2 Translator KP'},
                pythonic_params=True)
    flask_cors.CORS(app.app)

    # Read any load configuration details for this instance
    try:
        with open('openapi_server/flask_config.json') as infile:
            local_config = json.load(infile)
    except Exception:
        local_config = {"port": 5008}

    RTXConfiguration()

    dbmanager = ARAXDatabaseManager(allow_downloads=True)
    try:
        eprint("Checking for complete databases")
        if dbmanager.check_versions():
            eprint("Databases incomplete; running update_databases")
            dbmanager.update_databases()
        else:
            eprint("Databases seem to be complete")
    except Exception as e:
        eprint(traceback.format_exc())
        raise e
    del dbmanager

    pid = os.fork()
    if pid == 0:  # I am the child process
        sys.stdout = open('/dev/null', 'w')
        sys.stdin = open('/dev/null', 'r')
        setproctitle.setproctitle("python3 ARAX_background_tasker::run_tasks")        
        eprint("Starting background tasker in a child process")
        try:
            ARAXBackgroundTasker().run_tasks(local_config)
        except Exception as e:
            eprint("Error in ARAXBackgroundTasker.run_tasks()")
            eprint(traceback.format_exc())
            raise e
        eprint("Background tasker child process ended unexpectedly")
    elif pid > 0:  # I am the parent process
        # Start the service
        eprint(f"Background tasker is running in child process {pid}")
        global child_pid
        child_pid = pid
        signal.signal(signal.SIGCHLD, receive_sigchld)
        signal.signal(signal.SIGPIPE, receive_sigpipe)
        signal.signal(signal.SIGTERM, receive_sigterm)
        eprint("Starting flask application in the parent process")
        app.run(port=local_config['port'], threaded=True)
    else:
        eprint("[__main__]: fork() unsuccessful")
        assert False, "****** fork() unsuccessful in __main__"


if __name__ == '__main__':
    main()
