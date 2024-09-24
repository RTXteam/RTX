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
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.aiohttp_client import (
    AioHttpClientInstrumentor
)
from opentelemetry import trace
from opentelemetry.trace.span import Span
from opentelemetry.sdk.resources import  Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


FLASK_DEFAULT_TCP_PORT = 5008
global child_pid
child_pid = None
global parent_pid
parent_pid = None

CONFIG_FILE = 'openapi_server/flask_config.json'

def instrument(app, host, port):
    
    service_name = "RTX-KG2"

    trace.set_tracer_provider(TracerProvider(
        resource=Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name
        })
    ))
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(
            JaegerExporter(
                        agent_host_name=host,
                        agent_port=port
        )
        )
    )
    # trace.get_tracer_provider().get_tracer(__name__)
    tracer_provider = trace.get_tracer(__name__)
    FlaskInstrumentor().instrument_app(app=app.app, tracer_provider=trace)
    RequestsInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()

def main():

    rtx_config = RTXConfiguration()

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

    # Read any load configuration details for this instance
    try:
        with open(CONFIG_FILE, 'r') as infile:
            local_config = json.load(infile)
    except Exception:
        eprint(f"Error loading config file: {CONFIG_FILE}")
        local_config = {"port": FLASK_DEFAULT_TCP_PORT}
    tcp_port = local_config['port']

    parent_pid = os.getpid()

    pid = os.fork()
    if pid == 0:  # I am the child process
        from ARAX_background_tasker import ARAXBackgroundTasker
        sys.stdout = open('/dev/null', 'w')
        sys.stdin = open('/dev/null', 'r')
        setproctitle.setproctitle("python3 ARAX_background_tasker"
                                  f"::run_tasks [port={tcp_port}]")
        eprint("Starting background tasker in a child process")
        try:
            ARAXBackgroundTasker(parent_pid,
                                 run_kp_info_cacher=False).run_tasks()
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
                    sys.exit(0)
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
        child_pid = pid
        signal.signal(signal.SIGCHLD, receive_sigchld)
        signal.signal(signal.SIGPIPE, receive_sigpipe)
        signal.signal(signal.SIGTERM, receive_sigterm)

        eprint("Starting flask application in the parent process")
        setproctitle.setproctitle(setproctitle.getproctitle() +
                                  f" [port={tcp_port}]")
        if rtx_config.telemetry_enabled:
            instrument(app, rtx_config.jaeger_endpoint, rtx_config.jaeger_port)
        app.run(port=local_config['port'], threaded=True)
    else:
        eprint("[__main__]: fork() unsuccessful")
        assert False, "****** fork() unsuccessful in __main__"


if __name__ == '__main__':
    main()
