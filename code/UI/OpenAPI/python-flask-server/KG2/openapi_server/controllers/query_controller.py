import connexion, flask
import json
import os, sys, signal
import resource
import logging
import tempfile
from typing import Iterable, Callable

rlimit_child_process_bytes = 34359738368  # 32 GiB

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../../../ARAX/ARAXQuery")
import ARAX_query

def child_receive_sigpipe(signal_number, frame):
    if signal_number == signal.SIGPIPE:
        logging.info("[query_controller]: child process detected a SIGPIPE; exiting python")
        os._exit(0)

def run_query_dict_in_child_process(query_dict: dict,
                                    query_runner: Callable) -> Iterable[str]:
    logging.debug("[query_controller]: Creating pipe and forking a child to handle the query")
    read_fd, write_fd = os.pipe()

    child_process_log_filename = tempfile.mkstemp(prefix='arax-query-controller-child-process-', suffix='.log')[1]
    logging.info(f"[query_controller]: child process log file name {child_process_log_filename}")

    # always flush stdout and stderr before calling fork(); someone could have turned off auto-flushing and we don't want double-output
    sys.stderr.flush()
    sys.stdout.flush()

    pid = os.fork()

    if pid == 0: # I am the child process
        log_stream = open(child_process_log_filename, 'a')  # not using "with" because we need this stream to persist
        sys.stderr = log_stream # parent and child process should not share the same stderr stream object
        logger = logging.getLogger()
        for hdlr in logger.handlers:  # child process shall not do any logging except what we authorize, to avoid thread issue
            logger.removeHandler(hdlr)
        new_handler = logging.StreamHandler(stream=log_stream)
        new_handler.setLevel(logging.INFO)  # :DEBUG: this can be changed to logging.DEBUG if you want, for debugging purposes
        logger.addHandler(new_handler)  # install the new logging handler for the child process, that writes to the new stderr
        sys.stdout = open('/dev/null', 'w')         # parent and child process should not share the same stdout stream object
        sys.stdin = open('/dev/null', 'r')          # parent and child process should not share the same stdin stream object
        os.close(read_fd)                   # child doesn't read from the pipe, it writes to it 
        resource.setrlimit(resource.RLIMIT_AS, (rlimit_child_process_bytes, rlimit_child_process_bytes))  # set a virtual memory limit for the child process
        signal.signal(signal.SIGPIPE, child_receive_sigpipe) # get rid of signal handler so we don't double-print to the log on SIGPIPE error
        signal.signal(signal.SIGCHLD, signal.SIG_IGN) # disregard any SIGCHLD signal in the child process
        with os.fdopen(write_fd, "w") as write_fo:  # child process needs to get a stream object for the file descriptor `write_fd`
            json_string_generator = query_runner(query_dict)
            for json_string in json_string_generator:
                write_fo.write(json_string)
                write_fo.flush()
        os._exit(0)
    elif pid > 0: # I am the parent process
        os.close(write_fd)  # the parent does not write to the pipe, it reads from it
        logging.debug("[query_controller]: child process pid={pid}")
        read_fo = os.fdopen(read_fd, "r")
    else:
        logging.error("[query_controller]: fork() unsuccessful")
        assert False, "********** fork() unsuccessful; something went very wrong *********"
    return read_fo


def _run_query_and_return_json_generator_nonstream(query_dict: dict) -> Iterable[str]:
    return (json.dumps(ARAX_query.ARAXQuery().query_return_message(query_dict, mode='RTXKG2').to_dict()),)


def _run_query_and_return_json_generator_stream(query_dict: dict) -> Iterable[str]:
    return ARAX_query.ARAXQuery().query_return_stream(query_dict, mode='RTXKG2')


def query(request_body):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: Dict[str, ]

    :rtype: Response
    """

    # Note that we never even get here if the request_body is not schema-valid JSON

    query = connexion.request.get_json()  # :QUESTION: why don't we use `request_body`?

    mime_type = 'application/json'

    http_status = 200
    if query.get('stream_progress', False):  # if stream_progress is specified and if it is True:

        fork_mode = True # :DEBUG: can turn this to False to disable fork-mode
        http_status = None
        mime_type = 'text/event-stream'

        if not fork_mode:
            json_generator = _run_query_and_return_json_generator_stream(query)
        else:
            json_generator = run_query_dict_in_child_process(query,
                                                             _run_query_and_return_json_generator_stream)

    # Else perform the query and return the result
    else:
        json_generator = run_query_dict_in_child_process(query,
                                                         _run_query_and_return_json_generator_nonstream)


    resp_obj = flask.Response(json_generator, mimetype=mime_type)
    if http_status is not None and hasattr(resp_obj, 'http_status'):
        http_status = resp_obj.http_status
    else:
        http_status = None

    return (resp_obj, http_status)


# :TESTING: vvvvvvvvvvvvvvvvvv
# if __name__ == "__main__":
#     signal.signal(signal.SIGPIPE, signal.SIG_IGN)
#     query_dict = {
#         "operations": {
#             "actions": [
#                 "add_qnode(ids=[CHEMBL.COMPOUND:CHEMBL112], key=n00)",
#                 "add_qnode(ids=[UniProtKB:P55000], key=n01)",
#                 "add_qedge(subject=n00, object=n01, key=e00)",
#                 "expand(edge_key=e00,kp=RTX-KG2)",
#                 "resultify()",
#                 "return(message=true, store=false)",
#             ]
#         }
#     }
#     for json_str in run_query_dict_in_child_process(query_dict, _run_query_and_return_json_generator_stream):
#         print(json_str)
# :TESTING: ^^^^^^^^^^^^^^^^^^
