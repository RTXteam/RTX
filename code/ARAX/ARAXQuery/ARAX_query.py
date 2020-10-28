#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import time
from datetime import datetime
import subprocess
import traceback
from collections import Counter
import numpy as np
import threading
import json
import uuid

from response import Response
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo
from actions_parser import ActionsParser
from ARAX_filter import ARAXFilter
from ARAX_resultify import ARAXResultify
from ARAX_query_graph_interpreter import ARAXQueryGraphInterpreter
from ARAX_messenger import ARAXMessenger
from ARAX_ranker import ARAXRanker

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.message import Message
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge
from swagger_server.models.previous_message_processing_plan import PreviousMessageProcessingPlan

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
from RTXConfiguration import RTXConfiguration

from swagger_server.models.message import Message
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering")
from ParseQuestion import ParseQuestion
from Q0Solution import Q0
#import ReasoningUtilities
from QueryGraphReasoner import QueryGraphReasoner

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback/")
from RTXFeedback import RTXFeedback


class ARAXQuery:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        

    def query_return_stream(self,query):

        main_query_thread = threading.Thread(target=self.asynchronous_query, args=(query,))
        main_query_thread.start()

        if self.response is None or "DONE" not in self.response.status:

            # Sleep until a response object has been created
            while self.response is None:
                time.sleep(0.1)

            i_message = 0
            n_messages = len(self.response.messages)

            while "DONE" not in self.response.status:
                n_messages = len(self.response.messages)
                while i_message < n_messages:
                    yield(json.dumps(self.response.messages[i_message])+"\n")
                    i_message += 1
                time.sleep(0.2)

            # #### If there are any more logging messages in the queue, send them first
            n_messages = len(self.response.messages)
            while i_message < n_messages:
                yield(json.dumps(self.response.messages[i_message])+"\n")
                i_message += 1

            # Remove the little DONE flag the other thread used to signal this thread that it is done
            self.response.status = re.sub('DONE,','',self.response.status)

            # Stream the resulting message back to the client
            yield(json.dumps(ast.literal_eval(repr(self.message)))+"\n")

        # Wait until both threads rejoin here and the return
        main_query_thread.join()
        return { 'DONE': True }


    def asynchronous_query(self,query):

        #### Define a new response object if one does not yet exist
        if self.response is None:
            self.response = Response()

        result = self.query(query)
        message = self.message
        if message is None:
            message = Message()
            self.message = message
        message.message_code = result.error_code
        message.code_description = result.message
        message.log = result.messages

        # Insert a little flag into the response status to denote that this thread is done
        self.response.status = f"DONE,{self.response.status}"
        return


    def query_return_message(self,query):

        result = self.query(query)
        message = self.message
        if message is None:
            message = Message()
            self.message = message
        message.message_code = result.error_code
        message.code_description = result.message
        message.log = result.messages
        return message


    def query(self,query):
        #### Define a default response
        response = Response()
        self.response = response
        #Response.output = 'STDERR'
        response.info(f"ARAXQuery launching on incoming Message")

        #### Determine a plan for what to do based on the input
        result = self.examine_incoming_query(query)
        if result.status != 'OK':
            return response
        query_attributes = result.data

        # #### If we have a query_graph in the input query
        if "have_query_graph" in query_attributes:

            # Then if there is also a processing plan, assume they go together. Leave the query_graph intact
            # and then will later execute the processing plan
            if "have_previous_message_processing_plan" in query_attributes:
                pass
            else:
                response.info(f"Found input query_graph. Interpreting it and generating ARAXi processing plan to answer it")
                interpreter = ARAXQueryGraphInterpreter()
                query['message'] = ARAXMessenger().from_dict(query['message'])
                result = interpreter.translate_to_araxi(query['message'])
                response.merge(result)
                if result.status != 'OK':
                    return response
                query['previous_message_processing_plan'] = {}
                query['previous_message_processing_plan']['processing_actions'] = result.data['araxi_commands']
                query_attributes['have_previous_message_processing_plan'] = True

            #response.info(f"Found input query_graph. Sending to the QueryGraphReasoner")
            #qgr = QueryGraphReasoner()
            #message = qgr.answer(query["message"]["query_graph"], TxltrApiFormat=True)
            ##self.log_query(query,message,'new')
            #rtxFeedback = RTXFeedback()
            #rtxFeedback.connect()
            #rtxFeedback.addNewMessage(message,query)
            #rtxFeedback.disconnect()
            #self.limit_message(message,query)
            #self.message = message
            #return response

        #### If we have a previous message processing plan, handle that
        if "have_previous_message_processing_plan" in query_attributes:
            response.info(f"Found input processing plan. Sending to the ProcessingPlanExecutor")
            result = self.executeProcessingPlan(query)
            return response

        #### Otherwise extract the id and the terms from the incoming parameters
        else:
            response.info(f"Found id and terms from canned query")
            id = query["message"]["query_type_id"]
            terms = query["message"]["terms"]

        #### Create an RTX Feedback management object
        response.info(f"Try to find a cached message for this canned query")
        rtxFeedback = RTXFeedback()
        rtxFeedback.connect()
        cachedMessage = rtxFeedback.getCachedMessage(query)

        #### If we can find a cached message for this query and this version of RTX, then return the cached message
        if ( cachedMessage is not None ):
            response.info(f"Loaded cached message for return")
            apiMessage = Message().from_dict(cachedMessage)
            rtxFeedback.disconnect()
            self.limit_message(apiMessage,query)

            if apiMessage.message_code is None:
                if apiMessage.result_code is not None:
                    apiMessage.message_code = apiMessage.result_code
                else:
                    apiMessage.message_code = "wha??"

            #self.log_query(query,apiMessage,'cached')
            self.message = apiMessage
            return response

        #### Still have special handling for Q0
        if id == 'Q0':
            response.info(f"Answering 'what is' question with Q0 handler")
            q0 = Q0()
            message = q0.answer(terms["term"],use_json=True)
            if 'original_question' in query["message"]:
              message.original_question = query["message"]["original_question"]
              message.restated_question = query["message"]["restated_question"]
            message.query_type_id = query["message"]["query_type_id"]
            message.terms = query["message"]["terms"]
            id = message.id
            #self.log_query(query,message,'new')
            rtxFeedback.addNewMessage(message,query)
            rtxFeedback.disconnect()
            self.limit_message(message,query)
            self.message = message
            return response

        #### Else call out to original solution scripts for an answer
        else:

            response.info(f"Entering legacy handler for a canned query")

            #### Use the ParseQuestion system to determine what the execution_string should be
            txltr = ParseQuestion()
            eprint(terms)
            command = "python3 " + txltr.get_execution_string(id,terms)

            #### Set CWD to the QuestioningAnswering area and then invoke from the shell the Q1Solution code
            cwd = os.getcwd()
            os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering")
            eprint(command)
            returnedText = subprocess.run( [ command ], stdout=subprocess.PIPE, shell=True )
            os.chdir(cwd)

            #### reformat the stdout result of the shell command into a string
            reformattedText = returnedText.stdout.decode('utf-8')
            #eprint(reformattedText)

            #### Try to decode that string into a message object
            try:
                #data = ast.literal_eval(reformattedText)
                data = json.loads(reformattedText)
                message = Message.from_dict(data)
                if message.message_code is None:
                    if message.result_code is not None:
                        message.message_code = message.result_code
                    else:
                        message.message_code = "wha??"

            #### If it fails, the just create a new Message object with a notice about the failure
            except:
                response.error("Error parsing the message from the reasoner. This is an internal bug that needs to be fixed. Unable to respond to this question at this time. The unparsable message was: " + reformattedText, error_code="InternalError551")
                return response

            #print(query)
            if 'original_question' in query["message"]:
                message.original_question = query["message"]["original_question"]
                message.restated_question = query["message"]["restated_question"]
            message.query_type_id = query["message"]["query_type_id"]
            message.terms = query["message"]["terms"]

            #### Log the result and return the Message object
            #self.log_query(query,message,'new')
            rtxFeedback.addNewMessage(message,query)
            rtxFeedback.disconnect()

            #### Limit message
            self.limit_message(message,query)
            self.message = message
            return response

        #### If the query type id is not triggered above, then return an error
        response.error(f"The specified query id '{id}' is not supported at this time", error_code="UnsupportedQueryTypeID")
        rtxFeedback.disconnect()
        return response



    def examine_incoming_query(self,query):

        response = self.response
        response.info(f"Examine input query for needed information for dispatch")
        #eprint(query)

        #### Check to see if there's a processing plan
        if "previous_message_processing_plan" in query:
            response.data["have_previous_message_processing_plan"] = 1

        #### Check to see if the pre-0.9.2 query_message has come through
        if "query_message" in query:
            response.error("Query specified 'query_message' instead of 'message', which is pre-0.9.2 style. Please update.", error_code="Pre0.9.2Query")
            return response

        #### Check to see if there's a query message to process
        if "message" in query:
            response.data["have_message"] = 1

            #### Check the query_type_id and terms to make sure there is information in both
            if "query_type_id" in query["message"] and query["message"]["query_type_id"] is not None:
                if "terms" in query["message"] is not None:
                    response.data["have_query_type_id_and_terms"] = 1
                else:
                    response.error("query_type_id was provided but terms is empty", error_code="QueryTypeIdWithoutTerms")
                    return response
            elif "terms" in query["message"] and query["message"]["terms"] is not None:
                response.error("terms hash was provided without a query_type_id", error_code="TermsWithoutQueryTypeId")
                return response

            #### Check if there is a query_graph
            if "query_graph" in query["message"] and query["message"]["query_graph"] is not None:
                response.data["have_query_graph"] = 1

            #### If there is both a query_type_id and a query_graph, then return an error
            if "have_query_graph" in response.data and "have_query_type_id_and_terms" in response.data:
                response.error("Message contains both a query_type_id and a query_graph, which is disallowed", error_code="BothQueryTypeIdAndQueryGraph")
                return response

        #### Check to see if there is at least a message or a previous_message_processing_plan
        if "have_message" not in response.data and "have_previous_message_processing_plan" not in response.data:
            response.error("No message or previous_message_processing_plan present in Query", error_code="NoQueryMessageOrPreviousMessageProcessingPlan")
            return response

        # #### FIXME Need to do more validation and tidying of the incoming message here or somewhere


        #### If we got this far, then everything seems to be good enough to proceed
        return response



    def limit_message(self,message,query):
        if "max_results" in query and query["max_results"] is not None:
            if message.results is not None:
                if len(message.results) > query["max_results"]:
                    del message.results[query["max_results"]:]
                    message.code_description += " (output is limited to "+str(query["max_results"]) + " results)"



    #### Given an input query with a processing plan, execute that processing plan on the input
    def executeProcessingPlan(self,inputEnvelope):
        response = self.response
        response.debug(f"Entering executeProcessingPlan")
        messages = []
        message = None

        # If there is already a message (perhaps with a query_graph) already in the query, preserve it
        if 'message' in inputEnvelope and inputEnvelope['message'] is not None:
            message = inputEnvelope['message']
            messages = [ message ]

        message_id = None
        query = None
        #### Pull out the main processing plan envelope
        envelope = PreviousMessageProcessingPlan.from_dict(inputEnvelope["previous_message_processing_plan"])

        #### Connect to the message store just once, even if we won't use it
        rtxFeedback = RTXFeedback()
        rtxFeedback.connect()

        #### Create a messenger object for basic message processing
        messenger = ARAXMessenger()

        #### If there are URIs provided, try to load them
        if envelope.previous_message_uris is not None:
            response.debug(f"Found previous_message_uris")
            for uri in envelope.previous_message_uris:
                response.debug(f"    messageURI={uri}")
                matchResult = re.match( r'http[s]://arax.ncats.io/.*api/rtx/.+/message/(\d+)',uri,re.M|re.I )
                if matchResult:
                    referenced_message_id = matchResult.group(1)
                    response.debug(f"Found local RTX identifier corresponding to respond_id {referenced_message_id}")
                    response.debug(f"Loading message_id {referenced_message_id}")
                    referenced_message = rtxFeedback.getMessage(referenced_message_id)
                    #eprint(type(message))
                    if not isinstance(referenced_message,tuple):
                        referenced_message = ARAXMessenger().from_dict(referenced_message)
                        response.debug(f"Original question was: {referenced_message.original_question}")
                        messages.append(referenced_message)
                        message_id = referenced_message_id
                        query = { "query_type_id": referenced_message.query_type_id, "restated_question": referenced_message.restated_question, "terms": referenced_message.terms }
                    else:
                        response.error(f"Unable to load message_id {referenced_message_id}", error_code="CannotLoadMessageById")
                        return response

        #### If there are one or more previous_messages embedded in the POST, process them
        if envelope.previous_messages is not None:
            response.debug(f"Received previous_messages")
            for uploadedMessage in envelope.previous_messages:
                response.debug(f"uploadedMessage is a "+str(uploadedMessage.__class__))
                if str(uploadedMessage.__class__) == "<class 'swagger_server.models.message.Message'>":
                    uploadedMessage = ARAXMessenger().from_dict(uploadedMessage)
                    messages.append(uploadedMessage)

                    if uploadedMessage.results:
                        pass
                        #if message["terms"] is None:
                        #    message["terms"] = { "dummyTerm": "giraffe" }
                        #if message["query_type_id"] is None:
                        #    message["query_type_id"] = "UnknownQ"
                        #if message["restated_question"] is None:
                        #    message["restated_question"] = "Unknown question"
                        #if message["original_question"] is None:
                        #    message["original_question"] = "Unknown question"

                        #query = { "query_type_id": message["query_type_id"], "restated_question": message["restated_question"], "original_question": message["original_question"], "terms": message["terms"] }
                    else:
                        #response.error(f"Uploaded message does not contain a results. May be the wrong format")
                        #return response
                        response.warning(f"There are no results in this uploaded message, but maybe that's okay")
                else:
                    response.error(f"Uploaded message is not of type Message. It is of type"+str(uploadedMessage.__class__))
                    return response

        #### Take different actions based on the number of messages we now have in hand
        n_messages = len(messages)
        if n_messages == 0:
            response.debug(f"No starting messages were referenced. Will start with a blank template Message")
            result = messenger.create_message()
            message = result.data['message']
        elif n_messages == 1:
            response.debug(f"A single Message is ready and in hand")
            message = messages[0]
        else:
            response.debug(f"Multiple Messages were uploaded or imported by reference. However, proper merging code has not been implmented yet! Will use just the first Message for now.")
            message = messages[0]

        #### Examine the options that were provided and act accordingly
        optionsDict = {}
        if envelope.options:
            response.debug(f"Processing options were provided, but these are not implemented at the moment and will be ignored")
            for option in envelope.options:
                response.debug(f"   option="+option)
                optionsDict[option] = 1


        #### If there are processing_actions, then fulfill those
        if envelope.processing_actions:
            response.debug(f"Found processing_actions")
            actions_parser = ActionsParser()
            result = actions_parser.parse(envelope.processing_actions)
            response.merge(result)
            if result.error_code != 'OK':
                return response

            #### Import the individual ARAX processing modules and process DSL commands
            from ARAX_expander import ARAXExpander
            from ARAX_overlay import ARAXOverlay
            from ARAX_filter_kg import ARAXFilterKG
            from ARAX_resultify import ARAXResultify
            from ARAX_filter_results import ARAXFilterResults
            expander = ARAXExpander()
            filter = ARAXFilter()
            overlay = ARAXOverlay()
            filter_kg = ARAXFilterKG()
            resultifier = ARAXResultify()
            filter_results = ARAXFilterResults()
            self.message = message

            #### Process each action in order
            action_stats = { }
            actions = result.data['actions']
            for action in actions:
                response.info(f"Processing action '{action['command']}' with parameters {action['parameters']}")
                nonstandard_result = False
                skip_merge = False

                # Catch a crash
                try:
                    if action['command'] == 'create_message':
                        result = messenger.create_message()
                        message = result.data['message']
                        self.message = message

                    elif action['command'] == 'fetch_message':
                        result = messenger.apply_fetch_message(message,action['parameters'])
                        message = messenger.message
                        self.message = message

                    elif action['command'] == 'add_qnode':
                        result = messenger.add_qnode(message,action['parameters'])

                    elif action['command'] == 'add_qedge':
                        result = messenger.add_qedge(message,action['parameters'])

                    elif action['command'] == 'expand':
                        result = expander.apply(message,action['parameters'], response=response)
                        skip_merge = True

                    elif action['command'] == 'filter':
                        result = filter.apply(message,action['parameters'])

                    elif action['command'] == 'resultify':
                        result = resultifier.apply(message, action['parameters'])

                    elif action['command'] == 'overlay':  # recognize the overlay command
                        result = overlay.apply(message, action['parameters'], response=response)
                        skip_merge = True

                    elif action['command'] == 'filter_kg':  # recognize the filter_kg command
                        result = filter_kg.apply(message, action['parameters'])

                    elif action['command'] == 'filter_results':  # recognize the filter_kg command
                        result = filter_results.apply(message, action['parameters'])

                    elif action['command'] == 'query_graph_reasoner':
                        response.info(f"Sending current query_graph to the QueryGraphReasoner")
                        qgr = QueryGraphReasoner()
                        message = qgr.answer(ast.literal_eval(repr(message.query_graph)), TxltrApiFormat=True)
                        self.message = message
                        nonstandard_result = True

                    elif action['command'] == 'return':
                        action_stats['return_action'] = action
                        break

                    elif action['command'] == 'rank_results':
                        response.info(f"Running experimental reranker on results")
                        try:
                            ranker = ARAXRanker()
                            #ranker.aggregate_scores(message, response=response)
                            ranker.aggregate_scores_dmk(message, response=response)
                        except Exception as error:
                            exception_type, exception_value, exception_traceback = sys.exc_info()
                            response.error(f"An uncaught error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UncaughtARAXiError")
                            return response

                    else:
                        response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
                        return response

                except Exception as error:
                    exception_type, exception_value, exception_traceback = sys.exc_info()
                    response.error(f"An uncaught error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UncaughtARAXiError")
                    return response

                #### Merge down this result and end if we're in an error state
                if nonstandard_result is False:
                    if not skip_merge:
                        response.merge(result)
                    if result.status != 'OK':
                        message.message_code = response.error_code
                        message.code_description = response.message
                        message.log = response.messages
                        return response

                #### Immediately after resultify, run the experimental ranker
                if action['command'] == 'resultify':
                    response.info(f"Running experimental reranker on results")
                    try:
                        ranker = ARAXRanker()
                        #ranker.aggregate_scores(message, response=response)
                        ranker.aggregate_scores_dmk(message, response=response)
                    except Exception as error:
                        exception_type, exception_value, exception_traceback = sys.exc_info()
                        response.error(f"An uncaught error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UncaughtARAXiError")
                        return response

            #### At the end, process the explicit return() action, or implicitly perform one
            return_action = { 'command': 'return', 'parameters': { 'message': 'true', 'store': 'true' } }
            if action is not None and action['command'] == 'return':
                return_action = action
                #### If an explicit one left out some parameters, set the defaults
                if 'store' not in return_action['parameters']:
                    return_action['parameters']['store'] == 'false'
                if 'message' not in return_action['parameters']:
                    return_action['parameters']['message'] == 'false'

            # Fill out the message with data
            message.message_code = response.error_code
            message.code_description = response.message
            message.log = response.messages
            if message.query_options is None:
                message.query_options = {}
            message.query_options['processing_actions'] = envelope.processing_actions

            # If store=true, then put the message in the database
            if return_action['parameters']['store'] == 'true':
                response.debug(f"Storing resulting Message")
                message_id = rtxFeedback.addNewMessage(message, query)
                
            #### If asking for the full message back
            if return_action['parameters']['message'] == 'true':
                response.info(f"Processing is complete. Transmitting resulting Message back to client.")
                return response

            #### Else just the id is returned
            else:
                if message_id is None:
                    message_id = 0
                response.info(f"Processing is complete. Resulting Message id is {message_id} and is available to fetch via /message endpoint.")
                return( { "status": 200, "message_id": str(message_id), "n_results": message.n_results, "url": "https://arax.ncats.io/api/rtx/v1/message/"+str(message_id) }, 200)



