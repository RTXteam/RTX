import connexion
import flask
import json
import os
import signal
import six
import sys
import tempfile
import time
from typing import Iterable, Callable

# this is needed for running the module as a script in "test mode" where the CWD is the "query_controllers" directory:
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../models")
import response

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../../../ARAX/ARAXQuery")
import ARAX_query

def _run_query_and_return_json_generator_nonstream(query_dict: dict) -> Iterable[str]:
    return (json.dumps(ARAX_query.ARAXQuery().query_return_message(query_dict, mode='RTXKG2').to_dict()),)

def _run_query_and_return_json_generator_stream(query_dict: dict) -> Iterable[str]:
    return ARAX_query.ARAXQuery().query_return_stream(query_dict, mode='RTXKG2')

def run_query_dict_in_child_process(query_dict: dict,
                                    query_runner: Callable) -> Iterable[str]:
    print("INFO: [query_controller]: Creating pipe and forking a child to handle the query", file=sys.stderr)
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    print(f"INFO: pid={pid}", file=sys.stderr)
    if pid == 0: # I am the child process
        os.close(read_fd)
        with os.fdopen(write_fd, "w") as write_fo:
            json_string_generator = query_runner(query_dict)
            for json_string in json_string_generator:
                write_fo.write(json_string)
                write_fo.flush()
        os._exit(0)
    elif pid > 0: # I am the parent process
        os.close(write_fd)
        read_fo = os.fdopen(read_fd, "r")
    else:
        assert False, "negative pid should never happen"
    return read_fo


def query(request_body):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: Dict[str, ]

    :rtype: Response
    """

    # Note that we never even get here if the request_body is not schema-valid JSON

    query = connexion.request.get_json()  # :QUESTION: why don't we use `request_body`?
    araxq = ARAX_query.ARAXQuery()

    if "stream_progress" in query and query['stream_progress'] is True:
        json_generator = run_query_dict_in_child_process(query,
                                                         _run_query_and_return_json_generator_stream)
        # Return a stream of data to let the client know what's going on
        resp_obj = flask.Response(json_generator, mimetype='text/plain')
        return resp_obj
    # Else perform the query and return the result
    else:
        json_generator = run_query_dict_in_child_process(query,
                                                         _run_query_and_return_json_generator_nonstream)
        resp_obj = response.Response.from_dict(json.loads(next(json_generator)))
        http_status = 200
        if hasattr(resp_obj, 'http_status'):
            http_status = resp_obj.http_status
        return (resp_obj, http_status)

# :TESTING: vvvvvvvvvvvvvvvvvv
if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    query_dict = {
        "operations": {
            "actions": [
                "add_qnode(ids=[CHEMBL.COMPOUND:CHEMBL112], key=n00)",
                "add_qnode(ids=[UniProtKB:P55000], key=n01)",
                "add_qedge(subject=n00, object=n01, key=e00)",
                "expand(edge_key=e00,kp=RTX-KG2)",
                "resultify()",
                "return(message=true, store=false)",
            ]
        }
    }
    for json_str in run_query_dict_in_child_process(query_dict, _run_query_and_return_json_generator_stream):
        print(json_str)
# :TESTING: ^^^^^^^^^^^^^^^^^^
