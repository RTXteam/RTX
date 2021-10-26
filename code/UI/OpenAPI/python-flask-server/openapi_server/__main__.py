#!/usr/bin/env python3

import connexion
import flask
import logging
import signal
import json

from flask_cors import CORS

from openapi_server import encoder

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../ARAX/ARAXQuery")

def receive_sigchld(signal_number, frame):
    if signal_number == signal.SIGCHLD:
        try:
            os.waitpid(-1, os.WNOHANG)
        except ChildProcessError as e:
            print(repr(e), file=sys.stderr)


def main():
    app = connexion.App(__name__, specification_dir='./openapi/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'ARAX Translator Reasoner'},
                pythonic_params=True)
    CORS(app.app)
    signal.signal(signal.SIGCHLD, receive_sigchld)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    #### Read any load configuration details for this instance
    try:
        with open('openapi_server/flask_config.json') as infile:
            local_config = json.load(infile)
    except:
        local_config = { "port": 5000 }

    #### Start the service
    app.run(port=local_config['port'], threaded=True)


if __name__ == '__main__':
    main()
