import json
import os
import setproctitle
import signal
import sys
import traceback
from typing import Union

from typing import TextIO, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../../ARAX/ResponseCache")
from response_cache import ResponseCache

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../models")


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


fork_mode = True


def child_receive_sigpipe(signal_number, frame):
    if signal_number == signal.SIGPIPE:
        eprint("[response_controller]: child process detected a "
               "SIGPIPE; exiting python")
        os._exit(0)


def _get_response(response_id: str) -> Union[dict[str, Any], tuple[Any, ...]]:
    response_cache = ResponseCache()
    return response_cache.get_response(response_id)


def get_response_in_child_process(response_id: str) -> TextIO:
    eprint("[response_controller]: Creating pipe and "
           "forking a child to get the response")
    read_fd, write_fd = os.pipe()

# If there is any output in the buffer for either of those streams, when os.fork
# is called, there will be two copies of the buffer, both pointing to the same
# output stream, with the attendant potential for a double-write to the output
# stream. So, ensure that both stderr and stdout are flushed before the fork.
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
                write_fo.write(json.dumps(envelope))
                write_fo.flush()               
# The reason why I am catching BaseException in the child process is because I
# want to ensure that under no circumstances does the child process's cpython
# exit with sys.exit; I only want it to exit with sys._exit, so no resource
# (that I might have missed) that is jointly owned by child process and parent
# process will be closed by the child process. The assumption that if such
# resources exist, they are owned by the parent process and not to be touched by
# the child process:
        except BaseException as e:
            eprint("Exception in response_controller.get_response_in_child_process: "
                   f"{type(e)}\n{traceback.format_exc()}")
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


def get_response(response_id: str) -> Union[dict[str, Any], tuple[Any, ...]]:  # noqa: E501
    """Request a previously stored response from the server

     # noqa: E501

    :param response_id: Identifier of the response to return
    :type response_id: str

    :rtype: Response
    """

    if fork_mode:
        read_fo = get_response_in_child_process(response_id)
        resp_obj = json.load(read_fo)
        if type(resp_obj) is list and len(resp_obj) == 2:
            resp_obj = tuple(resp_obj)
    else:
        resp_obj = _get_response(response_id)
    return resp_obj


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

