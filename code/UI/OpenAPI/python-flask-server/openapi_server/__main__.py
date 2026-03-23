# ruff: noqa: E402
# pylint: disable=wrong-import-position
"""
Entry point for the ARAX OpenAPI Flask server.

This module initializes and launches the ARAX Translator Reasoner API service
using a Connexion/Flask application. It is intended to be executed via
`python -m openapi_server` in production environments.

Key responsibilities:
- Load runtime configuration from a local JSON config file.
- Optionally verify and update required ARAX databases.
- Optionally spawn and manage a background tasker process for asynchronous work.
- Configure signal handlers to ensure proper cleanup of child processes.
- Initialize OpenTelemetry tracing (Jaeger exporter) if enabled.
- Configure and start the Connexion-based Flask web server with CORS support.

Implementation notes:
- Uses `os.fork()` to launch the background tasker as a child process.
- Dynamically modifies `sys.path` to import ARAX modules from the repository layout.
- Suppresses selected third-party deprecation warnings (e.g., Jaeger exporter, pkg_resources).
- Uses a custom JSON provider for Flask response serialization.

Configuration:
- The configuration file (`flask_config.json`) resides alongside this module and may define:
    - `port` (int): TCP port for the Flask server (default: 5000)
    - `check_databases` (bool): Whether to verify/update databases at startup
    - `run_background_tasker` (bool): Whether to launch the background tasker
    - `force_disable_telemetry` (bool): Override to disable OpenTelemetry

Caveats:
- Relies on Unix-specific features (e.g., `os.fork()`); not compatible with Windows.
- The Jaeger exporter used here is deprecated in favor of OTLP; warning is suppressed.
- Dynamic `sys.path` modification assumes a specific repository structure.

This module is primarily intended for deployment and operational use rather than reuse.
"""
import warnings
warnings.filterwarnings(
    "ignore",
    message=r"Call to deprecated method __init__.*Jaeger.*",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API.*",
    category=UserWarning
)

import json
import os
import signal
import sys
import traceback
from pathlib import Path
import setproctitle
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.sdk.resources import Resource


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


FLASK_DEFAULT_TCP_PORT = 5000

HERE = Path(__file__).resolve().parent


def add_to_syspath(path: Path) -> None:
    path_str = str(path.resolve())
    if path_str not in sys.path:
        sys.path.append(path_str)




def instrument(app, host, port):
    provider = TracerProvider(
        resource=Resource.create({
            ResourceAttributes.SERVICE_NAME: "ARAX"
        })
    )
    trace.set_tracer_provider(provider)
    provider.add_span_processor(
        SimpleSpanProcessor(
            JaegerExporter(
                agent_host_name=host,
                agent_port=port
            )
        )
    )

    FlaskInstrumentor().instrument_app(app=app.app, tracer_provider=provider)
    RequestsInstrumentor().instrument(tracer_provider=provider)
    AioHttpClientInstrumentor().instrument(tracer_provider=provider)


