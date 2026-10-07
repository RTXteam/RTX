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
import yaml
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
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
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

trapi_openapi_definition_cache = None
def trapi_openapi_definition():
    global trapi_openapi_definition_cache
    if trapi_openapi_definition_cache is None:
        yaml_filename = os.path.dirname(os.path.abspath(__file__)) + "/openapi/openapi.yaml"
        eprint(f"INFO: Reading OpenAPI definition {yaml_filename}")
        with open( yaml_filename, "r") as infile:
            trapi_openapi_definition_cache = yaml.safe_load(infile)
    return trapi_openapi_definition_cache


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

    #FlaskInstrumentor().instrument_app(app=app.app, tracer_provider=provider)
    #HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    #RequestsInstrumentor().instrument(tracer_provider=provider)
    #SQLite3Instrumentor().instrument(tracer_provider=provider)
    #AioHttpClientInstrumentor().instrument(tracer_provider=provider)


def main():
    rtx_root_dir = HERE / "../../../../.."
    add_to_syspath(rtx_root_dir / "code")
    from RTXConfiguration import RTXConfiguration  # pylint: disable=import-outside-toplevel, import-error
    rtx_config = RTXConfiguration()

    araxquery_dir = rtx_root_dir / "code/ARAX/ARAXQuery"
    add_to_syspath(araxquery_dir)

    code_dir = rtx_root_dir / "code/ARAX/ResponseCache"
    add_to_syspath(code_dir)

    code_dir = rtx_root_dir / "code/ARAX/KnowledgeSources"
    add_to_syspath(code_dir)

    # See ARAX issue 2788. Load kp_info_cacher once in the parent, before
    # the fork below and before any request threads start, so two threads
    # never import it for the first time at the same moment. Import the
    # bare name, not Expand.kp_info_cacher, because that is the sys.modules
    # key every runtime site uses and the one the race is on.
    add_to_syspath(araxquery_dir / "Expand")
    import kp_info_cacher  # noqa: F401  # pylint: disable=import-outside-toplevel, import-error, unused-import

    # See ARAX issue 2800. node_synonymizer builds its BMT toolkit lazily, so
    # build it here once in the single-threaded parent, before the fork below
    # and before any request threads start. Otherwise two request threads could
    # trigger the first build at the same moment. get_bmt_toolkit caches one
    # toolkit process-wide, so every controller reuses this one.
    nodesyn_dir = rtx_root_dir / "code/ARAX/NodeSynonymizer"
    add_to_syspath(nodesyn_dir)
    #try:
    #    import node_synonymizer  # pylint: disable=import-outside-toplevel, import-error
    #    node_synonymizer.get_bmt_toolkit()
    #except Exception as exc:  # pylint: disable=broad-exception-caught
    #    eprint("FATAL: NodeSynonymizer could not load the BMT toolkit at "
    #           f"startup, aborting. {exc}")
    #    sys.exit(1)

    config_file_path = HERE / "flask_config.json"
    # Read any local configuration details for this instance
    local_config = {}
    try:
        with config_file_path.open('r', encoding="utf-8") as infile:
            local_config = json.load(infile)
        eprint(f"Loaded config file {config_file_path}")
    except FileNotFoundError:
        eprint("Using default config options because could not find "
               f"config file: {config_file_path}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in config file: {config_file_path}: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Unable to read config file: {config_file_path}: {exc}") from exc
    tcp_port = local_config.get('port', FLASK_DEFAULT_TCP_PORT)
    check_databases = local_config.get('check_databases', True)
    run_background_tasker = local_config.get('run_background_tasker', True)
    force_disable_telemetry = local_config.get('force_disable_telemetry', False)
    query_fork_mode = local_config.get('query_fork_mode', True)
    query_fork_mode = False  #T2FIXME
    child_process_rlimit = local_config.get('child_process_rlimit', 34359738368)

    if check_databases:
        from ARAX_database_manager import ARAXDatabaseManager  # pylint: disable=import-outside-toplevel, import-error
        dbmanager = ARAXDatabaseManager(allow_downloads=True)
        try:
            eprint("Checking for complete databases")
            # check_versions returns True if new databases need to be downloaded
            if dbmanager.check_versions():
                if (rtx_config.domain == "arax.ncats.io" and (
                        rtx_config.maturity == "development" or rtx_config.maturity == "production")):
                    eprint("ARAX databases incomplete; checking if only a symlink is missing")
                    dbmanager.symlink_from_central_and_write_versions(debug=True)
                else:
                    eprint("ARAX databases incomplete; unable to fix on this system; aborting application server startup")
                    sys.exit(1)
            eprint("ARAX databases are complete; proceeding with application start-up")
        except Exception:  # pylint: disable=broad-exception-caught
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
            except Exception:  # pylint: disable=broad-exception-caught
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
    #from Filter_KG.remove_nodes import RemoveNodes  # pylint: disable=import-outside-toplevel, import-error
    #RemoveNodes.load_block_list_file()

    from fastapi import FastAPI, APIRouter
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn # pylint: disable=import-outside-toplevel

    #from openapi_server.apis.pubmed_mesh_ngd_api import router as PubmedMeshNgdApiRouter
    #from openapi_server.apis.asyncquery_api import router as AsyncqueryApiRouter
    #from openapi_server.apis.asyncquery_status_api import router as AsyncqueryStatusApiRouter
    from openapi_server.apis.entity_api import router as EntityApiRouter
    #from openapi_server.apis.example_questions_api import router as ExampleQuestionsApiRouter
    from openapi_server.apis.meta_knowledge_graph_api import router as MetaKnowledgeGraphApiRouter
    from openapi_server.apis.query_api import router as QueryApiRouter
    from openapi_server.apis.response_api import router as ResponseApiRouter
    from openapi_server.apis.status_api import router as StatusApiRouter
    #from openapi_server.apis.translate_api import router as TranslateApiRouter

    # In FastAPI, custom JSON encoding is typically handled by creating a custom 
    # Response class (e.g., inheriting from starlette.responses.JSONResponse)
    # from openapi_server.provider import CustomJSONResponse 
    app = FastAPI(
        docs_url="/devED/api/arax/v2.0/docs",
        openapi_url="/devED/api/arax/v2.0/openapi.json"
        )
    app.openapi = trapi_openapi_definition
    api_router = APIRouter(prefix="/devED/api/arax/v2.0")
    app.include_router(api_router)

    api_prefix = "/devED/api/arax/v2.0"
    #app.include_router(PubmedMeshNgdApiRouter, prefix=api_prefix)
    #app.include_router(AsyncqueryApiRouter, prefix=api_prefix)
    #app.include_router(AsyncqueryStatusApiRouter, prefix=api_prefix)
    app.include_router(EntityApiRouter, prefix=api_prefix)
    #app.include_router(ExampleQuestionsApiRouter, prefix=api_prefix)
    app.include_router(MetaKnowledgeGraphApiRouter, prefix=api_prefix)
    app.include_router(QueryApiRouter, prefix=api_prefix)
    app.include_router(ResponseApiRouter, prefix=api_prefix)
    app.include_router(StatusApiRouter, prefix=api_prefix)
    #app.include_router(TranslateApiRouter, prefix=api_prefix)

# Store configuration in app.state
    app.state.QUERY_FORK_MODE = query_fork_mode
    app.state.CHILD_PROCESS_RLIMIT = child_process_rlimit

    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setproctitle.setproctitle(setproctitle.getproctitle() +
                              f" [port={tcp_port}]")
    if rtx_config.telemetry_enabled and not force_disable_telemetry:
        eprint("NOT Starting OpenTelemetry instrumentation")
        #instrument(app, rtx_config.jaeger_endpoint, rtx_config.jaeger_port)


    eprint(f"Starting flask application with TCP port: {tcp_port}")
    uvicorn.run(app, host="0.0.0.0", port=tcp_port)


if __name__ == '__main__':
    main()
