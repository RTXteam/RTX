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
import requests

from ARAX_response import ARAXResponse
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo
from actions_parser import ActionsParser
from ARAX_filter import ARAXFilter
from ARAX_resultify import ARAXResultify
from ARAX_query_graph_interpreter import ARAXQueryGraphInterpreter
from ARAX_messenger import ARAXMessenger
from ARAX_ranker import ARAXRanker
from operation_to_ARAXi import WorkflowToARAXi
from ARAX_query_tracker import ARAXQueryTracker

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.response import Response
from openapi_server.models.message import Message
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge
from openapi_server.models.operations import Operations

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
from RTXConfiguration import RTXConfiguration

from openapi_server.models.message import Message
from openapi_server.models.q_node import QNode
from openapi_server.models.q_edge import QEdge

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering")
#from ParseQuestion import ParseQuestion
#from QueryGraphReasoner import QueryGraphReasoner

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ResponseCache")
from response_cache import ResponseCache

from ARAX_database_manager import ARAXDatabaseManager
from reasoner_validator import validate
from jsonschema.exceptions import ValidationError

query_tracker_reset = ARAXQueryTracker()
query_tracker_reset.clear_unfinished_entries()


class ARAXQuery:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.rtxConfig = RTXConfiguration()
        
        self.DBManager = ARAXDatabaseManager(live = "Production")
        if self.DBManager.check_versions():
            self.response = ARAXResponse()
            self.response.debug(f"At least one database file is either missing or out of date. Updating now... (This may take a while)")
            self.response = self.DBManager.update_databases(True, response=self.response)

    def query_return_stream(self,query, mode='ARAX'):

        main_query_thread = threading.Thread(target=self.asynchronous_query, args=(query,mode,))
        main_query_thread.start()

        if self.response is None or "DONE" not in self.response.status:

            # Sleep until a response object has been created
            while self.response is None:
                time.sleep(0.1)

            i_message = 0
            n_messages = len(self.response.messages)
            query_plan_counter = 0
            idle_ticks = 0.0

            while "DONE" not in self.response.status:
                n_messages = len(self.response.messages)
                while i_message < n_messages:
                    yield(json.dumps(self.response.messages[i_message])+"\n")
                    i_message += 1
                    idle_ticks = 0.0
                #### Also emit any updates to the query_plan
                if query_plan_counter < self.response.query_plan['counter']:
                    query_plan_counter = self.response.query_plan['counter']
                    yield(json.dumps(self.response.query_plan,sort_keys=True)+"\n")
                    idle_ticks = 0.0
                time.sleep(0.2)
                idle_ticks += 0.2
                if idle_ticks > 180.0:
                    timestamp = str(datetime.now().isoformat())
                    yield(json.dumps({ 'timestamp': timestamp, 'level': 'DEBUG', 'code': '', 'message': 'Query is still progressing...' })+"\n")
                    idle_ticks = 0.0

            # #### If there are any more logging messages in the queue, send them first
            n_messages = len(self.response.messages)
            while i_message < n_messages:
                yield(json.dumps(self.response.messages[i_message])+"\n")
                i_message += 1

            #### Also emit any updates to the query_plan
            if query_plan_counter < self.response.query_plan['counter']:
                query_plan_counter = self.response.query_plan['counter']
                yield(json.dumps(self.response.query_plan,sort_keys=True)+"\n")

            # Remove the little DONE flag the other thread used to signal this thread that it is done
            self.response.status = re.sub('DONE,','',self.response.status)

            # Stream the resulting message back to the client
            yield(json.dumps(self.response.envelope.to_dict(),sort_keys=True))

        # Wait until both threads rejoin here and the return
        main_query_thread.join()
        self.track_query_finish()
        return { 'DONE': True }


    def asynchronous_query(self,query, mode='ARAX'):

        #### Define a new response object if one does not yet exist
        if self.response is None:
            self.response = ARAXResponse()

        #### Execute the query
        self.query(query, mode=mode, origin='API')

        #### Do we still need all this cruft?
        #result = self.query(query)
        #message = self.message
        #if message is None:
        #    message = Message()
        #    self.message = message
        #message.message_code = result.error_code
        #message.code_description = result.message
        #message.log = result.messages

        # Insert a little flag into the response status to denote that this thread is done
        self.response.status = f"DONE,{self.response.status}"
        return


    ########################################################################################
    def query_return_message(self, query, mode='ARAX'):

        self.query(query, mode=mode, origin='API')
        response = self.response

        #### If the query ended in an error, copy the error to the envelope
        if response.status != 'OK':
            response.envelope.status = response.error_code
            response.envelope.description = response.message
            if hasattr(response,'http_status'):
                response.envelope.http_status = response.http_status

        if mode == 'asynchronous':
            attributes = {
                'status': 'Running Async',
                'message_id': None,
                'message_code': 'Running',
                'code_description': 'Query running via /asyncquery'
            }
            query_tracker = ARAXQueryTracker()
            query_tracker.update_tracker_entry(self.response.tracker_id, attributes)
        else:
            self.track_query_finish()

        return response.envelope


    ########################################################################################
    def track_query_finish(self):

        query_tracker = ARAXQueryTracker()
        try:
            response_id = self.response.response_id
        except:
            response_id = None

        attributes = {
            'status': 'Completed',
            'message_id': response_id,
            'message_code': self.response.error_code,
            'code_description': self.response.message
        }

        query_tracker.update_tracker_entry(self.response.tracker_id, attributes)




    ########################################################################################
    def query(self,query, mode='ARAX', origin='local'):

        #### Create the skeleton of the response
        response = ARAXResponse()
        self.response = response

        #### Announce the launch of query()
        #### Note that setting ARAXResponse.output = 'STDERR' means that we get noisy output to the logs
        ARAXResponse.output = 'STDERR'
        response.info(f"{mode} Query launching on incoming Query")

        #### Create an empty envelope
        messenger = ARAXMessenger()
        messenger.create_envelope(response)

        #### Preserve the query_options
        if 'query_options' in query and query['query_options'] is not None:
            response.envelope.query_options = query['query_options']
        else:
            response.envelope.query_options = {}

        #### If a submitter came in, reflect that back into the response
        if "callback" in query and query['callback'] is not None and query['callback'].startswith('http://localhost:8000/ars/'):
            response.envelope.submitter = 'ARS'
        elif 'submitter' in query:
            response.envelope.submitter = query['submitter']
        else:
            if "callback" in query and query['callback'] is not None:
                match = re.match(r'http[s]://(.+?)/',query['callback'])
                if match:
                    response.envelope.submitter = match.group(1)
                else:
                    response.envelope.submitter = '?'
            else:
                response.envelope.submitter = '?'

        #### Create an entry to track this query
        tracker_id = None
        if origin == 'API':
            query_tracker = ARAXQueryTracker()
            attributes = { 'submitter': response.envelope.submitter, 'input_query': query, 'remote_address': 'test_address' }
            tracker_id = query_tracker.create_tracker_entry(attributes)
        response.tracker_id = tracker_id

        #### Determine a plan for what to do based on the input
        #eprint(json.dumps(query, indent=2, sort_keys=True))
        result = self.examine_incoming_query(query, mode=mode)
        if result.status != 'OK':
            return response
        query_attributes = result.data

        #### Convert the message from dicts to objects
        if 'message' in query:
            response.debug(f"Deserializing message")
            query['message'] = ARAXMessenger().from_dict(query['message'])

        # If there is a workflow, translate it to ARAXi and append it to the operations actions list
        if "have_workflow" in query_attributes:
            if query['message'].query_graph is None:
                response.error(f"Cannot have a workflow with an null query_graph", error_code="MissingQueryGraph")
                return response

            try:
                self.convert_workflow_to_ARAXi(query)
            except Exception as error:
                exception_type, exception_value, exception_traceback = sys.exc_info()
                response.error(f"An unhandled error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UnhandledError")
                return response
            query_attributes["have_operations"] = True

        # #### If we have a query_graph in the input query
        if "have_query_graph" in query_attributes and "have_operations" not in query_attributes:

            response.envelope.message.query_graph = query['message'].query_graph

            #### In ARAX mode, run the QueryGraph through the QueryGraphInterpreter and to generate ARAXi
            if mode == 'ARAX' or mode == 'asynchronous':
                response.info(f"Found input query_graph. Interpreting it and generating ARAXi processing plan to answer it")
                interpreter = ARAXQueryGraphInterpreter()
                interpreter.translate_to_araxi(response)
                if response.status != 'OK':
                    return response
                query['operations'] = {}
                query['operations']['actions'] = result.data['araxi_commands']

            #### Else the mode is KG2 mode, where we just accept one-hop queries, and run a simple ARAXi
            else:
                response.info(f"Found input query_graph. Querying RTX KG2 to answer it")
                if len(response.envelope.message.query_graph.nodes) > 2:
                    response.error(f"Only 1 hop (2 node) queries can be handled at this time", error_code="TooManyHops")
                    return response
                query['operations'] = {}
                query['operations']['actions'] = [ 'expand(kp=RTX-KG2)', 'resultify()', 'return(store=false)' ]

            query_attributes['have_operations'] = True


        #### If we have operations, execute them
        if "have_operations" in query_attributes:
            response.info(f"Found input processing plan. Sending to the ProcessingPlanExecutor")
            result = self.execute_processing_plan(query, mode=mode)

        #### This used to support canned queries, but no longer does
        else:
            response.error(f"Unable to determine ARAXi to execute. Error Q213", error_code="UnknownError")

        return response


    #######################################################################################
    def examine_incoming_query(self, query, mode='ARAX'):

        response = self.response
        response.info(f"Examine input Query for needed information for dispatch")
        #eprint(query)

        #### Check to see if there's an operations processing plan
        if 'operations' in query and query['operations'] is not None:
            response.data["have_operations"] = 1

        #### Check to see if there's a workflow processing plan
        if 'workflow' in query and query['workflow'] is not None:
            response.data["have_workflow"] = 1

        #### Check to see if there's a query message to process
        if 'message' in query and query['message'] is not None:
            response.data["have_message"] = 1

            #### Check if there is a query_graph
            if "query_graph" in query["message"] and query["message"]["query_graph"] is not None:
                response.data["have_query_graph"] = 1
                self.validate_incoming_query_graph(query["message"])

        #### Check to see if there is at least a message or a operations
        if "have_message" not in response.data and "have_operations" not in response.data:
            response.error("No message or operations present in Query", error_code="NoQueryMessageOrOperations")
            return response

        # #### FIXME Need to do more validation and tidying of the incoming message here or somewhere


        # RTXKG2 does not support operations
        if mode == 'RTXKG2' and "have_operations" in response.data:
            response.error("RTXKG2 does not support operations in Query", error_code="OperationsNotSupported")
            return response

        #### If we got this far, then everything seems to be good enough to proceed
        return response


    #######################################################################################
    def convert_workflow_to_ARAXi(self, query):

        response = self.response
        response.info(f"Converting workflow elements to ARAXi")

        # Convert the TRAPI workflow into ARAXi
        converter = WorkflowToARAXi()
        araxi = converter.translate(query['workflow'], query['message'].query_graph.to_dict(), response)

        # If there are not already operations, create empty stubs
        if 'operations' not in query:
            query['operations'] = {}
        if 'actions' not in query['operations']:
            query['operations']['actions'] = []

        # Append the new workflow-based ARAXi onto the end of the existing actions if there are any
        query['operations']['actions'].extend(araxi)

        return response


    ############################################################################################
    def validate_incoming_query_graph(self,message):

        response = self.response
        response.info(f"Validating the input query graph")

        # Define allowed qnode and qedge attributes to check later
        allowed_qnode_attributes = { 'ids': 1, 'categories':1, 'is_set': 1, 'option_group_id': 1, 'name': 1, 'constraints': 1 }
        allowed_qedge_attributes = { 'predicates':1, 'subject': 1, 'object': 1, 'option_group_id': 1, 'exclude': 1, 'relation': 1, 'constraints': 1 }

        #### Loop through nodes checking the attributes
        for id,qnode in message['query_graph']['nodes'].items():
            for attr in qnode:
                if attr not in allowed_qnode_attributes:
                    response.error(f"QueryGraph node '{id}' has an unexpected property '{attr}'. This property is not understood and therefore processing is halted, rather than answer an incompletely understood query", error_code="UnknownQNodeProperty")
                    return response

        #### Loop through edges checking the attributes
        for id,qedge in message['query_graph']['edges'].items():
            for attr in qedge:
                if attr not in allowed_qedge_attributes:
                    response.error(f"QueryGraph edge '{id}' has an unexpected property '{attr}'. This property is not understood and therefore processing is halted, rather than answer an incompletely understood query", error_code="UnknownQEdgeProperty")
                    return response

        return response


    ############################################################################################
    def limit_message(self,message,query):
        if "max_results" in query and query["max_results"] is not None:
            if message.results is not None:
                if len(message.results) > query["max_results"]:
                    del message.results[query["max_results"]:]
                    message.code_description += " (output is limited to "+str(query["max_results"]) + " results)"



    ############################################################################################
    #### Given an input query with a processing plan, execute that processing plan on the input
    def execute_processing_plan(self,input_operations_dict, mode='ARAX'):

        response = self.response
        response.debug(f"Entering execute_processing_plan")
        messages = []
        message = None

        # If there is already a message (perhaps with a query_graph) already in the query, preserve it
        if 'message' in input_operations_dict and input_operations_dict['message'] is not None:
            incoming_message = input_operations_dict['message']
            if isinstance(incoming_message,dict):
                incoming_message = Message.from_dict(incoming_message)
            eprint(f"TESTING: incoming_test is a {type(incoming_message)}")
            messages = [ incoming_message ]

        #### Pull out the main processing plan
        operations = Operations.from_dict(input_operations_dict["operations"])

        #### Connect to the message store just once, even if we won't use it
        response_cache = ResponseCache()
        response_cache.connect()

        #### Create a messenger object for basic message processing
        messenger = ARAXMessenger()

        #### If there are URIs provided, try to load them
        force_remote = False
        if operations.message_uris is not None:
            response.debug(f"Found message_uris")
            for uri in operations.message_uris:
                response.debug(f"    messageURI={uri}")
                matchResult = re.match( r'http[s]://arax.ncats.io/.*api/arax/.+/response/(\d+)',uri,re.M|re.I )
                if matchResult and not force_remote:
                    referenced_response_id = matchResult.group(1)
                    response.debug(f"Found local ARAX identifier corresponding to response_id {referenced_response_id}")
                    response.debug(f"Loading response_id {referenced_response_id}")
                    referenced_envelope = response_cache.get_response(referenced_response_id)

                    if False:
                        #### Hack to get it to work
                        for node_key,node in referenced_envelope["message"]["knowledge_graph"]["nodes"].items():
                            if 'attributes' in node and node['attributes'] is not None:
                                new_attrs = []
                                for attr in node['attributes']:
                                    if attr['type'] is not None:
                                        new_attrs.append(attr)
                                if len(new_attrs) < len(node['attributes']):
                                    node['attributes'] = new_attrs

                        #### Hack to get it to work
                        for node_key,node in referenced_envelope["message"]["knowledge_graph"]["edges"].items():
                            if 'attributes' in node and node['attributes'] is not None:
                                new_attrs = []
                                for attr in node['attributes']:
                                    if attr['type'] is not None:
                                        new_attrs.append(attr)
                                if len(new_attrs) < len(node['attributes']):
                                    node['attributes'] = new_attrs

                    if isinstance(referenced_envelope,dict):
                        referenced_envelope = Response().from_dict(referenced_envelope)
                        #messages.append(referenced_message)
                        messages = [ referenced_envelope.message ]
                        #eprint(json.dumps(referenced_envelope.message.results,indent=2))
                    else:
                        response.error(f"Unable to load response_id {referenced_response_id}", error_code="CannotLoadPreviousResponseById")
                        return response

                else:
                    loaded_message = messenger.fetch_message(uri)
                    messages = [ loaded_message ]

        #### If there are one or more messages embedded in the POST, process them
        if operations.messages is not None:
            response.debug(f"Received messages")
            for uploadedMessage in operations.messages:
                response.debug(f"uploadedMessage is a "+str(uploadedMessage.__class__))
                if str(uploadedMessage.__class__) == "<class 'openapi_server.models.message.Message'>":
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

        #### If there's no input message, then create one
        if n_messages == 0:
            response.debug(f"No starting messages were referenced. Will start with a blank template Message")
            messenger.create_envelope(response)

            message = response.envelope.message

        #### If there's on message, we will run with that
        elif n_messages == 1:
            response.debug(f"A single Message is ready and in hand")
            message = messages[0]
            response.envelope.message = message

        #### Multiple messages unsupported
        else:
            response.debug(f"Multiple Messages were uploaded or imported by reference. However, proper merging code has not been implmented yet! Will use just the first Message for now.")
            message = messages[0]

        #### Examine the options that were provided and act accordingly
        optionsDict = {}
        if operations.options:
            response.debug(f"Processing options were provided, but these are not implemented at the moment and will be ignored")
            for option in operations.options:
                response.debug(f"   option="+option)
                optionsDict[option] = 1


        #### If there are actions, then fulfill those
        if operations.actions:
            response.debug(f"Found actions")
            actions_parser = ActionsParser()
            result = actions_parser.parse(operations.actions)
            response.merge(result)
            if result.error_code != 'OK':
                return response

            #### Put our input processing actions into the envelope
            if response.envelope.operations is None:
                response.envelope.operations = {}
            response.envelope.operations['actions'] = operations.actions


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

            #### Create some empty stubs if they don't exist
            if message.results is None:
                message.results = []


            #### If the mode is asynchronous, then fork here. The parent returns the response thus far that everything checks out and is proceeding
            #### and the child continues to work on the query, eventually to finish and exit()
            if mode == 'asynchronous':
                callback = input_operations_dict['callback']
                response.info(f"Everything seems in order to begin processing the query asynchronously. Processing will continue and Response will be posted to {callback}")
                newpid = os.fork()
                #### The parent returns to tell the caller that work will proceed
                if newpid > 0:
                    response.envelope.status = 'Running'
                    response.envelope.description = 'Asynchronous answering of query underway'
                    return response
                #### The child continues
                #### The child loses the MySQL connection of the parent, so need to reconnect
                response_cache.connect()
                
            #### If there is already a KG with edges, recompute the qg_keys
            if message.knowledge_graph is not None and len(message.knowledge_graph.edges) > 0:
                resultifier.recompute_qg_keys(response)

            #### Process each action in order
            action_stats = { }
            actions = result.data['actions']
            action = None
            for action in actions:
                response.info(f"Processing action '{action['command']}' with parameters {action['parameters']}")
                nonstandard_result = False
                skip_merge = False

                # Catch a crash
                try:
                    if action['command'] == 'create_message':
                        messenger.create_envelope(response)
                        #### Put our input processing actions into the envelope
                        if response.envelope.query_options is None:
                            response.envelope.query_options = {}
                        response.envelope.query_options['actions'] = operations.actions

                    elif action['command'] == 'fetch_message':
                        messenger.apply_fetch_message(response,action['parameters'])

                    elif action['command'] == 'add_qnode':
                        messenger.add_qnode(response,action['parameters'])

                    elif action['command'] == 'add_qedge':
                        messenger.add_qedge(response,action['parameters'])

                    elif action['command'] == 'expand':
                        user_timeout = None
                        if response.envelope.query_options is not None and 'kp_timeout' in response.envelope.query_options:
                            user_timeout = response.envelope.query_options['kp_timeout']
                            try:
                                user_timeout = int(user_timeout)
                            except:
                                response.error(f"Unable to convert user_timeout '{user_timeout} into an integer", error_code="UserTimeoutNotInt")
                                return response
                        expander.apply(response, action['parameters'], mode=mode, user_timeout=user_timeout)

                    elif action['command'] == 'filter':
                        filter.apply(response,action['parameters'])

                    elif action['command'] == 'resultify':
                        resultifier.apply(response, action['parameters'])

                    elif action['command'] == 'scoreless_resultify':
                        resultifier.apply(response, action['parameters'])

                    elif action['command'] == 'overlay':  # recognize the overlay command
                        overlay.apply(response, action['parameters'])

                    elif action['command'] == 'filter_kg':  # recognize the filter_kg command
                        filter_kg.apply(response, action['parameters'])

                    elif action['command'] == 'filter_results':  # recognize the filter_results command
                        response.debug(f"Before filtering, there are {len(response.envelope.message.results)} results")
                        filter_results.apply(response, action['parameters'])

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
                            ranker.aggregate_scores_dmk(response)
                        except Exception as error:
                            exception_type, exception_value, exception_traceback = sys.exc_info()
                            response.error(f"An uncaught error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UncaughtARAXiError")
                            if mode == 'asynchronous':
                                self.send_to_callback(callback, response)
                            return response

                    else:
                        response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
                        if mode == 'asynchronous':
                            self.send_to_callback(callback, response)
                        return response

                except Exception as error:
                    exception_type, exception_value, exception_traceback = sys.exc_info()
                    response.error(f"An uncaught error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UncaughtARAXiError")
                    if mode == 'asynchronous':
                        self.send_to_callback(callback, response)
                    return response

                #### If we're in an error state return now
                if response.status != 'OK':
                    response.envelope.status = response.error_code
                    response.envelope.description = response.message
                    if mode == 'asynchronous':
                        self.send_to_callback(callback, response)
                    return response

                #### Immediately after resultify, run the experimental ranker
                if action['command'] == 'resultify':
                    response.info(f"Running experimental reranker on results")
                    try:
                        ranker = ARAXRanker()
                        ranker.aggregate_scores_dmk(response)
                    except Exception as error:
                        exception_type, exception_value, exception_traceback = sys.exc_info()
                        response.error(f"An uncaught error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UncaughtARAXiError")
                        if mode == 'asynchronous':
                            self.send_to_callback(callback, response)
                        return response

            #### At the end, process the explicit return() action, or implicitly perform one
            return_action = { 'command': 'return', 'parameters': { 'response': 'true', 'store': 'true' } }
            if action is not None and action['command'] == 'return':
                return_action = action
                #### If an explicit one left out some parameters, set the defaults
                if 'store' not in return_action['parameters']:
                    return_action['parameters']['store'] = 'false'
                if 'response' not in return_action['parameters']:
                    return_action['parameters']['response'] = 'false'

            #print(json.dumps(ast.literal_eval(repr(response.__dict__)), sort_keys=True, indent=2))
            #for node_key, node in response.envelope.message.knowledge_graph.nodes.items():
            #    if node.attributes is not None:
            #        for attr in node.attributes:
            #            eprint(f"  - {node_key}.{attr.name} is {type(attr.value)}")

            # Fill out the message with data
            response.envelope.status = response.error_code
            response.envelope.description = response.message
            if response.envelope.operations is None:
                response.envelope.operations = operations
            #response.envelope.operations['actions'] = operations.actions

            # Update the reasoner_id to ARAX if not already present
            for result in response.envelope.message.results:
                if result.reasoner_id is None:
                    result.reasoner_id = 'ARAX'

            # Store the validation and provenance metadata
            #trapi_version = '1.2.0'
            #validate(response.envelope,'Response',trapi_version)
            #response.envelope.validation_result = { 'status': 'PASS', 'version': trapi_version, 'size': '?', 'message': '' }
            #from ARAX_attribute_parser import ARAXAttributeParser
            #attribute_parser = ARAXAttributeParser(response.envelope,response.envelope['message'])
            #response.envelope.validation_result['provenance_summary'] = attribute_parser.summarize_provenance_info()
            #response.envelope.validation_result = { 'status': 'PASS', 'version': trapi_version, 'size': '?', 'message': '' }
            if response.envelope.query_options is None:
                response.envelope.query_options = {}
            response.envelope.query_options['query_plan'] = response.query_plan

            # If store=true, then put the message in the database
            response_id = None
            if return_action['parameters']['store'] == 'true':
                response.debug(f"Storing resulting Message")
                response_id = response_cache.add_new_response(response)
                response.info(f"Result was stored with id {response_id}. It can be viewed at https://arax.ncats.io/?r={response_id}")
            response.response_id = response_id
 
            #### Record how many results came back
            n_results = len(message.results)
            response.info(f"Processing is complete and resulted in {n_results} results.")
            if response.message == 'Normal completion':
                response.message = f"Normal completion with {n_results} results."

            #### If asking for the full message back
            if return_action['parameters']['response'] == 'true':
                if mode == 'asynchronous':
                    response.info(f"Processing is complete. Attempting to the result to the callback URL.")
                    self.send_to_callback(callback, response)
                else:
                    response.info(f"Processing is complete. Transmitting resulting Message back to client.")
                    return response

            #### Else just the id is returned
            else:
                if response_id is None:
                    response_id = 0
                else:
                    response.info(f"Resulting Message id is {response_id} and is available to fetch via /response endpoint.")

                servername = 'localhost'
                if self.rtxConfig.is_production_server:
                    servername = 'arax.ncats.io'
                url = f"https://{servername}/api/arax/v1.0/response/{response_id}"

                return( { "status": 200, "response_id": str(response_id), "n_results": n_results, "url": url }, 200)



    ############################################################################################
    def send_to_callback(self, callback, response):
        response.info(f"Attempting to send to callback URL: {callback}")
        envelope_dict = response.envelope.to_dict()
        try:
            post_response_content = requests.post(callback, json=envelope_dict, headers={'accept': 'application/json'})
            status_code = post_response_content.status_code
            response.info(f"Response from POST to callback URL was {status_code}")
            if status_code not in [ 200, 201 ]:
                response.error(f"Response from POST to callback URL was {status_code}", error_code="UnreachableCallback")

        except:
            response.error(f"Unable to make a connection to URL {callback} at all. Work is lost", error_code="UnreachableCallback")
        self.track_query_finish()
        os._exit(0)


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

    #### Create the ARAXQuery object
    araxq = ARAXQuery()

    #### For debugging purposes, you can send all messages as they are logged to STDERR
    #ARAXResponse.output = 'STDERR'

    #### Set the query based on the supplied example_number
    if params.example_number == 0:
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=acetaminophen, key=n0)",
            "add_qnode(categories=biolink:Protein, key=n1)",
            "add_qedge(subject=n0, object=n1, key=e0)",
            "expand(edge_key=e0)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=10)",
            "return(message=true, store=true)",
        ]}}

    elif params.example_number == 1:
        query = { 'message': { 'query_type_id': 'Q0', 'terms': { 'term': 'lovastatin' } } }
        #query = { "query_type_id": "Q0", "terms": { "term": "lovastatin" }, "bypass_cache": "true" }  # Use bypass_cache if the cache if bad for this question

    elif params.example_number == 2:
        query = { "message": { "query_graph": { "edges": [
                    { "id": "qg2", "subject": "qg1", "object": "qg0", "type": "physically_interacts_with" }
                ],
                "nodes": [
                    { "id": "qg0", "name": "acetaminophen", "curie": "CHEMBL.COMPOUND:CHEMBL112", "type": "chemical_substance" },
                    { "id": "qg1", "name": None, "desc": "Generic protein", "curie": None, "type": "protein" }
                ] } } }

    elif params.example_number == 3:  # FIXME: Don't fix me, this is our planned demo example 1.
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=acetaminophen, key=n0)",
            "add_qnode(categories=biolink:Protein, key=n1)",
            "add_qedge(subject=n0, object=n1, key=e0)",
            "expand(edge_key=e0)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=10)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 301:  # Variant of 3 with NGD
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=acetaminophen, key=n0)",
            "add_qnode(categories=biolink:Protein, key=n1)",
            "add_qedge(subject=n0, object=n1, key=e0)",
            "expand(edge_key=e0)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 4:
        query = { "operations": { "actions": [
            "add_qnode(name=hypertension, key=n00)",
            "add_qnode(categories=biolink:Protein, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00)",
            "resultify()",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 5:  # test overlay with ngd: hypertension->protein
        query = { "operations": { "actions": [
            "add_qnode(name=hypertension, key=n00)",
            "add_qnode(categories=biolink:Protein, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00)",
            "overlay(action=compute_ngd)",
            "resultify()",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 6:  # test overlay
        query = { "operations": { "actions": [
            "create_message",
            "add_qnode(ids=DOID:12384, key=n00)",
            "add_qnode(categories=biolink:PhenotypicFeature, is_set=True, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00, type=has_phenotype)",
            "expand(edge_key=e00, kp=RTX-KG2)",
            #"overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
            #"overlay(action=overlay_clinical_info, chi_square=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
            #"overlay(action=compute_ngd, default_value=inf)",
            #"overlay(action=compute_ngd, virtual_relation_label=NGD1, subject_qnode_key=n00, object_qnode_key=n01)",
            "filter(maximum_results=2)",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 7:  # stub to test out the compute_jaccard feature
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:14330, key=n00)",  # parkinsons
            "add_qnode(categories=biolink:Protein, is_set=True, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=false, key=n02)",
            "add_qedge(subject=n01, object=n00, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 8:  # to test jaccard with known result  # FIXME:  ERROR: Node DOID:8398 has been returned as an answer for multiple query graph nodes (n00, n02)
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:8398, key=n00)",  # osteoarthritis
            "add_qnode(categories=biolink:PhenotypicFeature, is_set=True, key=n01)",
            "add_qnode(type=disease, is_set=true, key=n02)",
            "add_qedge(subject=n01, object=n00, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_id=[e00,e01])",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 9:  # to test jaccard with known result. This check's out by comparing with match p=(s:disease{ids:"DOID:1588"})-[]-(r:protein)-[]-(:chemical_substance) return p and manually counting
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:1588, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=True, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n02)",
            "add_qedge(subject=n01, object=n00, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 10:  # test case of drug prediction
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:1588, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=false, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00)",
            "overlay(action=predict_drug_treats_disease)",
            "resultify(ignore_edge_direction=True)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 11:  # test overlay with overlay_clinical_info, paired_concept_frequency via COHD
        query = { "operations": { "actions": [
            "create_message",
            "add_qnode(ids=DOID:0060227, key=n00)",  # Adam's oliver
            "add_qnode(categories=biolink:PhenotypicFeature, is_set=True, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00, type=has_phenotype)",
            "expand(edge_key=e00)",
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
            #"overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_relation_label=COHD1, subject_qnode_key=n00, object_qnode_key=n01)",
            "filter(maximum_results=2)",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 12:  # dry run of example 2 # FIXME NOTE: this is our planned example 2 (so don't fix, it's just so it's highlighted in my IDE)
        query = { "operations": { "actions": [
            "create_message",
            "add_qnode(name=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_key=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",  # can be removed, but shows we can filter by Knowledge provider
            "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=true)",
            ] } }
    elif params.example_number == 13:  # add pubmed id's
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00)",
            "overlay(action=add_node_pmids, max_num=15)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 14:  # test
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:8712, key=n00)",
            "add_qnode(categories=biolink:PhenotypicFeature, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n02)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n03)",
            "add_qedge(subject=n00, object=n01, key=e00, type=has_phenotype)",  # phenotypes of disease
            "add_qedge(subject=n02, object=n01, key=e01, type=indicated_for)",  # only look for drugs that are indicated for those phenotypes
            "add_qedge(subject=n02, object=n03, key=e02)",  # find proteins that interact with those drugs
            "expand(edge_id=[e00, e01, e02])",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",  # only look at drugs that target lots of phenotypes
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.06, remove_connected_nodes=t, qnode_key=n02)",  # remove edges and drugs that connect to few phenotypes
            #"filter_kg(action=remove_edges_by_type, edge_type=J1, remove_connected_nodes=f)",
            ##"overlay(action=overlay_clinical_info, paired_concept_frequency=true)",  # overlay with COHD information
            #"overlay(action=overlay_clinical_info, paired_concept_frequency=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n02)",  # overlay drug->disease virtual edges with COHD information
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=paired_concept_frequency, direction=below, threshold=0.0000001, remove_connected_nodes=t, qnode_key=n02)",  # remove drugs below COHD threshold
            #"overlay(action=compute_jaccard, start_node_key=n01, intermediate_node_key=n02, end_node_key=n03, virtual_relation_label=J2)",  # look at proteins that share many/any drugs in common with the phenotypes
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.001, remove_connected_nodes=t, qnode_key=n03)",
            #"filter_kg(action=remove_edges_by_type, edge_type=J2, remove_connected_nodes=f)",
            #"filter_kg(action=remove_edges_by_type, edge_type=C1, remove_connected_nodes=f)",
            ##"overlay(action=compute_ngd)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 15:  # FIXME NOTE: this is our planned example 3 (so don't fix, it's just so it's highlighted in my IDE)
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:9406, key=n00)",  # hypopituitarism
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",  # look for all drugs associated with this disease (29 total drugs)
            "add_qnode(categories=biolink:Protein, key=n02)",   # look for proteins associated with these diseases (240 total proteins)
            "add_qedge(subject=n00, object=n01, key=e00)",  # get connections
            "add_qedge(subject=n01, object=n02, key=e01)",  # get connections
            "expand(edge_id=[e00,e01])",  # expand the query graph
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",  # Look in COHD to find which drug are being used to treat this disease based on the log ratio of expected frequency of this drug being used to treat a disease, vs. the observed number of times it’s used to treat this disease
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_key=n01)",   # concentrate only on those drugs that are more likely to be treating this disease than expected
            "filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",  # remove proteins that got disconnected as a result of this filter action
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",   # use normalized google distance to find how frequently the protein and the drug are mentioned in abstracts
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_key=n02)",   # remove proteins that are not frequently mentioned together in PubMed abstracts
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 1515:  # Exact duplicate of ARAX_Example3.ipynb
        query = {"operations": {"actions": [
            "add_qnode(ids=DOID:9406, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
            "add_qnode(categories=biolink:Protein, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_key=n01)",
            "filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_key=n02)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 16:  # To test COHD
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:8398, key=n00)",
            #"add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(categories=biolink:PhenotypicFeature, key=n01)",
            "add_qedge(subject=n00, object=n01, type=has_phenotype, key=e00)",
            "expand(edge_key=e00)",
            "overlay(action=overlay_clinical_info, chi_square=true)",
            "resultify()",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 17:  # Test resultify #FIXME: this returns a single result instead of a list (one for each disease/phenotype found)
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:731, key=n00, type=disease, is_set=false)",
            "add_qnode(categories=biolink:PhenotypicFeature, is_set=false, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00)",
            'resultify(ignore_edge_direction=true)',
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 18:  # test removing orphaned nodes
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:9406, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00, e01])",
            "filter_kg(action=remove_edges_by_type, edge_type=physically_interacts_with, remove_connected_nodes=f)",
            "filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 19:  # Let's see what happens if you ask for a node in KG2, but not in KG1 and try to expand
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UMLS:C1452002, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00, type=interacts_with)",
            "expand(edge_key=e00)",
            "return(message=true, store=false)"
        ]}}  # returns response of "OK" with the info: QueryGraphReasoner found no results for this query graph
    elif params.example_number == 20:  # Now try with KG2 expander
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=UMLS:C1452002, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00, type=interacts_with)",
            "expand(edge_key=e00, kp=RTX-KG2)",
            "return(message=true, store=false)"
        ]}}  # returns response of "OK" with the info: QueryGraphReasoner found no results for this query graph
    elif params.example_number == 101:  # test of filter results code
        query = { "operations": { "actions": [
            "create_message",
            "add_qnode(name=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_key=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=d, max_results=15)",
            #"filter_results(action=sort_by_edge_count, direction=a)",
            #"filter_results(action=limit_number_of_results, max_results=5)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 102:  # add pubmed id's
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00)",
            "overlay(action=add_node_pmids, max_num=15)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=a, max_results=20)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 103:  # add pubmed id's
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:1227, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00)",
            "overlay(action=add_node_pmids, max_num=15)",
            "filter_kg(action=remove_nodes_by_property, node_property=uri, property_value=https://www.ebi.ac.uk/chembl/compound/inspect/CHEMBL2111164)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 1212:  # dry run of example 2 with the machine learning model
        query = { "operations": { "actions": [
            "create_message",
            "add_qnode(ids=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_key=n02)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",  # can be removed, but shows we can filter by Knowledge provider
            "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",  # overlay by probability that the drug treats the disease
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=probability_drug_treats, direction=descending, max_results=15)",  # filter by the probability that the drug treats the disease. cilnidipine prob=0.8976650309881645 which is the 9th highest (so top 10)
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 201:  # KG2 version of demo example 1 (acetaminophen)
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
            "add_qnode(key=n01, categories=biolink:Protein, is_set=true)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "expand(edge_key=e00, kp=RTX-KG2)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 202:  # KG2 version of demo example 2 (Parkinson's)
        query = { "operations": { "actions": [
            "create_message",
            "add_qnode(name=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=molecularly_interacts_with)",  # for KG2
            #"add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",  # for KG1
            "expand(edge_id=[e00,e01], kp=RTX-KG2)",  # for KG2
            #"expand(edge_id=[e00,e01], kp=ARAX/KG1)",  # for KG1
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",  # seems to work just fine
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.008, remove_connected_nodes=t, qnode_key=n02)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 203:  # KG2 version of demo example 3 (but using idiopathic pulmonary fibrosis)
        query = { "operations": { "actions": [
            "create_message",
            #"add_qnode(key=n00, ids=DOID:0050156)",  # idiopathic pulmonary fibrosis
            "add_qnode(ids=DOID:9406, key=n00)",  # hypopituitarism, original demo example
            "add_qnode(key=n01, categories=biolink:ChemicalEntity, is_set=true)",
            "add_qnode(key=n02, categories=biolink:Protein)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "add_qedge(key=e01, subject=n01, object=n02)",
            "expand(edge_id=[e00,e01], kp=RTX-KG2)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=2, remove_connected_nodes=t, qnode_key=n01)",
            "filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 2033:  # KG2 version of demo example 3 (but using idiopathic pulmonary fibrosis), with all decorations
        query = { "operations": { "actions": [
            "create_message",
            "add_qnode(key=n00, id=DOID:0050156)",  # idiopathic pulmonary fibrosis
            #"add_qnode(ids=DOID:9406, key=n00)",  # hypopituitarism, original demo example
            "add_qnode(key=n01, categories=biolink:ChemicalEntity, is_set=true)",
            "add_qnode(key=n02, categories=biolink:Protein)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "add_qedge(key=e01, subject=n01, object=n02)",
            "expand(edge_id=[e00,e01], kp=RTX-KG2)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=0, remove_connected_nodes=t, qnode_key=n01)",
            #"filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 222:  # Simple BTE query
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=NCBIGene:1017)",  # CDK2
            "add_qnode(key=n01, categories=biolink:ChemicalEntity, is_set=True)",
            "add_qedge(key=e00, subject=n01, object=n00)",
            "expand(edge_key=e00, kp=BTE)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 233:  # KG2 version of demo example 1 (acetaminophen)
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
            "add_qnode(key=n01, categories=biolink:Protein, is_set=true)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "expand(edge_key=e00, kp=RTX-KG2)",
            "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=https://pharos.nih.gov)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 300:  # KG2 version of demo example 1 (acetaminophen)
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_edge_type=J1)",
            "filter_kg(action=remove_edges_by_attribute_default, edge_attribute=jaccard_index, type=std, remove_connected_nodes=t, qnode_key=n02)",
            #"filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",  # can be removed, but shows we can filter by Knowledge provider
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=descending, max_results=15)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 690:  # test issue 690
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:14330, key=n00)",
            "add_qnode(type=not_a_real_type, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=molecularly_interacts_with)",
            "expand(edge_id=[e00,e01], continue_if_no_results=true)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6231:  # chunyu testing #623, all nodes already in the KG and QG
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL521, categories=biolink:ChemicalEntity)",
            "add_qnode(key=n01, is_set=true, categories=biolink:Protein)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "add_qnode(key=n02, type=biological_process)",
            "add_qedge(key=e01, subject=n01, object=n02)",
            "expand(edge_id=[e00, e01], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n01, virtual_relation_label=FET, object_qnode_key=n02, cutoff=0.05)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6232:  # chunyu testing #623, this should return the 10 smallest FET p-values and only add the virtual edge with top 10 FET p-values
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL521, categories=biolink:ChemicalEntity)",
            "add_qnode(key=n01, is_set=true, categories=biolink:Protein)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "add_qnode(key=n02, type=biological_process)",
            "add_qedge(key=e01, subject=n01, object=n02)",
            "expand(edge_id=[e00, e01], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n01, virtual_relation_label=FET, object_qnode_key=n02, top_n=10)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6233:  # chunyu testing #623, this DSL tests the FET module based on (source id - involved_in - target id) and only decorate/add virtual edge with pvalue<0.05
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL521, categories=biolink:ChemicalEntity)",
            "add_qnode(key=n01, is_set=true, categories=biolink:Protein)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "add_qnode(key=n02, type=biological_process)",
            "add_qedge(key=e01, subject=n01, object=n02, type=involved_in)",
            "expand(edge_id=[e00, e01], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n01, virtual_relation_label=FET, object_qnode_key=n02, rel_edge_key=e01, cutoff=0.05)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6234:  # chunyu testing #623, nodes not in the KG and QG. This should throw an error initially. In the future we might want to add these nodes.
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL521, categories=biolink:ChemicalEntity)",
            "add_qnode(key=n01, categories=biolink:Protein)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "expand(edge_id=[e00], kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n01, virtual_relation_label=FET, object_qnode_key=n02, cutoff=0.05)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6235:  # chunyu testing #623, this is a two-hop sample. First, find all edges between DOID:14330 and proteins and then filter out the proteins with connection having pvalue>0.001 to DOID:14330. Second, find all edges between proteins and chemical_substances and then filter out the chemical_substances with connection having pvalue>0.005 to proteins
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:14330, key=n00, type=disease)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_key=e01, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6236:  # chunyu testing #623, this is a three-hop sample: DOID:14330 - protein - (physically_interacts_with) - chemical_substance - phenotypic_feature
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:14330, key=n00, type=disease)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n02)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_key=e01, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.001, remove_connected_nodes=t, qnode_key=n02)",
            "add_qnode(categories=biolink:PhenotypicFeature, key=n03)",
            "add_qedge(subject=n02, object=n03, key=e02)",
            "expand(edge_key=e02, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n02, object_qnode_key=n03, virtual_relation_label=FET3)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 6237:  # chunyu testing #623, this is a four-hop sample: CHEMBL521 - protein - biological_process - protein - disease
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(key=n00, ids=CHEMBL.COMPOUND:CHEMBL521, categories=biolink:ChemicalEntity)",
            "add_qnode(key=n01, is_set=true, categories=biolink:Protein)",
            "add_qedge(key=e00, subject=n00, object=n01)",
            "expand(edge_key=e00, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n00, object_qnode_key=n01, virtual_relation_label=FET1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_key=n01)",
            "add_qnode(type=biological_process, is_set=true, key=n02)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_key=e01, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n01, object_qnode_key=n02, virtual_relation_label=FET2)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_key=n02)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n03)",
            "add_qedge(subject=n02, object=n03, key=e02)",
            "expand(edge_key=e02, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n02, object_qnode_key=n03, virtual_relation_label=FET3)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=fisher_exact_test_p-value, direction=above, threshold=0.01, remove_connected_nodes=t, qnode_key=n03)",
            "add_qnode(type=disease, key=n04)",
            "add_qedge(subject=n03, object=n04, key=e03)",
            "expand(edge_key=e03, kp=ARAX/KG1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n03, object_qnode_key=n04, virtual_relation_label=FET4)",
            "resultify()",
            "return(message=true, store=false)"
        ]}}
    elif params.example_number == 7680:  # issue 768 test all but jaccard, uncomment any one you want to test
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:1588, key=n0)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n1)",
            "add_qedge(subject=n0, object=n1, key=e0)",
            "expand(edge_key=e0)",
            #"overlay(action=predict_drug_treats_disease)",
            #"overlay(action=predict_drug_treats_disease, subject_qnode_id=n1, object_qnode_key=n0, virtual_relation_label=P1)",
            #"overlay(action=overlay_clinical_info,paired_concept_frequency=true)",
            #"overlay(action=overlay_clinical_info,observed_expected_ratio=true)",
            #"overlay(action=overlay_clinical_info,chi_square=true)",
            #"overlay(action=overlay_clinical_info,paired_concept_frequency=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=CP1)",
            #"overlay(action=overlay_clinical_info,observed_expected_ratio=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=OE1)",
            #"overlay(action=overlay_clinical_info,chi_square=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=C1)",
            "overlay(action=fisher_exact_test, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=FET)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=15)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 7681:  # issue 768 with jaccard
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:14330, key=n00)",  # parkinsons
            "add_qnode(categories=biolink:Protein, is_set=True, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=False, key=n02)",
            "add_qedge(subject=n01, object=n00, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=15)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 7200:  # issue 720, example 2
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:14330, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            #"filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_key=n02)",
            #"filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
            #"overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
            "resultify(ignore_edge_direction=true, debug=true)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 885:
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:11830, key=n00)",
            "add_qnode(categories=biolink:Protein, is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=molecularly_interacts_with)",
            "expand(edge_id=[e00,e01], kp=RTX-KG2)",
            # overlay a bunch of clinical info
            "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C1)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C2)",
            "overlay(action=overlay_clinical_info, chi_square=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C3)",
            # return results
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 887:
        query = {"operations": {"actions": [
            "add_qnode(name=DOID:9406, key=n00)",
            "add_qnode(categories=biolink:ChemicalEntity, is_set=true, key=n01)",
            "add_qnode(categories=biolink:Protein, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=observed_expected_ratio, direction=below, threshold=3, remove_connected_nodes=t, qnode_key=n01)",
            "filter_kg(action=remove_orphaned_nodes, node_category=biolink:Protein)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n01, object_qnode_key=n02)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=normalized_google_distance, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_key=n02)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 892:  # drug disease prediction with BTE
        query = {"operations": {"actions": [
            "add_qnode(ids=DOID:11830, type=disease, key=n00)",
            "add_qnode(type=gene, ids=[UniProtKB:P39060, UniProtKB:O43829, UniProtKB:P20849], is_set=true, key=n01)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01)",
            "expand(kp=BTE)",
            "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
            "resultify(ignore_edge_direction=true)",
            "return(message=true, store=true)"
        ]}}
    elif params.example_number == 8922:  # drug disease prediction with BTE and KG2
        query = {"operations": {"actions": [
            "add_qnode(ids=DOID:11830, key=n0, type=disease)",
            "add_qnode(categories=biolink:ChemicalEntity, ids=n1)",
            "add_qedge(subject=n0, object=n1, ids=e1)",
            "expand(edge_id=e1, kp=RTX-KG2)",
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
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=DOID:11830, key=n0, type=disease)",
            "add_qnode(categories=biolink:ChemicalEntity, ids=n1)",
            "add_qedge(subject=n0, object=n1, ids=e1)",
            # "expand(edge_key=e00, kp=RTX-KG2)",
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
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=DOID:11830, key=n00, type=disease)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=RTX-KG2)",
            "expand(edge_key=e00, kp=BTE)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            "overlay(action=predict_drug_treats_disease)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=0.75, remove_connected_nodes=true, qnode_key=n01)",
            "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 8673:  # test_one_hop_based_on_types_1
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=MONDO:0001475, key=n00, type=disease)",
            "add_qnode(categories=biolink:Protein, key=n01, is_set=true)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n02)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "add_qedge(subject=n01, object=n02, key=e01, type=molecularly_interacts_with)",
            "expand(edge_id=[e00,e01], kp=RTX-KG2, continue_if_no_results=true)",
            #- expand(edge_id=[e00,e01], kp=BTE, continue_if_no_results=true)",
            "expand(edge_key=e00, kp=BTE, continue_if_no_results=true)",
            #- expand(edge_key=e00, kp=GeneticsKP, continue_if_no_results=true)",
            "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
            "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
            "overlay(action=overlay_clinical_info, chi_square=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n02)",
            #"overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n00, object_qnode_key=n01)",
            #"overlay(action=compute_ngd, virtual_relation_label=N2, subject_qnode_key=n00, object_qnode_key=n02)",
            #"overlay(action=compute_ngd, virtual_relation_label=N3, subject_qnode_key=n01, object_qnode_key=n02)",
            "resultify(ignore_edge_direction=true)",
            "filter_results(action=limit_number_of_results, max_results=100)",
            "return(message=true, store=true)",
        ]}}
    elif params.example_number == 9999:
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(name=acetaminophen, key=n0)",
            "add_qnode(categories=biolink:Protein, key=n1)",
            "add_qedge(subject=n0, object=n1, key=e0)",
            "expand(edge_key=e0)",
            "resultify()",
            "filter_results(action=limit_number_of_results, max_results=100)",
            "return(message=true, store=json)",
        ]}}
    elif params.example_number == 1492:
        query = {"operations": {"actions": [
            "create_message",
            "add_qnode(ids=MONDO:0005301, key=n0)",
            "add_qnode(categories=biolink:ChemicalEntity, key=n1)",
            "add_qedge(subject=n0, object=n1, key=e0, predicates=biolink:related_to)",
            "expand(kp=ClinicalRiskKP, edge_key=e0)",
            "overlay(action=compute_ngd, virtual_relation_label=N1, subject_qnode_key=n0, object_qnode_key=n1)",
            "resultify()",
            "return(message=true, store=true)",
        ]}}
    else:
        eprint(f"Invalid test number {params.example_number}. Try 1 through 17")
        return


    #### Execute the query
    araxq.query(query)
    response = araxq.response

    #### If the result was an error, just end here
    #if response.status != 'OK':
    #    print(response.show(level=ARAXResponse.DEBUG))
    #    return response

    #### Retrieve the TRAPI Response (envelope) and TRAPI Message from the result
    envelope = response.envelope
    message = envelope.message
    envelope.status = response.error_code
    envelope.description = response.message


    #### Print out the logging stream
    print(response.show(level=ARAXResponse.DEBUG))

    #### Print out the message that came back
    print(json.dumps(ast.literal_eval(repr(envelope)), sort_keys=True, indent=2))

    #### Other stuff that could be dumped
    #print(json.dumps(message.to_dict(),sort_keys=True,indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.query_graph)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.nodes)), sort_keys=True, indent=2))
    #print(response.show(level=ARAXResponse.DEBUG))

    print(f"Number of results: {len(message.results)}")

    #print(f"Drugs names in the KG: {[x.name for x in message.knowledge_graph.nodes if 'chemical_substance' in x.type or 'drug' in x.type]}")

    #print(f"Essence names in the answers: {[x.essence for x in message.results]}")
    print("Results:")
    for result in message.results:
        confidence = result.confidence
        if confidence is None:
            confidence = 0.0
        print("  -" + '{:6.3f}'.format(confidence) + f"\t{result.essence}")

    # print the response id at the bottom for convenience too:
    print(f"Returned response id: {envelope.id}")

if __name__ == "__main__": main()
