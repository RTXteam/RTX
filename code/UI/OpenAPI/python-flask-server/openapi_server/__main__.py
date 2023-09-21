#!/usr/bin/env python3

import connexion
import flask_cors
import logging
import json
import openapi_server.encoder
import os
import sys
import signal
import atexit
import traceback
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

sys.path.append(os.path.dirname(os.path.abspath(__file__)) +
                "/../../../../ARAX/ARAXQuery")

from ARAX_background_tasker import ARAXBackgroundTasker
from ARAX_database_manager import ARAXDatabaseManager

sys.path.append(os.path.dirname(os.path.abspath(__file__)) +
                "/../../../..")
from RTXConfiguration import RTXConfiguration

# can change this to logging.DEBUG for debuggging
logging.basicConfig(level=logging.INFO)

child_pid = None


@atexit.register
def ignore_sigchld():
    logging.debug("Setting SIGCHLD to SIG_IGN before exiting")
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    if child_pid is not None:
        os.kill(child_pid, signal.SIGKKILL)


def receive_sigchld(signal_number, frame):
    if signal_number == signal.SIGCHLD:
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                logging.debug(f"PID returned from call to os.waitpid: {pid}")
                if pid == 0:
                    break
            except ChildProcessError as e:
                logging.debug(repr(e) +
                              "; this is expected if there are "
                              "no more child processes to reap")
                break


def receive_sigpipe(signal_number, frame):
    if signal_number == signal.SIGPIPE:
        logging.error("pipe error")


def main():
    app = connexion.App(__name__, specification_dir='./openapi/')
    app.app.json_encoder = openapi_server.encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'ARAX Translator Reasoner'},
                pythonic_params=True)
    flask_cors.CORS(app.app)
    signal.signal(signal.SIGCHLD, receive_sigchld)
    signal.signal(signal.SIGPIPE, receive_sigpipe)

    # Read any load configuration details for this instance
    try:
        with open('openapi_server/flask_config.json') as infile:
            local_config = json.load(infile)
    except Exception:
        local_config = {"port": 5000}

    RTXConfiguration()

    dbmanager = ARAXDatabaseManager()
    try:
        logging.info("Checking for complete databases")
        if dbmanager.check_versions():
            logging.warning("Databases incomplete; running update_databases")
            dbmanager.update_databases()
        else:
            logging.info("Databases seem to be complete")
    except Exception as e:
        logging.error(traceback.format_exc())
        raise e
    del dbmanager

    pid = os.fork()
    if pid == 0:  # I am the child process
        sys.stdout = open('/dev/null', 'w')
        sys.stdin = open('/dev/null', 'r')

        logging.info("Starting background tasker in a child process")
        ARAXBackgroundTasker().run_tasks(local_config)
    elif pid > 0:  # I am the parent process
        # Start the service
        logging.info(f"Background tasker is running in child process {pid}")
        global child_pid
        child_pid = pid
        logging.info("Starting flask application in the parent process")
        app.run(port=local_config['port'], threaded=True)
    else:
        logging.error("[__main__]: fork() unsuccessful")
        assert False, "****** fork() unsuccessful in __main__"


if __name__ == '__main__':
    main()
