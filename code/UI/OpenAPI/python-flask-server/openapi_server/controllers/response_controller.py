import json
import os
import setproctitle
import signal
import sys
import traceback

from openapi_server import util
from typing import Iterable

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../ARAX/ResponseCache")
from response_cache import ResponseCache

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../models")
import response


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


do_fork = False


def child_receive_sigpipe(signal_number, frame):
    if signal_number == signal.SIGPIPE:
        eprint("[response_controller]: child process detected a "
               "SIGPIPE; exiting python")
        os._exit(0)


def _get_response(response_id: str) -> Iterable[str]:
    response_cache = ResponseCache()
    return response_cache.get_response(response_id)


def get_response_in_child_process(response_id: str) -> dict:
    eprint("[response_controller]: Creating pipe and "
           "forking a child to get the response")
    read_fd, write_fd = os.pipe()

    sys.stderr.flush()
    sys.stdout.flush()
    pid = os.fork()
    if pid == 0:  # I am the child process
        sys.stdout = open('/dev/null', 'w')
        sys.stdin = open('/dev/null', 'r')
        # child doesn't read from the pipe, it writes to it
        os.close(read_fd)
        setproctitle.setproctitle("python3 response_controller"
                                  "::get_response_in_child_process")
        # get rid of signal handler so we don't double-print to the log on
        # SIGPIPE error
        signal.signal(signal.SIGPIPE, child_receive_sigpipe)
        # disregard any SIGCHLD signal in the child process
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        try:
            # child process needs to get a stream object for the file
            # descriptor `write_fd`
            with os.fdopen(write_fd, 'w') as write_fo:
                envelope = _get_response(response_id)
                json_strings = (json.dumps(envelope.to_dict()),)
                for json_string in json_strings:
                    write_fo.write(json_string)
                    write_fo.flush()
        except BaseException as e:
            print("Exception in response_controller.get_response_"
                  "in_child_process: "
                  f"{type(e)}\n{traceback.print_exc()}", file=sys.stderr)
            os._exit(1)
        os._exit(0)
    elif pid > 0:  # I am the parent process
        # the parent does not write to the pipe, it reads from it
        os.close(write_fd)
        eprint(f"[response_controller]: child process pid={pid}")
        read_fo = os.fdopen(read_fd, 'r')
    else:
        eprint("[response_controller]: fork() unsuccessful")
        assert False, "********** fork() unsuccessful; " +\
            "something went very wrong *********"
    return read_fo


def get_response(response_id: str):  # noqa: E501
    """Request a previously stored response from the server

     # noqa: E501

    :param response_id: Identifier of the response to return
    :type response_id: str

    :rtype: Response
    """

    if do_fork:
        json_generator = get_response_in_child_process(response_id)
        the_dict = json.loads(next(json_generator))
        http_status = the_dict.get('http_status', 200)
        resp_obj = response.Response.from_dict(the_dict)
        resp_obj.http_status = http_status
    else:
        resp_obj = _get_response(response_id)
        http_status = 200
    return (resp_obj, http_status)


def post_response(body):  # noqa: E501
    """Annotate a response

     # noqa: E501

    :param body: Object that provides annotation information
    :type body:

    :rtype: object
    """
    response_cache = ResponseCache()
    response_cache.store_callback(body)
    return 'received!'

