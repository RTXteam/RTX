#!/usr/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import datetime


class ARAXResponse:

    #### Class variables
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    level_names = { 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR' }
    equal_or_greater_levels = {
        'DEBUG': { 'DEBUG': 1, 'INFO': 1, 'WARNING': 1, 'ERROR': 1 },
        'INFO': { 'INFO': 1, 'WARNING': 1, 'ERROR': 1 },
        'WARNING': { 'WARNING': 1, 'ERROR': 1 },
        'ERROR': { 'ERROR': 1 }
        }
    output = None
    #output = 'STDERR'

    #### Constructor
    def __init__(self, status='OK', logging_level=WARNING, error_code='OK', message='Normal completion'):
        self.status = status
        self.http_status = 200
        self.logging_level = logging_level
        self.error_code = error_code
        self.message = message
        self.messages = []
        self.n_messages = 0
        self.n_errors = 0
        self.n_warnings = 0
        self.data = {}
        self.envelope = None

        self.query_plan = { 'qedge_keys': {}, 'counter': 0 }


    #### Add a debugging message
    def debug(self, message, code=None):
        """Public method that adds a DEBUG level message to the response object logger.
        DEBUG level messages should only be of interest to code developers.

        :param message: A natural English statement describing ongoing events.
        :type message: str
        """

        if code is None:
            code = ''
        self._add_message( message, self.DEBUG, code=code )


    #### Add an info message
    def info(self, message, code=None):
        """Public method that adds an INFO level message to the response object logger.
        INFO level messages should be of interest to ordinary users regarding the
        inner workings of the process or about innocuous assumptions made.

        :param message: A natural English statement describing ongoing events.
        :type message: str
        """

        if code is None:
            code = ''
        self._add_message( message, self.INFO, code=code )


    #### Add a warning message
    def warning(self, message, code=None):
        """Public method that adds a WARNING level message to the response object logger.
        WARNING level messages should be seen by ordinary users usually because
        crucial assumption was made or some subtask could not be successfully completed,
        although execution will continue as best as possible.

        :param message: A natural English statement describing an important event.
        :type message: str
        """

        if code is None:
            code = ''
        self._add_message( message, self.WARNING, code=code )
        self.n_warnings += 1


    #### Add an error message
    def error(self, message, code='UnknownError', error_code=None, http_status=400):
        """Public method that adds an ERROR level message to the response object logger.
        ERROR level messages must be conveyed to ordinary users usually because a
        crucial subtask could not be successfully completed and successful execution
        of the entire request cannot be completed. Note that logging an ERROR does
        not halt execution. Execution may continue for a while and multiple ERRORs may
        be logged, but at some point, execution should be halted and all logged events
        should be returned to the user for inspection and triage. The response object
        status attribute is automatically set to ERROR.

        :param message: A natural English statement describing a critical error.
        :type message: str
        :param code: A terse, unique string identifying the error (e.g. 'FileNotFound').
        :type code: str
        :param http_status: Integer HTTP status code to return (e.g. 400, 404, 500, 200).
        :type http_status: str
        """

        # Some backwards compatibility
        if error_code is not None and code is 'UnknownError':
            code = error_code

        self._add_message( message, self.ERROR, code=code )
        self.n_errors += 1
        self.status = 'ERROR'
        self.http_status = http_status
        self.error_code = code
        self.message = message


    #### Add a message
    def _add_message(self, message, level, code=None):
        """Private method called by the public methods to actually add the message to the log.

        :param message: A natural English statement describing the message.
        :type message: str
        :param level: One of the four numerical levels (i.e. 10, 20, 30, 40).
        :type level: int
        :param code: A terse machine-readable and human-readable code (e.g, KPNotAvailable).
        :type code: str
        """

        timestamp = str(datetime.datetime.now().isoformat())
        self.messages.append( { 'timestamp': timestamp, 'level': self.level_names[level], 'code': code, 'message': message } )
        self.n_messages += 1

        # Create a pretty printable message prefix
        prefix = f"{timestamp} {self.level_names[level]}: "
        if code is not None:
            prefix += f"[{code}] "

        if self.output is not None:
            if self.output == 'STDOUT':
                print(f"{prefix}{message}", flush=True)
            if self.output == 'STDERR':
                eprint(f"{prefix}{message}", flush=True)


    #### Merge a new response into an existing response
    def merge(self, response_to_merge):
        """Public method that merges the content of the passed response to the self response
        When the result of a called object method returns a new response object, this method
        should be used to merge the contents of the returned response object into the
        current response object. If the passed response is in and ERROR state, the current
        response is also set to an error state.

        :param response_to_merge: A response object received by the caller to be merged into the callers response object.
        :type response_to_merge: Response
        """
        self.n_messages += response_to_merge.n_messages
        self.n_errors += response_to_merge.n_errors
        self.n_warnings += response_to_merge.n_warnings
        for message in response_to_merge.messages:
            self.messages.append(message)
        if response_to_merge.status != 'OK':
            self.status = response_to_merge.status
            self.error_code = response_to_merge.error_code
            self.http_status = response_to_merge.http_status
            self.message = response_to_merge.message


    #### Return a text summary of the current state of the Response
    def show(self, level=WARNING):
        """Public method that returns a string buffer of a nice plain text rendering of the response object
        When the user or developer wants to see the current state of the response object,
        including all messages more severe that a certain level
        use print(response.show(level=response.INFO))

        :param level: Minimum message level to include in the string response (default: response.WARNING).
        :type level: integer
        :return: A string buffer (with newlines) suitable for plain-text printing
        :rtype: str
        """
        buffer = f"Response:\n"
        buffer += f"  status: {self.status}\n"
        buffer += f"  n_errors: {self.n_errors}  n_warnings: {self.n_warnings}  n_messages: {self.n_messages}\n"
        if self.status != 'OK':
            buffer += f"  error_code: {self.error_code}   message: {self.message}\n"
        for message in self.messages:
            if message['level'] in self.equal_or_greater_levels[self.level_names[level]]:

                # Create a pretty printable message prefix
                prefix = f"{message['timestamp']} {message['level']}: "
                if message['code'] is not None:
                    prefix += f"[{message['code']}] "

                buffer += f"  - {prefix}{message['message']}\n"
        return buffer


    #### Return the current list of messages as a formatted list
    def messages_list(self, level=WARNING):
        """Public method that returns a list of all messages greater or equal to the specified level
        Useful when a list of messages is sought
        e.g.: for message in response.message_list(level=response.INFO):

        :param level: Minimum message level to include in the returned list (default: response.WARNING).
        :type level: integer
        :return: A list of messages with timestamps and similar fancy things
        :rtype: list
        """
        result = []
        for message in self.messages:
            if message['level'] in self.equal_or_greater_levels[self.level_names[level]]:
                result.append(message)
        return result


    #### Add a query_plan element
    def update_query_plan(self, qedge_key, provider, status, description, query=None):
        """Method to add or update an element of the query_plan.

        :param edge_key: query_graph qedge key (e.g. 'e00').
        :type edge_key: str
        :param provider: knowledge provider name (e.g. 'infores:molepro).
        :type level: int
        :param status: status the KP (one of: Skipped, Waiting, Timed out, Error, Done).
        :type code: str
        :param description: Description of the result (see below for examples).
        :type code: str
        :param query: Optional query dict that is sent to the referenced KP.
        :type code: dict
        """

        """
            Suggested description lines:
                Skipped: does not support predicate 'biolink:physically_interacts_with'
                Query with 12 CURIEs sent: waiting for response
                Query with 4 CURIEs timed out after 30 seconds
                Query with 4 CURIEs returned ERROR after 1 seconds (HTTP 500)
                Query returned 89 results
        """

        if qedge_key not in self.query_plan['qedge_keys']:
            self.query_plan['qedge_keys'][qedge_key] = {}
        if provider == 'edge_properties':
            if provider not in self.query_plan['qedge_keys'][qedge_key]:
                self.query_plan['qedge_keys'][qedge_key][provider] = {}
            self.query_plan['qedge_keys'][qedge_key][provider][status] = description
        else:
            if provider not in self.query_plan['qedge_keys'][qedge_key]:
                self.query_plan['qedge_keys'][qedge_key][provider] = { 'status': status, 'description': description, 'query': query }
            else:
                self.query_plan['qedge_keys'][qedge_key][provider]['status'] = status
                self.query_plan['qedge_keys'][qedge_key][provider]['description'] = description
                if query is not None:
                    self.query_plan['qedge_keys'][qedge_key][provider]['query'] = query
        self.query_plan['counter'] += 1


##########################################################################################
import unittest
class ResponseTests(unittest.TestCase):

    def setUp(self):
        self.response = ARAXResponse()
        self.response.debug('And we are off')
        self.response.info('So far so good')
        self.response.warning('This does not look good')
        self.response.error('Bad news, Pal', code='BadNewsError')

    def test_n_errors(self):
        self.assertEqual(self.response.n_errors, 1)

    def test_n_warnings(self):
        self.assertEqual(self.response.n_warnings, 1)

    def test_n_messages(self):
        self.assertEqual(self.response.n_messages, 4)

    def test_messages_list(self):
        self.assertEqual(len(self.response.messages_list(level=self.response.DEBUG)), 4)

    def test_status(self):
        self.assertEqual(self.response.status, 'ERROR')

    def test_show(self):
        self.assertGreater(len(self.response.show(level=self.response.INFO)), 285)


##########################################################################################
def main():

    # ### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='Command line interface to the Response class. Runs tests when run without the --example=N flag')
    argparser.add_argument('--verbose', action='count', help='If set, print out messages to STDERR as they are generated' )
    argparser.add_argument('--example', type=int, help='Specify an example to run instead of unit tests (use --example=1)')
    params = argparser.parse_args()

    #### If no example was specified, run the unit tests
    if params.example is None:
        unittest.main()
        return

    #### Otherwise, we will run an example

    # ### Set verbosity
    # ### By default, all messages are not written out immediately, but just saved for later
    # ### Set class variable 'output' to STDERR or STDOUT to also write messages there
    # ### This is a **class** variable, so it applies to all instances of response objects!
    if params.verbose is not None:
        ARAXResponse.output = 'STDERR'

    #### Run a nice little example
    #### Create an Response object
    response = ARAXResponse()
    import json

    #### Set some messages
    response.debug('And we are off')
    response.info('So far so good')
    response.warning('This does not look good')
    response.error('Bad news, Pal', code='BadNewsError')

    #### Example for
    if params.example == 2:
        response.update_query_plan('e00', 'infores:molepro', 'Skipped', "KP does not support predicate 'biolink:physically_interacts_with'")
        response.update_query_plan('e00', 'infores:rtx-kg2', 'Done', "Query returned 89 results")
        response.update_query_plan('e00', 'infores:genetics-data-provider', 'Waiting', "Query with 12 CURIEs sent: waiting for response")
        print(json.dumps(response.query_plan,sort_keys=True,indent=2))
        return

    #### Show the resulting object including logged events at INFO or greater
    print(response.show(level=response.INFO))

    #### Request and print the full messages list at DEBUG and greater
    print("Messages list:")
    print(json.dumps(response.messages_list(level=response.DEBUG),sort_keys=True,indent=2))


if __name__ == "__main__": main()
