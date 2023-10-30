#!/usr/bin/env python3

import sys
import os
import traceback
import json
import setproctitle

sys.path.append(os.path.dirname(os.path.abspath(__file__)) +
                "/../../../../../ARAX/ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) +
                "/../../../../..")

from RTXConfiguration import RTXConfiguration
from ARAX_database_manager import ARAXDatabaseManager


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


FLASK_DEFAULT_TCP_PORT = 5008
child_pid = None
parent_pid = None


def main():

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
        from ARAX_background_tasker import ARAXBackgroundTasker
        sys.stdout = open('/dev/null', 'w')
        sys.stdin = open('/dev/null', 'r')
        setproctitle.setproctitle("python3 ARAX_background_tasker::run_tasks")
        eprint("Starting background tasker in a child process")
        try:
            ARAXBackgroundTasker(run_kp_info_cacher=False).run_tasks()
        except Exception as e:
            eprint("Error in ARAXBackgroundTasker.run_tasks()")
            eprint(traceback.format_exc())
            raise e
        eprint("Background tasker child process ended unexpectedly")
    elif pid > 0:  # I am the parent process
        import signal
        import atexit

        def receive_sigterm(signal_number, frame):
            if signal_number == signal.SIGTERM:
                if parent_pid == os.getpid():
                    try:
                        os.kill(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        eprint(f"child process {child_pid} is already gone; "
                               "exiting now")
                    os.exit(0)
                else:
                    # handle exit gracefully in the child process
                    os._exit(0)

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
        import connexion
        import flask_cors
        import openapi_server.encoder
        app = connexion.App(__name__, specification_dir='./openapi/')
        app.app.json_encoder = openapi_server.encoder.JSONEncoder
        app.add_api('openapi.yaml',
                    arguments={'title': 'ARAX KG2 Translator KP'},
                    pythonic_params=True)
        flask_cors.CORS(app.app)

        # Start the service
        eprint(f"Background tasker is running in child process {pid}")
        global child_pid
        child_pid = pid
        global parent_pid
        parent_pid = os.getpid()
        signal.signal(signal.SIGCHLD, receive_sigchld)
        signal.signal(signal.SIGPIPE, receive_sigpipe)
        signal.signal(signal.SIGTERM, receive_sigterm)

        # Read any load configuration details for this instance
        try:
            with open('openapi_server/flask_config.json') as infile:
                local_config = json.load(infile)
        except Exception:
            local_config = {"port": FLASK_DEFAULT_TCP_PORT}

        eprint("Starting flask application in the parent process")
        setproctitle.setproctitle(setproctitle.getproctitle() +
                                  f" [port={local_config['port']}]")
        app.run(port=local_config['port'], threaded=True)
    else:
        eprint("[__main__]: fork() unsuccessful")
        assert False, "****** fork() unsuccessful in __main__"


if __name__ == '__main__':
    main()
