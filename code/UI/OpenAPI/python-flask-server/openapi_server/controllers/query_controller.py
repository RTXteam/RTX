"""
Query controller for executing ARAX queries within a Flask/Connexion API.

This module implements the `/query` endpoint for the Translator Reasoner API,
providing both streaming and non-streaming execution modes. Queries are
submitted as JSON dictionaries (validated upstream by Connexion) and executed
via the ARAXQuery engine.

Key features:
- Optional execution of queries in a forked child process to isolate resource
  usage and improve robustness (`QUERY_CONTROLLER_FORK_MODE`).
- Inter-process communication using an OS pipe, allowing the child process to
  stream JSON output back to the parent.
- Support for streaming responses using Server-Sent Events (SSE) when
  `stream_progress` is requested.
- Enforcement of per-query memory limits in forked child processes.
- Defensive handling of signals (e.g., SIGPIPE) and process termination to
  prevent resource corruption or duplicate output.
- Injection of client metadata (e.g., remote IP address) into the query payload
  for downstream logging and analysis.

Design notes:
- The child process uses `os._exit()` to avoid invoking Python cleanup handlers
  that could interfere with resources shared with the parent.
- Standard input/output streams are redirected in the child process to avoid
  shared buffering issues after `fork()`.
- Generators are used to stream JSON responses incrementally, minimizing memory
  overhead for large results.
- The first yielded line in non-streaming mode encodes the HTTP status, followed
  by the serialized response payload.

This module assumes that all incoming requests have already passed OpenAPI
schema validation via Connexion.
"""
import json
import os
import sys
import signal
import resource
import traceback
from typing import Callable, Iterator
import connexion
import flask
import setproctitle

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../../ARAX/ARAXQuery")
import ARAX_query  # pylint: disable=import-outside-toplevel,import-error,wrong-import-position


RLIMIT_CHILD_PROCESS_BYTES = 34359738368  # 32 GiB

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def child_receive_sigpipe(signal_number, _):
    if signal_number == signal.SIGPIPE:
        eprint("[query_controller]: child process detected a "
               "SIGPIPE; exiting python")
        os._exit(0)


def run_query_dict_in_child_process(query_dict: dict,
                                    query_runner: Callable) -> Iterator[str]:
    eprint("[query_controller]: Creating pipe and "
           "forking a child to handle the query")
    read_fd, write_fd = os.pipe()
# If there is any output in the buffer for either of those streams, when os.fork
# is called, there will be two copies of the buffer, both pointing to the same
# output stream, with the attendant potential for a double-write to the output
# stream. So, ensure that both stderr and stdout are flushed before the fork.
    sys.stderr.flush()
    sys.stdout.flush()

    pid = os.fork()

    if pid == 0:  # I am the child process
        # parent and child process should not share the same stdout stream object
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')  # pylint: disable=consider-using-with
        # parent and child process should not share the same stdin stream object
        sys.stdin = open(os.devnull, 'r', encoding='utf-8')  # pylint: disable=consider-using-with
        os.close(read_fd)                   # child doesn't read from the pipe, it writes to it
        setproctitle.setproctitle("python3 query_controller::run_query_dict_in_child_process")
        # set a virtual memory limit for the child process
        resource.setrlimit(
            resource.RLIMIT_AS, (RLIMIT_CHILD_PROCESS_BYTES,
                                 RLIMIT_CHILD_PROCESS_BYTES))
        # get rid of signal handler so we don't double-print to the log on SIGPIPE error
        signal.signal(signal.SIGPIPE, child_receive_sigpipe)
        # disregard any SIGCHLD signal in the child process
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        try:
            # child process needs to get a stream object for the file descriptor `write_fd`
            with os.fdopen(write_fd, "w") as write_fo:
                json_string_generator = query_runner(query_dict)
                for json_string in json_string_generator:
                    write_fo.write(json_string)
                    write_fo.flush()
        except BaseException as e:  # pylint: disable=broad-exception-caught
            # The reason why I am catching BaseException in the child process is because I
            # want to ensure that under no circumstances does the child process's cpython
            # exit with sys.exit; I only want it to exit with sys._exit, so no resource
            # (that I might have missed) that is jointly owned by child process and parent
            # process will be closed by the child process. The assumption that if such
            # resources exist, they are owned by the parent process and not to be touched by
            # the child process:
            print("Exception in query_controller.run_query_dict_in_child_process: "
                  f"{type(e)}\n{traceback.format_exc()}", file=sys.stderr)
            os._exit(1)
        os._exit(0)
    elif pid > 0:  # I am the parent process
        os.close(write_fd)  # the parent does not write to the pipe, it reads from it
        eprint(f"[query_controller]: child process pid={pid}")
        read_fo = os.fdopen(read_fd, "r")
    else:
        eprint("[query_controller]: fork() unsuccessful")
        assert False, "********** fork() unsuccessful; something went very wrong *********"
    return read_fo


def _run_query_and_return_json_generator_nonstream(query_dict: dict) -> Iterator[str]:
    envelope = ARAX_query.ARAXQuery().query_return_message(query_dict)
    envelope_dict = envelope.to_dict()
    http_status = getattr(envelope, 'http_status', 200)
    envelope_dict['http_status'] = http_status
    yield json.dumps({"__http_status__": http_status}) + "\n"
    yield json.dumps(envelope_dict, sort_keys=True, allow_nan=False) + "\n"


def _run_query_and_return_json_generator_stream(query_dict: dict) -> Iterator[str]:
    return ARAX_query.ARAXQuery().query_return_stream(query_dict)


def query(request_body: dict) -> tuple[flask.Response, int | None]:  # noqa: E501
    """Initiate a query and wait to receive a Response
    """

    app = flask.current_app
    fork_mode = app.config.get("QUERY_CONTROLLER_FORK_MODE", True)

    # Note that we never even get here if the request_body is not schema-valid JSON

    request_body = dict(request_body)

    x_forwarded_for = connexion.request.headers.get("x-forwarded-for")
    remote_address = (
        x_forwarded_for.split(",")[0].strip()
        if x_forwarded_for
        else connexion.request.remote_addr or "???"
    )
    #### Record the remote IP address in the query for now so it is available downstream
    request_body['remote_address'] = remote_address

    # if stream_progress is specified and if it is True:
    if request_body.get('stream_progress', False):

        http_status = None
        if not fork_mode:
            json_generator = _run_query_and_return_json_generator_stream(
                request_body)
        else:
            json_generator = run_query_dict_in_child_process(
                request_body,
                _run_query_and_return_json_generator_stream)
        resp_obj = flask.Response(json_generator, mimetype="text/event-stream")
    else:
        if not fork_mode:
            json_generator = _run_query_and_return_json_generator_nonstream(
                request_body)
        else:
            json_generator = run_query_dict_in_child_process(
                request_body,
                _run_query_and_return_json_generator_nonstream)
        status_line = next(json_generator)
        status_dict = json.loads(status_line)
        http_status = status_dict['__http_status__']
        response_serialized_str = next(json_generator)
        resp_obj = flask.Response(response_serialized_str, mimetype="application/json")
    return resp_obj, http_status
