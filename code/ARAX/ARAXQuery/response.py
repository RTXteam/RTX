#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re


class Response:

    #### Class variables
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    level_names = { 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR' }
    output = None

    #### Constructor
    def __init__(self, status='OK', logging_level=WARNING, error_code='OK', message='Normal completion'):
        self.status = status
        self.logging_level = logging_level
        self.error_code = error_code
        self.message = message
        self.messages = []
        self.n_messages = 0
        self.n_errors = 0
        self.n_warnings = 0
        self.data = {}

    #### Define attribute status
    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, status: str):
        self._status = status


    #### Define attribute logging_level
    @property
    def logging_level(self) -> str:
        return self._logging_level

    @logging_level.setter
    def logging_level(self, logging_level: str):
        self._logging_level = logging_level


    #### Define attribute error_code
    @property
    def error_code(self) -> str:
        return self._error_code

    @error_code.setter
    def error_code(self, error_code: str):
        self._error_code = error_code


    #### Define attribute message
    @property
    def message(self) -> str:
        return self._message

    @message.setter
    def message(self, message: str):
        self._message = message


    #### Define attribute n_errors
    @property
    def n_errors(self) -> int:
        return self._n_errors

    @n_errors.setter
    def n_errors(self, n_errors: int):
        self._n_errors = n_errors


    #### Define attribute n_warnings
    @property
    def n_warnings(self) -> int:
        return self._n_warnings

    @n_warnings.setter
    def n_warnings(self, n_warnings: int):
        self._n_warnings = n_warnings


    #### Define attribute n_messages
    @property
    def n_messages(self) -> int:
        return self._n_messages

    @n_messages.setter
    def n_messages(self, n_messages: int):
        self._n_messages = n_messages


    #### Define attribute messages
    @property
    def messages(self) -> list:
        return self._messages

    @messages.setter
    def messages(self, messages: list):
        self._messages = messages


    #### Define attribute data
    @property
    def data(self) -> dict:
        return self._data

    @data.setter
    def data(self, data: dict):
        self._data = data


    #### Add a debugging message
    def debug(self, message):
        self.add_message( message, self.DEBUG )


    #### Add an info message
    def info(self, message):
        self.add_message( message, self.INFO )


    #### Add a warning message
    def warning(self, message):
        self.add_message( message, self.WARNING )
        self.n_warnings += 1


    #### Add an error message
    def error(self, message, error_code='UnknownError'):
        self.add_message( message, self.ERROR )
        self.n_errors += 1
        self.status = 'ERROR'
        self.error_code = error_code
        self.message = message


    #### Add a message
    def add_message(self, message, message_level):
        self.messages.append( { 'level': message_level, 'message': message } )
        self.n_messages += 1
        if self.output is not None:
            if self.output == 'STDOUT':
                print(f"{self.level_names[message_level]}: {message}")
            if self.output == 'STDERR':
                eprint(f"{self.level_names[message_level]}: {message}")

    #### Merge a new response into an existing response
    def merge(self, response_to_merge):
        self.n_messages += response_to_merge.n_messages
        self.n_errors += response_to_merge.n_errors
        self.n_warnings += response_to_merge.n_warnings
        for message in response_to_merge.messages:
            self.messages.append( { 'level': message['level'], 'message': message['message'] } )
        if response_to_merge.status != 'OK':
            self.status = response_to_merge.status
            self.error_code = response_to_merge.error_code
            self.message = response_to_merge.message


    #### Return a text summary of the current state of the Response
    def show(self, level=WARNING):
        buffer = f"Response:\n"
        buffer += f"  status: {self.status}\n"
        buffer += f"  n_errors: {self.n_errors}  n_warnings: {self.n_warnings}  n_messages: {self.n_messages}\n"
        if self.status != 'OK':
            buffer += f"  error_code: {self.error_code}   message: {self.message}\n"
        for message in self.messages:
            if message['level'] >= level:
                buffer += f"  - [{self.level_names[message['level']]}]: {message['message']}\n"
        return buffer


    #### Return the current list of messages as a formatted list
    def messages_list(self, level=WARNING):
        result = []
        for message in self.messages:
            if message['level'] >= level:
                result.append(f"{self.level_names[message['level']]}: {message['message']}")
        return result


##########################################################################################
def main():

    #### Create an Response object
    response = Response()
    Response.output = 'STDERR'

    #### Set some messages
    response.debug('And we are off')
    response.info('So far so good')
    response.warning('This does not look good')
    response.error('Bad news, Pal')

    #### Show the resulting object
    print(response.show(level=response.INFO))

    print("Messages list:")
    print(response.messages_list(level=response.DEBUG))

if __name__ == "__main__": main()