def main():
    rtx_root_dir = HERE / "../../../../.."
    add_to_syspath(rtx_root_dir / "code")
    from RTXConfiguration import RTXConfiguration  # pylint: disable=import-outside-toplevel, import-error
    rtx_config = RTXConfiguration()

    araxquery_dir = rtx_root_dir / "code/ARAX/ARAXQuery"
    add_to_syspath(araxquery_dir)

    config_file_path = HERE / "flask_config.json"
    # Read any load configuration details for this instance
    try:
        with config_file_path.open('r', encoding="utf-8") as infile:
            local_config = json.load(infile)
    except Exception:
        eprint(f"Error loading config file: {config_file_path}")
        local_config = {}
    tcp_port = local_config.get('port', FLASK_DEFAULT_TCP_PORT)
    check_databases = local_config.get('check_databases', True)
    run_background_tasker = local_config.get('run_background_tasker', True)
    force_disable_telemetry = local_config.get('force_disable_telemetry', False)
    query_controller_fork_mode = local_config.get('query_controller_fork_mode', True)

    if check_databases:
        from ARAX_database_manager import ARAXDatabaseManager  # pylint: disable=import-outside-toplevel, import-error
        dbmanager = ARAXDatabaseManager(allow_downloads=True)
        try:
            eprint("Checking for complete databases")
            # check_versions returns True if new databases need to be downloaded
            if dbmanager.check_versions():
                eprint("Databases incomplete; running update_databases")
                dbmanager.update_databases()
            else:
                eprint("Databases seem to be complete")
        except Exception:
            eprint(traceback.format_exc())
            raise
        del dbmanager

    if run_background_tasker:
        parent_pid = os.getpid()
        pid = os.fork()
        if pid == 0:  # I am the child process
            from ARAX_background_tasker import ARAXBackgroundTasker  # pylint: disable=import-outside-toplevel, import-error
            sys.stdout = open(os.devnull, 'w', encoding="utf-8")  # pylint: disable=consider-using-with
            sys.stdin = open(os.devnull, 'r', encoding="utf-8")  # pylint: disable=consider-using-with
            setproctitle.setproctitle("python3 ARAX_background_tasker"
                                      f"::run_tasks [port={tcp_port}]")
            eprint("Starting background tasker in a child process")
            try:
                ARAXBackgroundTasker(parent_pid).run_tasks()
                eprint("Background tasker child process ended unexpectedly")
                os._exit(1)
            except Exception:
                eprint("Error in ARAXBackgroundTasker.run_tasks()")
                eprint(traceback.format_exc())
                os._exit(1)
        elif pid > 0:  # I am the parent process
            child_pid = pid

            def receive_sigterm(signal_number, _):
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

            def receive_sigchld(signal_number, _):
                if signal_number == signal.SIGCHLD:
                    while True:
                        try:
                            reaped_pid, _ = os.waitpid(-1, os.WNOHANG)
                            if reaped_pid == 0:
                                break
                        except ChildProcessError as e:
                            eprint(f"{e!r}; this is expected if there are "
                                   "no more child processes to reap")
                            break

            def receive_sigpipe(signal_number, _):
                if signal_number == signal.SIGPIPE:
                    eprint("pipe error")
            signal.signal(signal.SIGCHLD, receive_sigchld)
            signal.signal(signal.SIGPIPE, receive_sigpipe)
            signal.signal(signal.SIGTERM, receive_sigterm)
            eprint(f"Started the ARAX background tasker in child process {child_pid}")

        else:
            eprint("[__main__]: fork() unsuccessful")
            assert False, "****** fork() unsuccessful in __main__"

    # loading overly general nodes JSON file
    from Filter_KG.remove_nodes import RemoveNodes  # pylint: disable=import-outside-toplevel, import-error
    RemoveNodes.load_block_list_file()

    # Import web framework components only in parent process
    import connexion  # pylint: disable=import-outside-toplevel
    import flask_cors  # pylint: disable=import-outside-toplevel
    from openapi_server.provider import CustomJSONProvider  # pylint: disable=import-outside-toplevel
    specification_dir = HERE / "openapi"
    app = connexion.App(__name__, specification_dir=str(specification_dir))
    app.app.json_provider_class = CustomJSONProvider
    app.app.json = app.app.json_provider_class(app.app)
    app.app.config["QUERY_CONTROLLER_FORK_MODE"] = query_controller_fork_mode
    eprint(f"Using JSON provider: {type(app.app.json).__name__}")
    app.add_api('openapi.yaml',
                arguments={'title': 'ARAX Translator Reasoner'},
                pythonic_params=True)
    flask_cors.CORS(app.app)

    setproctitle.setproctitle(setproctitle.getproctitle() +
                              f" [port={tcp_port}]")
    if rtx_config.telemetry_enabled and not force_disable_telemetry:
        eprint("Starting OpenTelemetry instrumentation")
        instrument(app, rtx_config.jaeger_endpoint, rtx_config.jaeger_port)
    eprint(f"Starting flask application with TCP port: {tcp_port}")
    app.run(port=tcp_port, threaded=True)

if __name__ == '__main__':
    main()
