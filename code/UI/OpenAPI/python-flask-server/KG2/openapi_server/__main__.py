#!/usr/bin/env python3

import connexion, flask, flask_cors
import logging
import json
import openapi_server.encoder
import os, sys, signal, atexit
import threading
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/ARAXQuery")
from ARAX_background_tasker import ARAXBackgroundTasker

logging.basicConfig(level=logging.INFO)  # can change this to logging.DEBUG for debuggging

@atexit.register
def ignore_sigchld():
    logging.debug("Setting SIGCHLD to SIG_IGN before exiting")
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    
def receive_sigchld(signal_number, frame):
    if signal_number == signal.SIGCHLD:
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                logging.debug(f"PID returned from call to os.waitpid: {pid}")
                if pid == 0:
                    break
            except ChildProcessError as e:
                logging.debug(repr(e) + "; this is expected if there are no more child processes to reap")
                break

def receive_sigpipe(signal_number, frame):
    if signal_number == signal.SIGPIPE:
        logging.error("pipe error")

def main():
    app = connexion.App(__name__, specification_dir='./openapi/')
    app.app.json_encoder = openapi_server.encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'RTX KG2 Translator KP'},
                pythonic_params=True)
    flask_cors.CORS(app.app)
    signal.signal(signal.SIGCHLD, receive_sigchld)
    signal.signal(signal.SIGPIPE, receive_sigpipe)

    #### Read any load configuration details for this instance
    try:
        with open('openapi_server/flask_config.json') as infile:
            local_config = json.load(infile)
    except:
        local_config = { "port": 5008 }

    #### Start a thread that will perform basic background tasks independently of traffic.
    #### It should never return, forever looping in the background.
    background_tasker = ARAXBackgroundTasker()
    background_task_thread = threading.Thread(target=background_tasker.run_tasks, args=(local_config,))
    threading_lock = threading.Lock()
    local_config['threading_lock'] = threading_lock
    background_task_thread.start()

    #### Start the service
    app.run(port=local_config['port'], threaded=True)


if __name__ == '__main__':
    main()