##################################################################################################
def stringify_dict(inputDict):
    outString = "{"
    for key,value in sorted(inputDict.items(), key=lambda t: t[0]):
        if outString != "{":
            outString += ","
        outString += "'"+str(key)+"':'"+str(value)+"'"
    outString += "}"
    return(outString)


##################################################################################################
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='Primary interface to the ARAX system')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('example_number', type=int, help='Integer number of the example query to execute')
    params = argparser.parse_args()

    #### Set verbose
    verbose = params.verbose
    if verbose is None: verbose = 1

    #### Create a response and ARAXQuery
    response = Response()
    araxq = ARAXQuery()

    #### For debugging purposes, you can send all messages as they are logged to STDERR
    #Response.output = 'STDERR'

    #### Set the query based on the supplied example_number
    if params.example_number == 1:
        query = { 'message': { 'query_type_id': 'Q0', 'terms': { 'term': 'lovastatin' } } }
        #query = { "query_type_id": "Q0", "terms": { "term": "lovastatin" }, "bypass_cache": "true" }  # Use bypass_cache if the cache if bad for this question
    elif params.example_number == 2:
        query = { "message": { "query_graph": { "edges": [
                    { "id": "qg2", "source_id": "qg1", "target_id": "qg0", "type": "physically_interacts_with" }
                ],
                "nodes": [
                    { "id": "qg0", "name": "acetaminophen", "curie": "CHEMBL.COMPOUND:CHEMBL112", "type": "chemical_substance" },
                    { "id": "qg1", "name": None, "desc": "Generic protein", "curie": None, "type": "protein" }
                ] } } }
    elif params.example_number == 3:  # FIXME: Don't fix me, this is our planned demo example 1.
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=acetaminophen, id=n0)",
            "add_qnode(type=protein, id=n1)",
            "add_qedge(source_id=n0, target_id=n1, id=e0)",
            "expand(edge_id=e0)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=10)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 301:  # Variant of 3 with NGD
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=acetaminophen, id=n0)",
            "add_qnode(type=protein, id=n1)",
            "add_qedge(source_id=n0, target_id=n1, id=e0)",
            "expand(edge_id=e0)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n0, target_qnode_id=n1)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 4:
        query = { "previous_message_processing_plan": { "processing_actions": [
            "add_qnode(name=hypertension, id=n00)",
            "add_qnode(type=protein, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "resultify()",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 5:  # test overlay with ngd: hypertension->protein
        query = { "previous_message_processing_plan": { "processing_actions": [
            "add_qnode(name=hypertension, id=n00)",
            "add_qnode(type=protein, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=compute_ngd)",
            "resultify()",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 6:  # test overlay
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:12384, id=n00)",
            "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=has_phenotype)",
            "expand(edge_id=e00, kp=ARAX/KG2)",
            #"overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
            #"overlay(action=overlay_clinical_info, chi_square=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
            #"overlay(action=compute_ngd, default_value=inf)",
            #"overlay(action=compute_ngd, virtual_relation_label=NGD1, source_qnode_id=n00, target_qnode_id=n01)",
            "filter(maximum_results=2)",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 7:  # stub to test out the compute_jaccard feature
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",  # parkinsons
            "add_qnode(type=protein, is_set=True, id=n01)",
            "add_qnode(type=chemical_substance, is_set=false, id=n02)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 8:  # to test jaccard with known result  # FIXME:  ERROR: Node DOID:8398 has been returned as an answer for multiple query graph nodes (n00, n02)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:8398, id=n00)",  # osteoarthritis
            "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
            "add_qnode(type=disease, is_set=true, id=n02)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 9:  # to test jaccard with known result. This check's out by comparing with match p=(s:disease{id:"DOID:1588"})-[]-(r:protein)-[]-(:chemical_substance) return p and manually counting
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:1588, id=n00)",
            "add_qnode(type=protein, is_set=True, id=n01)",
            "add_qnode(type=chemical_substance, is_set=true, id=n02)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 10:  # test case of drug prediction
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:1588, id=n00)",
            "add_qnode(type=chemical_substance, is_set=false, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=predict_drug_treats_disease)",
            "resultify(ignore_edge_direction=True)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 11:  # test overlay with overlay_clinical_info, paired_concept_frequency via COHD
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:0060227, id=n00)",  # Adam's oliver
            "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=has_phenotype)",
            "expand(edge_id=e00)",
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
            #"overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_relation_label=COHD1, source_qnode_id=n00, target_qnode_id=n01)",
            "filter(maximum_results=2)",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 12:  # dry run of example 2 # FIXME NOTE: this is our planned example 2 (so don't fix, it's just so it's highlighted in my IDE)
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(name=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",  # can be removed, but shows we can filter by Knowledge provider
            "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 13:  # add pubmed id's
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:1227, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=add_node_pmids, max_num=15)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 14:  # test
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:8712, id=n00)",
            "add_qnode(type=phenotypic_feature, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, is_set=true, id=n02)",
            "add_qnode(type=protein, is_set=true, id=n03)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=has_phenotype)",  # phenotypes of disease
            "add_qedge(source_id=n02, target_id=n01, id=e01, type=indicated_for)",  # only look for drugs that are indicated for those phenotypes
            "add_qedge(source_id=n02, target_id=n03, id=e02)",  # find proteins that interact with those drugs
            "expand(edge_id=[e00, e01, e02])",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",  # only look at drugs that target lots of phenotypes
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.06, remove_connected_nodes=t, qnode_id=n02)",  # remove edges and drugs that connect to few phenotypes
            #"filter_kg(action=remove_edges_by_type, edge_type=J1, remove_connected_nodes=f)",
            ##"overlay(action=overlay_clinical_info, paired_concept_frequency=true)",  # overlay with COHD information
            #"overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n02)",  # overlay drug->disease virtual edges with COHD information
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=paired_concept_frequency, direction=below, threshold=0.0000001, remove_connected_nodes=t, qnode_id=n02)",  # remove drugs below COHD threshold
            #"overlay(action=compute_jaccard, start_node_id=n01, intermediate_node_id=n02, end_node_id=n03, virtual_relation_label=J2)",  # look at proteins that share many/any drugs in common with the phenotypes
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.001, remove_connected_nodes=t, qnode_id=n03)",
            #"filter_kg(action=remove_edges_by_type, edge_type=J2, remove_connected_nodes=f)",
            #"filter_kg(action=remove_edges_by_type, edge_type=C1, remove_connected_nodes=f)",
            ##"overlay(action=compute_ngd)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 15:  # FIXME NOTE: this is our planned example 3 (so don't fix, it's just so it's highlighted in my IDE)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:9406, id=n00)",  # hypopituitarism
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",  # look for all drugs associated with this disease (29 total drugs)
            "add_qnode(type=protein, id=n02)",   # look for proteins associated with these diseases (240 total proteins)
            "add_qedge(source_id=n00, target_id=n01, id=e00)",  # get connections
            "add_qedge(source_id=n01, target_id=n02, id=e01)",  # get connections
            "expand(edge_id=[e00,e01])",  # expand the query graph
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",  # Look in COHD to find which drug are being used to treat this disease based on the log ratio of expected frequency of this drug being used to treat a disease, vs. the observed number of times it’s used to treat this disease
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_id=n01)",   # concentrate only on those drugs that are more likely to be treating this disease than expected
            "filter_kg(action=remove_orphaned_nodes, node_type=protein)",  # remove proteins that got disconnected as a result of this filter action
            "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",   # use normalized google distance to find how frequently the protein and the drug are mentioned in abstracts
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n02)",   # remove proteins that are not frequently mentioned together in PubMed abstracts
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 1515:  # Exact duplicate of ARAX_Example3.ipynb
        query = {"previous_message_processing_plan": {"processing_actions": [
            "add_qnode(curie=DOID:9406, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qnode(type=protein, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_id=n01)",
            "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n02)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 16:  # To test COHD
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:8398, id=n00)",
            #"add_qnode(name=DOID:1227, id=n00)",
            "add_qnode(type=phenotypic_feature, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, type=has_phenotype, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=overlay_clinical_info, chi_square=true)",
            "resultify()",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 17:  # Test resultify #FIXME: this returns a single result instead of a list (one for each disease/phenotype found)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:731, id=n00, type=disease, is_set=false)",
            "add_qnode(type=phenotypic_feature, is_set=false, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            'resultify(ignore_edge_direction=true)',
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 18:  # test removing orphaned nodes
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:9406, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qnode(type=protein, is_set=true, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00, e01])",
            "filter_kg(action=remove_edges_by_type, edge_type=physically_interacts_with, remove_connected_nodes=f)",
            "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 19:  # Let's see what happens if you ask for a node in KG2, but not in KG1 and try to expand
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=UMLS:C1452002, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=interacts_with)",
            "expand(edge_id=e00)",
            "return(message=true, store=false)"
        ]}}  # returns response of "OK" with the info: QueryGraphReasoner found no results for this query graph
    elif params.example_number == 20:  # Now try with KG2 expander
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=UMLS:C1452002, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=interacts_with)",
            "expand(edge_id=e00, kp=ARAX/KG2)",
            "return(message=true, store=false)"
        ]}}  # returns response of "OK" with the info: QueryGraphReasoner found no results for this query graph
    elif params.example_number == 101:  # test of filter results code
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(name=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=d, max_results=15)",
            #"filter_results(action=sort_by_edge_count, direction=a)",
            #"filter_results(action=limit_number_of_results, max_results=5)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 102:  # add pubmed id's
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:1227, id=n00)",
            "add_qnode(type=chemical_substance, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 103:  # add pubmed id's
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:1227, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=add_node_pmids, max_num=15)",
            "filter_kg(action=remove_nodes_by_property, node_property=uri, property_value=https://www.ebi.ac.uk/chembl/compound/inspect/CHEMBL2111164)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 1212:  # dry run of example 2 with the machine learning model
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",  # can be removed, but shows we can filter by Knowledge provider
            "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",  # overlay by probability that the drug treats the disease
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=probability_drug_treats, direction=descending, max_results=15)",  # filter by the probability that the drug treats the disease. cilnidipine prob=0.8976650309881645 which is the 9th highest (so top 10)
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 201:  # KG2 version of demo example 1 (acetaminophen)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
            "add_qnode(id=n01, type=protein, is_set=true)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "expand(edge_id=e00, kp=ARAX/KG2)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 202:  # KG2 version of demo example 2 (Parkinson's)
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(name=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=molecularly_interacts_with)",  # for KG2
            #"add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",  # for KG1
            "expand(edge_id=[e00,e01], kp=ARAX/KG2)",  # for KG2
            #"expand(edge_id=[e00,e01], kp=ARAX/KG1)",  # for KG1
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",  # seems to work just fine
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.008, remove_connected_nodes=t, qnode_id=n02)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 203:  # KG2 version of demo example 3 (but using idiopathic pulmonary fibrosis)
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            #"add_qnode(id=n00, curie=DOID:0050156)",  # idiopathic pulmonary fibrosis
            "add_qnode(curie=DOID:9406, id=n00)",  # hypopituitarism, original demo example
            "add_qnode(id=n01, type=chemical_substance, is_set=true)",
            "add_qnode(id=n02, type=protein)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "add_qedge(id=e01, source_id=n01, target_id=n02)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=2, remove_connected_nodes=t, qnode_id=n01)",
            "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 2033:  # KG2 version of demo example 3 (but using idiopathic pulmonary fibrosis), with all decorations
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=DOID:0050156)",  # idiopathic pulmonary fibrosis
            #"add_qnode(curie=DOID:9406, id=n00)",  # hypopituitarism, original demo example
            "add_qnode(id=n01, type=chemical_substance, is_set=true)",
            "add_qnode(id=n02, type=protein)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "add_qedge(id=e01, source_id=n01, target_id=n02)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=0, remove_connected_nodes=t, qnode_id=n01)",
            #"filter_kg(action=remove_orphaned_nodes, node_type=protein)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 222:  # Simple BTE query
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=NCBIGene:1017)",  # CDK2
            "add_qnode(id=n01, type=chemical_substance, is_set=True)",
            "add_qedge(id=e00, source_id=n01, target_id=n00)",
            "expand(edge_id=e00, kp=BTE)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 233:  # KG2 version of demo example 1 (acetaminophen)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
            "add_qnode(id=n01, type=protein, is_set=true)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "expand(edge_id=e00, kp=ARAX/KG2)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=https://pharos.nih.gov)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 300:  # KG2 version of demo example 1 (acetaminophen)
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
            "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=jaccard_index, type=std, remove_connected_nodes=t, qnode_id=n02)",
            #"filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",  # can be removed, but shows we can filter by Knowledge provider
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 690:  # test issue 690
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:14330, id=n00)",
            "add_qnode(type=not_a_real_type, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=molecularly_interacts_with)",
            "expand(edge_id=[e00,e01], continue_if_no_results=true)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6231:  # chunyu testing #623, all nodes already in the KG and QG
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521, type=chemical_substance)",
            "add_qnode(id=n01, is_set=true, type=protein)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "add_qnode(id=n02, type=biological_process)",
            "add_qedge(id=e01, source_id=n01, target_id=n02)",
            "expand(edge_id=[e00, e01], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n01, virtual_relation_label=FET, target_qnode_id=n02, cutoff=0.05)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6232:  # chunyu testing #623, this should return the 10 smallest FET p-values and only add the virtual edge with top 10 FET p-values
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521, type=chemical_substance)",
            "add_qnode(id=n01, is_set=true, type=protein)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "add_qnode(id=n02, type=biological_process)",
            "add_qedge(id=e01, source_id=n01, target_id=n02)",
            "expand(edge_id=[e00, e01], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n01, virtual_relation_label=FET, target_qnode_id=n02, top_n=10)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6233:  # chunyu testing #623, this DSL tests the FET module based on (source id - involved_in - target id) and only decorate/add virtual edge with pvalue<0.05
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521, type=chemical_substance)",
            "add_qnode(id=n01, is_set=true, type=protein)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "add_qnode(id=n02, type=biological_process)",
            "add_qedge(id=e01, source_id=n01, target_id=n02, type=involved_in)",
            "expand(edge_id=[e00, e01], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n01, virtual_relation_label=FET, target_qnode_id=n02, rel_edge_id=e01, cutoff=0.05)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6234:  # chunyu testing #623, nodes not in the KG and QG. This should throw an error initially. In the future we might want to add these nodes.
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521, type=chemical_substance)",
            "add_qnode(id=n01, type=protein)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "expand(edge_id=[e00], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n01, virtual_relation_label=FET, target_qnode_id=n02, cutoff=0.05)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6235:  # chunyu testing #623, this is a two-hop sample. First, find all edges between DOID:14330 and proteins and then filter out the proteins with connection having pvalue>0.001 to DOID:14330. Second, find all edges between proteins and chemical_substances and then filter out the chemical_substances with connection having pvalue>0.005 to proteins
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00, type=disease)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=e01, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6236:  # chunyu testing #623, this is a three-hop sample: DOID:14330 - protein - (physically_interacts_with) - chemical_substance - phenotypic_feature
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00, type=disease)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n01)",
            "add_qnode(type=chemical_substance, is_set=true, id=n02)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=e01, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_id=n02)",
            "add_qnode(type=phenotypic_feature, id=n03)",
            "add_qedge(source_id=n02, target_id=n03, id=e02)",
            "expand(edge_id=e02, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n02, target_qnode_id=n03, virtual_relation_label=FET3)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6237:  # chunyu testing #623, this is a four-hop sample: CHEMBL521 - protein - biological_process - protein - disease
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL521, type=chemical_substance)",
            "add_qnode(id=n01, is_set=true, type=protein)",
            "add_qedge(id=e00, source_id=n00, target_id=n01)",
            "expand(edge_id=e00, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n00, target_qnode_id=n01, virtual_relation_label=FET1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_id=n01)",
            "add_qnode(type=biological_process, is_set=true, id=n02)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=e01, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n01, target_qnode_id=n02, virtual_relation_label=FET2)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_id=n02)",
            "add_qnode(type=protein, is_set=true, id=n03)",
            "add_qedge(source_id=n02, target_id=n03, id=e02)",
            "expand(edge_id=e02, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n02, target_qnode_id=n03, virtual_relation_label=FET3)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_id=n03)",
            "add_qnode(type=disease, id=n04)",
            "add_qedge(source_id=n03, target_id=n04, id=e03)",
            "expand(edge_id=e03, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n03, target_qnode_id=n04, virtual_relation_label=FET4)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 7680:  # issue 768 test all but jaccard, uncomment any one you want to test
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:1588, id=n0)",
            "add_qnode(type=chemical_substance, id=n1)",
            "add_qedge(source_id=n0, target_id=n1, id=e0)",
            "expand(edge_id=e0)",
            #"overlay(action=predict_drug_treats_disease)",
            #"overlay(action=predict_drug_treats_disease, source_qnode_id=n1, target_qnode_id=n0, virtual_relation_label=P1)",
            #"overlay(action=overlay_clinical_info,paired_concept_frequency=true)",
            #"overlay(action=overlay_clinical_info,observed_expected_ratio=true)",
            #"overlay(action=overlay_clinical_info,chi_square=true)",
            #"overlay(action=overlay_clinical_info,paired_concept_frequency=true, source_qnode_id=n0, target_qnode_id=n1, virtual_relation_label=CP1)",
            #"overlay(action=overlay_clinical_info,observed_expected_ratio=true, source_qnode_id=n0, target_qnode_id=n1, virtual_relation_label=OE1)",
            #"overlay(action=overlay_clinical_info,chi_square=true, source_qnode_id=n0, target_qnode_id=n1, virtual_relation_label=C1)",
            "overlay(action=fisher_exact_test, source_qnode_id=n0, target_qnode_id=n1, virtual_relation_label=FET)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=15)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 7681:  # issue 768 with jaccard
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",  # parkinsons
            "add_qnode(type=protein, is_set=True, id=n01)",
            "add_qnode(type=chemical_substance, is_set=False, id=n02)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=15)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 7200:  # issue 720, example 2
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
            #"filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
            #"overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 885:
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:11830, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=molecularly_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG2)",
            # overlay a bunch of clinical info
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C1)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C2)",
            "overlay(action=overlay_clinical_info, chi_square=true, source_qnode_id=n00, target_qnode_id=n02, virtual_relation_label=C3)",
            # return results
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 887:
        query = {"previous_message_processing_plan": {"processing_actions": [
            "add_qnode(name=DOID:9406, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qnode(type=protein, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n01)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_id=n01)",
            "filter_kg(action=remove_orphaned_nodes, node_type=protein)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n01, target_qnode_id=n02)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n02)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 892:  # drug disease prediction with BTE
        query = {"previous_message_processing_plan": {"processing_actions": [
            "add_qnode(curie=DOID:11830, type=disease, id=n00)",
            "add_qnode(type=gene, curie=[UniProtKB:P39060, UniProtKB:O43829, UniProtKB:P20849], is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(kp=BTE)",
            "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 8922:  # drug disease prediction with BTE and KG2
        query = {"previous_message_processing_plan": {"processing_actions": [
            "add_qnode(curie=DOID:11830, id=n0, type=disease)",
            "add_qnode(type=chemical_substance, id=n1)",
            "add_qedge(source_id=n0, target_id=n1, id=e1)",
            "expand(edge_id=e1, kp=ARAX/KG2)",
            "expand(edge_id=e1, kp=BTE)",
            #"overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
            #"overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            #"overlay(action=overlay_clinical_info, chi_square=true)",
            "overlay(action=predict_drug_treats_disease)",
            #"overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            #"filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 8671:  # test_one_hop_kitchen_sink_BTE_1
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:11830, id=n0, type=disease)",
            "add_qnode(type=chemical_substance, id=n1)",
            "add_qedge(source_id=n0, target_id=n1, id=e1)",
            # "expand(edge_id=e00, kp=ARAX/KG2)",
            "expand(edge_id=e1, kp=BTE)",
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            "overlay(action=overlay_clinical_info, chi_square=true)",
            "overlay(action=predict_drug_treats_disease)",
            "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 8672:  # test_one_hop_based_on_types_1
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:11830, id=n00, type=disease)",
            "add_qnode(type=chemical_substance, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00, kp=ARAX/KG2)",
            "expand(edge_id=e00, kp=BTE)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            "overlay(action=predict_drug_treats_disease)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=0.75, remove_connected_nodes=true, qnode_id=n01)",
            "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 8673:  # test_one_hop_based_on_types_1
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=MONDO:0001475, id=n00, type=disease)",
            "add_qnode(type=protein, id=n01, is_set=true)",
            "add_qnode(type=chemical_substance, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=molecularly_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG2, continue_if_no_results=true)",
            #- expand(edge_id=[e00,e01], kp=BTE, continue_if_no_results=true)",
            "expand(edge_id=e00, kp=BTE, continue_if_no_results=true)",
            #- expand(edge_id=e00, kp=GeneticsKP, continue_if_no_results=true)",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_relation_label=J1)",
            "overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)",
            "overlay(action=overlay_clinical_info, chi_square=true, virtual_relation_label=C1, source_qnode_id=n00, target_qnode_id=n02)",
            #"overlay(action=compute_ngd, virtual_relation_label=N1, source_qnode_id=n00, target_qnode_id=n01)",
            #"overlay(action=compute_ngd, virtual_relation_label=N2, source_qnode_id=n00, target_qnode_id=n02)",
            #"overlay(action=compute_ngd, virtual_relation_label=N3, source_qnode_id=n01, target_qnode_id=n02)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=100)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 9999:
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=acetaminophen, id=n0)",
            "add_qnode(type=protein, id=n1)",
            "add_qedge(source_id=n0, target_id=n1, id=e0)",
            "expand(edge_id=e0)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=100)",
            "return(message=true, store=json)",
        ]}}
    else:
        eprint(f"Invalid test number {params.example_number}. Try 1 through 17")
        return

    if 0:
        message = araxq.query_return_message(query)
        print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
        return

    result = araxq.query(query)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response

    #### Retrieve the Translator Message from the result
    message = araxq.message

    #### Print out the message that came back
    #print(response.show(level=Response.DEBUG))
    #print("Returned message:\n")
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.query_graph)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.nodes)), sort_keys=True, indent=2))
    print(json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2))
    #print(response.show(level=Response.DEBUG))

    print(response.show(level=Response.DEBUG))

    print(f"Number of results: {len(message.results)}")

    #print(f"Drugs names in the KG: {[x.name for x in message.knowledge_graph.nodes if 'chemical_substance' in x.type or 'drug' in x.type]}")

    #print(f"Essence names in the answers: {[x.essence for x in message.results]}")
    print("Results:")
    for result in message.results:
        confidence = result.confidence
        if confidence is None:
            confidence = 0.0
        print("  -" + '{:6.3f}'.format(confidence) + f"\t{result.essence}")

    #print(json.dumps(ast.literal_eval(repr(message.results[0])), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.results)), sort_keys=True, indent=2))
    #print(set.union(*[set(x.qg_id for x in r.edge_bindings if x.qg_id.startswith('J')) for r in message.results]))

    # look for qg id's in edge_bindings in results
    if False:
        try:
            print(f"Result qg_id's in results: {set.union(*[set(x.qg_id for x in r.edge_bindings) for r in message.results])}")
        except:
            pass

    # Check edge attributes
    if True:
        vals = []
        num_edges_show = 2
        num_edges_shown = 0
        #attribute_of_interest = 'jaccard_index'
        #attribute_of_interest = 'observed_expected_ratio'
        #attribute_of_interest = 'ngd'
        #attribute_of_interest = 'normalized_google_distance'
        #attribute_of_interest = 'chi_square'
        #attribute_of_interest = 'paired_concept_frequency'
        #attribute_of_interest = 'probability'
        attribute_of_interest = 'probability_treats'
        all_attribute_names = set()
        for edge in message.knowledge_graph.edges:
            if hasattr(edge, 'edge_attributes') and edge.edge_attributes and len(edge.edge_attributes) >= 1:
                for edge_attribute in edge.edge_attributes:
                    all_attribute_names.add(edge_attribute.name)
                    if edge_attribute.name == attribute_of_interest:
                        if num_edges_shown < num_edges_show:
                            print(json.dumps(ast.literal_eval(repr(edge)), sort_keys=True, indent=2))
                            num_edges_shown += 1
                        #for attr in edge.edge_attributes:
                        #    vals.append((attr.name, attr.value))
                        vals.append((edge_attribute.name, float(edge_attribute.value)))  # FIXME: some edge_attributes are floats, others are strings, object model weirdness
                    elif attribute_of_interest == all:
                        print(json.dumps(ast.literal_eval(repr(edge)), sort_keys=True, indent=2))
        print(f"All edge attribute names: {all_attribute_names}")
        if vals:
            print(f"number of edges with attribute {attribute_of_interest}: {len(vals)}")
            print(f"Mean of attribute {attribute_of_interest}: {np.mean([x[1] for x in vals])}")
            print(f"Median of attribute {attribute_of_interest}: {np.median([x[1] for x in vals])}")
            print(f"Max of attribute {attribute_of_interest}: {np.max([x[1] for x in vals])}")
            print(f"Min of attribute {attribute_of_interest}: {np.min([x[1] for x in vals])}")
        # show all the values of the edge attributes
        #print(sorted(Counter(vals).items(), key=lambda x:float(x[0][1])))

    # check for edges from a given drug
    if False:
        for edge in message.knowledge_graph.edges:
            if edge.source_id == "CHEMBL.COMPOUND:CHEMBL452076" or edge.target_id == "CHEMBL.COMPOUND:CHEMBL452076":
                print(edge)

    #for node in message.knowledge_graph.nodes:
    #    print(f"{node.name} {node.type[0]}")
    #     print(node.qnode_id)


    # if params.example_number == 101:
    #     import math
    #     edge_values = {}
    #     # iterate over the edges find the attribute values
    #     for edge in message.knowledge_graph.edges:  # iterate over the edges
    #         edge_values[str(edge.id)] = {'value': None, 'type': edge.type}
    #         if hasattr(edge, 'edge_attributes'):  # check if they have attributes
    #             if edge.edge_attributes:  # if there are any edge attributes
    #                 for attribute in edge.edge_attributes:  # for each attribute
    #                     if attribute.name == 'jaccard_index':  # check if it's the desired one
    #                         edge_values[str(edge.id)] = {'value': attribute.value, 'type': edge.type}
    #     if True:
    #         value_list=[-math.inf]*len(message.results)
    #     else:
    #         value_list=[math.inf]*len(message.results)
    #     i = 0
    #     type_flag = False
    #     for result in message.results:
    #         for binding in result.edge_bindings:
    #             if edge_values[binding.kg_id]['value'] is not None:
    #                 if not type_flag or (type_flag and params['edge_type'] == edge_values[binding.kg_id]['type']):
    #                     if abs(value_list[i]) == math.inf:
    #                         value_list[i] = edge_values[binding.kg_id]['value']
    #                     else:
    #                         # this will take the sum off all edges with the attribute if we want to change to max edit this line
    #                         value_list[i] += edge_values[binding.kg_id]['value']
    #         i+=1
    #     print(value_list)
    #     print([len(r.edge_bindings) for r in message.results])
    # if params.example_number == 102:
    #     import math
    #     node_values = {}
    #     # iterate over the nodes find the attribute values
    #     for node in message.knowledge_graph.nodes:  # iterate over the nodes
    #         node_values[str(node.id)] = {'value': None, 'type': node.type}
    #         if hasattr(node, 'node_attributes'):  # check if they have attributes
    #             if node.node_attributes:  # if there are any node attributes
    #                 for attribute in node.node_attributes:  # for each attribute
    #                     if attribute.name == 'pubmed_ids':  # check if it's the desired one
    #                         node_values[str(node.id)] = {'value': attribute.value.count("PMID"), 'type': node.type}
    #     if True:
    #         value_list=[-math.inf]*len(message.results)
    #     else:
    #         value_list=[math.inf]*len(message.results)
    #     i = 0
    #     type_flag = False
    #     for result in message.results:
    #         for binding in result.node_bindings:
    #             if node_values[binding.kg_id]['value'] is not None:
    #                 if not type_flag or (type_flag and params['node_type'] == node_values[binding.kg_id]['type']):
    #                     if abs(value_list[i]) == math.inf:
    #                         value_list[i] = node_values[binding.kg_id]['value']
    #                     else:
    #                         # this will take the sum off all nodes with the attribute if we want to change to max edit this line
    #                         value_list[i] += node_values[binding.kg_id]['value']
    #         i+=1
    #     print(value_list)
    #     #print([len(r.node_bindings) for r in message.results])

    #print(len(message.knowledge_graph.nodes))

    # check number of TP's for example 3
    if False:
        proteins = []
        for node in message.knowledge_graph.nodes:
            if node.type[0] == "protein":
                proteins.append(node.id)
        #for protein in sorted(proteins):
        #    print(f"{protein}")
        known_proteins = ["UniProtKB:P16473",
"UniProtKB:P05093",
"UniProtKB:P06401",
"UniProtKB:P08235",
"UniProtKB:P18405",
"UniProtKB:P03372",
"UniProtKB:P10275",
"UniProtKB:P11511",
"UniProtKB:P19838",
"UniProtKB:Q13936",
"UniProtKB:Q16665",
"UniProtKB:P22888",
"UniProtKB:Q9HB55",
"UniProtKB:P05108",
"UniProtKB:P08684",
"UniProtKB:Q92731",
"UniProtKB:P80365",
"UniProtKB:P24462",
"UniProtKB:P04278",
"UniProtKB:P31213",
"UniProtKB:P08842",
"UniProtKB:Q15125",
"UniProtKB:P04150",
"UniProtKB:P37058",
"UniProtKB:P54132",
"UniProtKB:P24462",
"UniProtKB:P80365",
"UniProtKB:Q92731",
"UniProtKB:P04278",
"UniProtKB:P31213",
"UniProtKB:Q15125",
"UniProtKB:P08842",
"UniProtKB:P16473",
"UniProtKB:P08235",
"UniProtKB:P05093",
"UniProtKB:P06401",
"UniProtKB:P18405",
"UniProtKB:P54132",
"UniProtKB:P04150",
"UniProtKB:P37058",
"UniProtKB:P08684",
"UniProtKB:P22888",
"UniProtKB:P05108",
"UniProtKB:Q9HB55",
"UniProtKB:Q13936",
"UniProtKB:P19838",
"UniProtKB:P11511",
"UniProtKB:P10275",
"UniProtKB:Q16665",
"UniProtKB:P03372"]
        print(f"For example 15 (demo eg. 3), number of TP proteins: {len(set(known_proteins).intersection(set(proteins)))}")  # fill these in after finding a good example

    try:
        print(f"Number of KnowledgeProviders in KG: {Counter([x.provided_by for x in message.knowledge_graph.edges])}")
    except:
        print(f"Number of KnowledgeProviders in KG: {Counter([y for x in message.knowledge_graph.edges for y in x.provided_by])}")

# print the message id at the bottom for convenience too:
    print(f"message id: {json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2)}")

if __name__ == "__main__": main()
