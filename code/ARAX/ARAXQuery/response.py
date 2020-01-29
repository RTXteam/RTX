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

    #### Output all logging to STDERR as well as save it for later
    #### By default, they are not written out, but just saved for later
    #### This is a **class** variable, so applies to all instances of response objects!
    Response.output = 'STDERR'

    #### Set some messages
    response.debug('And we are off')
    response.info('So far so good')
    response.warning('This does not look good')
    response.error('Bad news, Pal')

    #### Show the resulting object including logged events at INFO or greater
    print(response.show(level=response.INFO))

    #### Request and print the full messages list at DEBUG and greater
    print("Messages list:")
    print(response.messages_list(level=response.DEBUG))


if __name__ == "__main__": main()
