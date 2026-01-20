import connexion
import flask
import json
import os
import sys
import signal
import resource
import traceback
from typing import Iterable, Callable
import setproctitle

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../../ARAX/ARAXQuery")
import ARAX_query


rlimit_child_process_bytes = 34359738368  # 32 GiB

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

def child_receive_sigpipe(signal_number, frame):
    if signal_number == signal.SIGPIPE:
        eprint("[query_controller]: child process detected a "
               "SIGPIPE; exiting python")
        os._exit(0)


def run_query_dict_in_child_process(query_dict: dict,
                                    query_runner: Callable) -> Iterable[str]:
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
        sys.stdout = open('/dev/null', 'w')         # parent and child process should not share the same stdout stream object
        sys.stdin = open('/dev/null', 'r')          # parent and child process should not share the same stdin stream object
        os.close(read_fd)                   # child doesn't read from the pipe, it writes to it
        setproctitle.setproctitle("python3 query_controller::run_query_dict_in_child_process")       
        resource.setrlimit(resource.RLIMIT_AS, (rlimit_child_process_bytes, rlimit_child_process_bytes))  # set a virtual memory limit for the child process
        signal.signal(signal.SIGPIPE, child_receive_sigpipe) # get rid of signal handler so we don't double-print to the log on SIGPIPE error
        signal.signal(signal.SIGCHLD, signal.SIG_IGN) # disregard any SIGCHLD signal in the child process
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        try:
            with os.fdopen(write_fd, "w") as write_fo:  # child process needs to get a stream object for the file descriptor `write_fd`
                json_string_generator = query_runner(query_dict)
                for json_string in json_string_generator:
                    write_fo.write(json_string)
                    write_fo.flush()
# The reason why I am catching BaseException in the child process is because I
# want to ensure that under no circumstances does the child process's cpython
# exit with sys.exit; I only want it to exit with sys._exit, so no resource
# (that I might have missed) that is jointly owned by child process and parent
# process will be closed by the child process. The assumption that if such
# resources exist, they are owned by the parent process and not to be touched by
# the child process:                    
        except BaseException as e:
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


def _run_query_and_return_json_generator_nonstream(query_dict: dict) -> Iterable[str]:
    envelope = ARAX_query.ARAXQuery().query_return_message(query_dict)
    envelope_dict = envelope.to_dict()
    http_status = getattr(envelope, 'http_status', 200)
    envelope_dict['http_status'] = http_status
    yield json.dumps({"__http_status__": http_status}) + "\n"
    yield json.dumps(envelope_dict, sort_keys=True, allow_nan=False) + "\n"


def _run_query_and_return_json_generator_stream(query_dict: dict) -> Iterable[str]:
    return ARAX_query.ARAXQuery().query_return_stream(query_dict)


def query(request_body):  # noqa: E501
    """Initiate a query and wait to receive a Response

    :param request_body: Query information to be submitted
    :type request_body: Dict[str, ]

    :rtype: Response
    """

    # Note that we never even get here if the request_body is not schema-valid JSON

    query = connexion.request.get_json()

    #### Record the remote IP address in the query for now so it is available downstream
    query['remote_address'] = connexion.request.headers.get('x-forwarded-for', '???')

    mime_type = 'application/json'
    fork_mode = True  # :DEBUG: can turn this to False to disable fork-mode

    # import multiprocessing
    # multiprocessing.set_start_method('fork')
    if query.get('stream_progress', False):  # if stream_progress is specified and if it is True:


        http_status = None
        mime_type = 'text/event-stream'
        if not fork_mode:
            json_generator = _run_query_and_return_json_generator_stream(query)
        else:
            json_generator = run_query_dict_in_child_process(query,
                                                             _run_query_and_return_json_generator_stream)
        resp_obj = flask.Response(json_generator, mimetype=mime_type)
    else:
        if not fork_mode:
            json_generator = _run_query_and_return_json_generator_nonstream(query)
        else:
            json_generator = run_query_dict_in_child_process(query,
                                                         _run_query_and_return_json_generator_nonstream)
        status_line = next(json_generator)
        status_dict = json.loads(status_line)
        http_status = status_dict['__http_status__']        
        response_serialized_str = next(json_generator)
        resp_obj = flask.Response(response_serialized_str)
    return (resp_obj, http_status)
