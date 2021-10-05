#!/usr/bin/env python3

import connexion
import flask
import logging
import signal

## :DEBUG: vvvvvvvvvvvvvvvvvv
#logging.basicConfig(filename="/tmp/connexion_fork-test.log",
#                    filemode="a",
#                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
#                                                datefmt='%H:%M:%S',
#                                                level=logging.DEBUG)
# :DEBUG: ^^^^^^^^^^^^^^^^^^

from flask_cors import CORS

from openapi_server import encoder

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../ARAX/ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../reasoningtool/QuestionAnswering")

# :DEBUG: vvvvvvvvvvvvvvvvvv
# # Capture and log any unexpected exceptions raise by handler code:
#def error_handler(exception):
#    flask.current_app.logger.exception(exception)
# :DEBUG: ^^^^^^^^^^^^^^^^^^

def receive_sigchld(signal_number, frame):
    if signal_number == signal.SIGCHLD:
        os.waitpid(-1, os.WNOHANG)

def main():
    app = connexion.App(__name__, specification_dir='./openapi/')
# :DEBUG: vvvvvvvvvvvvvvvvvv
#    app.app.logger.debug("Starting up connexion server")
# :DEBUG: ^^^^^^^^^^^^^^^^^^
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'ARAX Translator Reasoner'},
                pythonic_params=True)
# :DEBUG: vvvvvvvvvvvvvvvvvv
#    app.add_error_handler(Exception, error_handler)
# :DEBUG: ^^^^^^^^^^^^^^^^^^
    CORS(app.app)
    signal.signal(signal.SIGCHLD, receive_sigchld)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    app.run(port=5001, threaded=True)


if __name__ == '__main__':
    main()
