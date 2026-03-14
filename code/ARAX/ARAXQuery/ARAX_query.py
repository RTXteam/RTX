import copy
import sys
import os
import json
import re
import time
from datetime import datetime
import traceback
import threading
import requests
import gc
import contextlib

from ARAX_response import ARAXResponse
from actions_parser import ActionsParser
from ARAX_filter import ARAXFilter
from ARAX_query_graph_interpreter import ARAXQueryGraphInterpreter
from ARAX_messenger import ARAXMessenger
from ARAX_ranker import ARAXRanker
from operation_to_ARAXi import WorkflowToARAXi
from ARAX_query_tracker import ARAXQueryTracker
from result_transformer import ResultTransformer

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.response import Response
from openapi_server.models.message import Message
from openapi_server.models.operations import Operations

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ResponseCache")
from response_cache import ResponseCache  #noqa: E402

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)


ARAXResponse.output = 'STDERR'

null_context_manager = contextlib.nullcontext()


class response_locking(ARAXResponse):
    def __init__(self, lock: threading.Lock):
        self.lock = lock
        super().__init__()

    def __add_message(self, message, level, code=None):
        with self.lock:
            super()._add_message(message, level, code)

class ARAXQuery:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.rtxConfig = RTXConfiguration()
        self.lock = None

    def handle_memory_error(self, e):
        with self.lock if self.lock is not None else null_context_manager:
            self.response.envelope.message.results = []
        gc.collect()
        print("[asynchronous_query]: " + repr(e), file=sys.stderr)
        with self.lock if self.lock is not None else null_context_manager:
            self.response.error("ARAX ran out of memory during query processing; no results will be returned for this query")

    @staticmethod
    def query_tracker_reset():
        query_tracker_reset = ARAXQueryTracker()
        query_tracker_reset.clear_unfinished_entries()
        del query_tracker_reset


    def query_return_stream(self, query, mode='ARAX'):

        main_query_thread = threading.Thread(target=self.asynchronous_query, args=(query,mode,))
        self.lock = threading.Lock()
        main_query_thread.start()

        if self.response is None or "DONE" not in self.response.status:

            # Sleep until a response object has been created
            have_response = False
            while not have_response:
                with self.lock:
                    have_response = (self.response is not None)
                if not have_response:
                    time.sleep(0.1)

            try:
                i_message = 0
                with self.lock:
                    n_messages = len(self.response.messages)
                query_plan_counter = 0
                idle_ticks = 0.0
                pid = None

                self.response.debug("In query_return_stream")

                response_status_says_done = False
                while not response_status_says_done:
                    with self.lock:
                        response_status_says_done = ("DONE" in self.response.status)
                    if response_status_says_done:
                        break
                    with self.lock:
                        n_messages = len(self.response.messages)
                    while i_message < n_messages:
                        with self.lock:
                            i_message_obj = self.response.messages[i_message].copy()
                        yield(json.dumps(i_message_obj, allow_nan=False) + "\n")
                        i_message += 1
                        idle_ticks = 0.0

                    if pid is None:
                        pid = os.getpid()
                        authorization = str(hash('Pickles' + str(pid)))
                        yield(json.dumps( { "pid": pid, "authorization": authorization } )+"\n")

                    #### Also emit any updates to the query_plan
                    with self.lock:
                        self_query_plan_counter = self.response.query_plan['counter']
                    if query_plan_counter < self_query_plan_counter:
                        query_plan_counter = self_query_plan_counter
                        with self.lock:
                            self_response_query_plan = self.response.query_plan.copy()
                        yield(json.dumps(self_response_query_plan, allow_nan=False, sort_keys=True) + "\n")
                        idle_ticks = 0.0
                    time.sleep(0.2)
                    idle_ticks += 0.2
                    if idle_ticks > 180.0:
                        timestamp = str(datetime.now().isoformat())
                        yield json.dumps({ 'timestamp': timestamp, 'level': 'DEBUG', 'code': '', 'message': 'Query is still progressing...' }) + "\n"
                        idle_ticks = 0.0
            except MemoryError as e:
                self.handle_memory_error(e)

                # #### If there are any more logging messages in the queue, send them first
            n_messages = len(self.response.messages)
            while i_message < n_messages:
                yield(json.dumps(self.response.messages[i_message], allow_nan=False) + "\n")
                i_message += 1

            #### Also emit any updates to the query_plan
            self_response_query_plan_counter = self.response.query_plan['counter']
            if query_plan_counter < self_response_query_plan_counter:
                query_plan_counter = self_response_query_plan_counter
                yield(json.dumps(self.response.query_plan, allow_nan=False, sort_keys=True) + "\n")

            # Remove the little DONE flag the other thread used to signal this thread that it is done
            self.response.status = re.sub('DONE,', '', self.response.status)

            #### Switch OK to Success for TRAPI compliance
            if self.response.envelope.status == 'OK':
                self.response.envelope.status = 'Success'

            # Stream the resulting message back to the client
            try:
                msg_str = json.dumps(self.response.envelope.to_dict(),
                                     allow_nan=False,
                                     sort_keys=True) + "\n"
            except ValueError as v:
                self.response.envelope.message.results = []
                self.response.envelope.message.auxiliary_graphs = None
                self.response.envelope.message.knowledge_graph = {'edges': dict(), 'nodes': dict()}
                self.response.envelope.status = 'ERROR'
                error_message_str = f"error dumping result to JSON: {str(v)}"
                self.response.error(error_message_str)
                eprint(error_message_str)
                msg_str = json.dumps(self.response.envelope.to_dict(),
                                     sort_keys=True) + "\n"
            yield msg_str

        # Wait until both threads rejoin here and the return
        main_query_thread.join()
        self.track_query_finish()
        return


    def asynchronous_query(self,query, mode='ARAX'):

        try:
            #### Define a new response object if one does not yet exist
            with self.lock:
                have_response = self.response is not None
            if not have_response:
                new_response = response_locking(self.lock)
                with self.lock:
                    self.response = new_response

            self.response.debug("in asynchronous_query")

            #### Execute the query
            self.query(query, mode=mode, origin='API')

        except MemoryError as e:
            self.handle_memory_error(e)


        # Insert a little flag into the response status to denote that this thread is done
        with self.lock:
            self.response.status = f"DONE,{self.response.status}"

        return


    ########################################################################################
    def query_return_message(self, query, mode='ARAX'):

        self.response = ARAXResponse()
        response = self.response
        response.debug("in query_return_message")

        self.query(query, mode=mode, origin='API')

        #### If the query ended in an error, copy the error to the envelope
        if response.status != 'OK':
            response.envelope.status = response.error_code
            response.envelope.description = response.message
            if hasattr(response,'http_status'):
                response.envelope.http_status = response.http_status
            self.track_query_finish()
            return response.envelope

        if mode == 'asynchronous':
            attributes = {
                'status': 'Running Async',
                'message_id': None,
                'message_code': 'Running',
                'code_description': 'Query running via /asyncquery (parent)'
            }
            query_tracker = ARAXQueryTracker()
            if hasattr(self.response, 'job_id'):
                query_tracker.update_tracker_entry(self.response.job_id, attributes)
        else:
            self.track_query_finish()
            #### Switch OK to Success for TRAPI compliance
            response.envelope.status = 'Success'


        return response.envelope


    ########################################################################################
    def track_query_finish(self):

        query_tracker = ARAXQueryTracker()
        try:
            response_id = self.response.response_id
        except (AttributeError, TypeError):
            response_id = None

        attributes = {
            'status': 'Completed',
            'message_id': response_id,
            'message_code': self.response.error_code,
            'code_description': self.response.message
        }

        if hasattr(self.response, 'job_id'):
            query_tracker.update_tracker_entry(self.response.job_id, attributes)
        else:
            # Sometimes we finish without a job_id having been created, and that's okay
            pass



    ########################################################################################
    def query(self, query, mode='ARAX', origin='local'):

        #### Create the skeleton of the response
        response = self.response
        if response is None:  # At this point in the code, the response should only be
                              # None in regression tests that call ARAXQuery.query() directly
            response = ARAXResponse()
            self.response = response

        #### Announce the launch of query()
        #### Note that setting ARAXResponse.output = 'STDERR' means that we get noisy output to the logs
        response.info(f"{mode} Query launching on incoming Query")
        response.debug(f"RTXConfiguration says maturity={self.rtxConfig.maturity}, "
                       f"current_branch={self.rtxConfig.current_branch_name}, "
                       f"is_itrb_instance={self.rtxConfig.is_itrb_instance}, "
                       f"arax_version={self.rtxConfig.arax_version}, "
                       f"trapi_version={self.rtxConfig.trapi_version}")

        #### Create an empty envelope
        messenger = ARAXMessenger()
        messenger.create_envelope(response)

        #### Preserve the query_options
        if 'query_options' in query and query['query_options'] is not None:
            response.envelope.query_options = query['query_options']
        else:
            response.envelope.query_options = {}

        #### Need to put certain input Query parameters into query_options to later use by Expand et al.
        if 'return_minimal_metadata' in query:
            response.envelope.query_options['return_minimal_metadata'] = query['return_minimal_metadata']

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
        job_id = None
        if origin == 'API':
            query_tracker = ARAXQueryTracker()
            if 'remote_address' in query and query['remote_address'] is not None:
                remote_address = query['remote_address']
            else:
                remote_address = '????'
            attributes = { 'submitter': response.envelope.submitter, 'input_query': query, 'remote_address': remote_address }
            job_id = query_tracker.create_tracker_entry(attributes)

            if job_id == -999:
                response.error("Query could not be run due to exceeded limits", error_code="OverLimit", http_status=429)
                return response

        response.job_id = job_id

        try:
            #### Determine a plan for what to do based on the input
            #eprint(json.dumps(query, indent=2, sort_keys=True))
            result = self.examine_incoming_query(query, mode=mode)
            if result.status != 'OK':
                return response
            query_attributes = result.data

            #### Convert the message from dicts to objects
            if 'message' in query:
                response.debug("Deserializing message")
                query['message'] = ARAXMessenger().from_dict(query['message'])

            # If there is a workflow, translate it to ARAXi and append it to the operations actions list
            if "have_workflow" in query_attributes:
                if query['message'].query_graph is None:
                    response.error("Cannot have a workflow with an null query_graph", error_code="MissingQueryGraph")
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
                    response.info("Found input query_graph. Interpreting it and generating ARAXi processing plan to answer it")
                    interpreter = ARAXQueryGraphInterpreter()
                    interpreter.translate_to_araxi(response)
                    if response.status != 'OK':
                        return response
                    query['operations'] = {}
                    query['operations']['actions'] = result.data['araxi_commands']

                #### Else the mode is KG2 mode, where we just accept one-hop queries, and run a simple ARAXi
                else:
                    response.info("Found input query_graph. Querying RTX KG2 to answer it")
                    if len(response.envelope.message.query_graph.nodes) > 2:
                        response.error("Only 1 hop (2 node) queries can be handled at this time", error_code="TooManyHops")
                        return response
                    query['operations'] = {}
                    query['operations']['actions'] = [ 'expand(kp=infores:rtx-kg2)', 'resultify()', 'return(store=false)' ]

                query_attributes['have_operations'] = True


            #### If we have operations, execute them
            if "have_operations" in query_attributes:
                response.info("Found input processing plan. Sending to the ProcessingPlanExecutor")
                result = self.execute_processing_plan(query, mode=mode)

            #### This used to support canned queries, but no longer does
            else:
                response.error("Unable to determine ARAXi to execute. Error Q213", error_code="UnknownError")

        except MemoryError as e:
            self.handle_memory_error(e)

        return response


    #######################################################################################
    def examine_incoming_query(self, query, mode='ARAX'):

        response = self.response
        response.info("Examine input Query for needed information for dispatch")
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
        response.info("Converting workflow elements to ARAXi")

        # Convert the TRAPI workflow into ARAXi
        converter = WorkflowToARAXi()
        araxi = converter.translate(query['workflow'], query['message'].query_graph.to_dict(), response)
        # The translation returns a list of ARAXi commands. If this list is empty, something went wrong
        # When convert_workflow_to_ARAXi is called, it's wrapped in a try/except, so raise an Exception to indicate
        # that something went wrong
        if not araxi:
            response.error("Unable to translate workflow into ARAXi", error_code="TranslationFailed")
            raise Exception

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
        response.info("Validating the input query graph")

        # Define allowed qnode and qedge attributes to check later
        allowed_qnode_attributes = { 'ids': 1, 'categories':1, 'is_set': 1, 'set_interpretation': 1, 'set_id': 1, 'member_ids': 1, 'option_group_id': 1, 'name': 1, 'constraints': 1 }
        allowed_qedge_attributes = { 'predicates': 1, 'subject': 1, 'object': 1, 'option_group_id': 1, 'exclude': 1, 'relation': 1, 'attribute_constraints': 1, 'qualifier_constraints': 1, 'knowledge_type': 1 }

        #### Loop through nodes checking the attributes
        for id,qnode in message['query_graph']['nodes'].items():
            for attr in qnode:
                if attr not in allowed_qnode_attributes:
                    response.error(f"QueryGraph node '{id}' has an unexpected property '{attr}'. This property is not understood and therefore processing is halted, rather than answer an incompletely understood query", error_code="UnknownQNodeProperty")
                    return response

        #### Check to ensure that either edges EOR paths is present
        if 'edges' not in message['query_graph'] and 'paths' not in message['query_graph']:
            response.error("QueryGraph is missing both 'edges' and 'paths'. At least one must be present.", error_code="MissingQEdgeAndQPath")
            return response

        #### Loop through edges checking the attributes
        if 'edges' in message['query_graph']:
            for id,qedge in message['query_graph']['edges'].items():
                for attr in qedge:
                    if attr not in allowed_qedge_attributes:
                        if attr == 'predicate':
                            response.error(f"QueryGraph edge '{id}' has an obsolete property '{attr}'. This property should be plural 'predicates' in TRAPI 1.4 and higher. Your query may be TRAPI 1.3 or lower and should be checked carefully and migrated to TRAPI 1.4", error_code="UnknownQEdgeProperty")
                        else:
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
        response.debug("Entering execute_processing_plan")
        messages = []
        message = None

        # If there is already a message (perhaps with a query_graph) already in the query, preserve it
        if 'message' in input_operations_dict and input_operations_dict['message'] is not None:
            incoming_message = input_operations_dict['message']
            if isinstance(incoming_message,dict):
                incoming_message = Message.from_dict(incoming_message)
            messages = [ incoming_message ]

        #### Pull out the main processing plan
        operations = Operations.from_dict(input_operations_dict["operations"])

        #### Connect to the message store just once, even if we won't use it
        response.debug("Connecting to ResponseCache")
        response_cache = ResponseCache()  #  also calls connect

        #### Create a messenger object for basic message processing
        response.debug("Creating ARAXMessenger instance")
        messenger = ARAXMessenger()

        #### If there are URIs provided, try to load them
        force_remote = False
        if operations.message_uris is not None:
            response.debug("Found message_uris")
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
            response.debug("Received messages")
            for uploadedMessage in operations.messages:
                response.debug("uploadedMessage is a "+str(uploadedMessage.__class__))
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
                        response.warning("There are no results in this uploaded message, but maybe that's okay")
                else:
                    response.error("Uploaded message is not of type Message. It is of type "+str(uploadedMessage.__class__))
                    return response

        #### Take different actions based on the number of messages we now have in hand
        n_messages = len(messages)

        #### If there's no input message, then create one
        if n_messages == 0:
            response.debug("No starting messages were referenced. Will start with a blank template Message")
            messenger.create_envelope(response)

            message = response.envelope.message

        #### If there's on message, we will run with that
        elif n_messages == 1:
            response.debug("A single Message is ready and in hand")
            message = messages[0]
            response.envelope.message = message

        #### Multiple messages unsupported
        else:
            response.warning("Multiple Messages were uploaded or imported by reference. However, proper merging code has not been implemented yet! Will use just the first Message for now.")
            message = messages[0]

        #### Examine the options that were provided and act accordingly
        optionsDict = {}
        if operations.options:
            response.debug("Processing options were provided, but these are not implemented at the moment and will be ignored")
            for option in operations.options:
                response.debug("   option="+option)
                optionsDict[option] = 1

        # Save the original input query for later reference
        if mode != "RTXKG2" and response.envelope.message.query_graph and response.envelope.message.query_graph.nodes and not hasattr(response, "original_query_graph"):
            response.original_query_graph = copy.deepcopy(response.envelope.message.query_graph)
            edge_or_path_text = ''
            if hasattr(response.original_query_graph,'edges'):
                edge_or_path_text += f" and qedges {str(response.original_query_graph.edges)})"
            if hasattr(response.original_query_graph,'paths'):
                edge_or_path_text += f" and paths {str(response.original_query_graph.paths)})"
            response.debug(f"Saving original query graph (has qnodes {set(response.original_query_graph.nodes)}{edge_or_path_text}")

        #### If there are actions, then fulfill those
        if operations.actions:
            response.debug("Found actions")
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
            from ARAX_infer import ARAXInfer
            from ARAX_connect import ARAXConnect
            expander = ARAXExpander()
            filter = ARAXFilter()
            overlay = ARAXOverlay()
            filter_kg = ARAXFilterKG()
            resultifier = ARAXResultify()
            filter_results = ARAXFilterResults()
            infer = ARAXInfer()
            connect = ARAXConnect()
            self.message = message

            #### Create some empty stubs if they don't exist
            if message.results is None:
                message.results = []


            #### If the mode is asynchronous, then fork here. The parent returns the response thus far that everything checks out and is proceeding
            #### and the child continues to work on the query, eventually to finish and exit()
            if mode == 'asynchronous':
                callback = input_operations_dict['callback']
                if callback.startswith('http://localhost'):
                    response.error(f"ERROR: A callback to localhost ({callback}) does not work. Please specify a resolvable callback URL")
                    return response

                response.info(f"Everything seems in order to begin processing the query asynchronously. Processing will continue and Response will be posted to {callback}")
                newpid = os.fork()
                #### The parent returns to tell the caller that work will proceed
                if newpid > 0:
                    response.envelope.status = 'Running'
                    response.envelope.description = 'Asynchronous answering of query underway'
                    return response
                #### The child continues
                #### The child loses the MySQL connection of the parent, so need to reconnect
                time.sleep(1)
                response_cache.connect()
                time.sleep(1)

                child_pid = os.getpid()
                response.debug(f"Child continues running. Child PID is {child_pid}. Record with alter_tracker_entry()")
                attributes = {
                    'pid': child_pid,
                    'code_description': 'Query executing via /asyncquery (child)'
                }
                query_tracker = ARAXQueryTracker()
                alter_result = query_tracker.alter_tracker_entry(self.response.job_id, attributes)
                response.debug(f"Child PID {child_pid} recorded with result {alter_result}")


            #### If there is already a KG with edges, recompute the qg_keys
            if message.knowledge_graph is not None and len(message.knowledge_graph.edges) > 0:
                resultifier.recompute_qg_keys(response)

            #### Process each action in order
            action_stats = { }
            actions = result.data['actions']
            action = None
            for action in actions:
                response.info(f"Processing action '{action['command']}' with parameters {action['parameters']}")

                # Catch a crash
                try:
                    if action['command'] == 'create_message' or action['command'] == 'create_envelope':
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
                        self.inject_int_value_into_parameters('kp_timeout', response.envelope.query_options, action['parameters'], 'UserTimeoutNotInt')
                        self.inject_int_value_into_parameters('prune_threshold', response.envelope.query_options, action['parameters'], 'PruneThresholdNotInt')
                        self.inject_boolean_value_into_parameters('return_minimal_metadata', response.envelope.query_options, action['parameters'], 'InternalError')
                        if response.status == 'ERROR':
                            if mode == 'asynchronous':
                                self.send_to_callback(callback, response)
                            return response
                        expander.apply(response, action['parameters'], mode=mode)

                    elif action['command'] == 'filter':
                        filter.apply(response,action['parameters'])

                    elif action['command'] == 'resultify':
                        resultifier.apply(response, action['parameters'], mode=mode)

                    elif action['command'] == 'scoreless_resultify':
                        resultifier.apply(response, action['parameters'], mode=mode)

                    elif action['command'] == 'overlay':  # recognize the overlay command
                        overlay.apply(response, action['parameters'])

                    elif action['command'] == 'filter_kg':  # recognize the filter_kg command
                        filter_kg.apply(response, action['parameters'])

                    elif action['command'] == 'infer':  # recognize the infer command
                        infer.apply(response, action['parameters'])

                    elif action['command'] == 'filter_results':  # recognize the filter_results command
                        response.debug(f"Before filtering, there are {len(response.envelope.message.results)} results")
                        filter_results.apply(response, action['parameters'])
                        response.debug(f"After filtering, there are {len(response.envelope.message.results)} results")

                    elif action['command'] == 'connect':
                        connect.apply(response, action['parameters'])

                    elif action['command'] == 'return':
                        action_stats['return_action'] = action
                        break

                    elif action['command'] == 'rank_results':
                        response.info("Running experimental reranker on results")
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
                if action['command'] == 'resultify' and mode != 'RTXKG2':
                    response.info("Running experimental reranker on results")
                    try:
                        ranker = ARAXRanker()
                        ranker.aggregate_scores_dmk(response)
                    except Exception as error:
                        exception_type, exception_value, exception_traceback = sys.exc_info()
                        response.error(f"An uncaught error occurred: {error}: {repr(traceback.format_exception(exception_type, exception_value, exception_traceback))}", error_code="UncaughtARAXiError")
                        if mode == 'asynchronous':
                            self.send_to_callback(callback, response)
                        return response

            if mode != 'RTXKG2':  # KG2 doesn't use virtual edges or edit the QG, so no transformation needed
                result_transformer = ResultTransformer()
                response.debug(f"Calling ResultTransformer; number of results is: {len(response.envelope.message.results)}")
                result_transformer.transform(response)
                response.debug(f"Results have been transformed; number of results is: {len(response.envelope.message.results)}")

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

            #### Provide the total results count in the Response if it is available
            try:
                response.envelope.total_results_count = response.total_results_count
            except (AttributeError, TypeError):
                pass

            #response.envelope.operations['actions'] = operations.actions

            # Update the resource_id to ARAX if not already present
            for result in response.envelope.message.results:
                if result.resource_id is None:
                    result.resource_id = 'infores:arax'

            # Store the validation and provenance metadata
            #trapi_version = '1.2.0'
            #try:
            #    validate(response.envelope,'Response',trapi_version)
            #    if 'description' not in response.envelope or response.envelope['description'] is None:
            #        response.envelope['description'] = 'reasoner-validator: PASS'
            #    response.envelope['validation_result'] = { 'status': 'PASS', 'version': trapi_version, 'message': '' }

            #except ValidationError as error:
            #    timestamp = str(datetime.now().isoformat())
            #    if 'logs' not in response.envelope or response.envelope['logs'] is None:
            #        response.envelope['logs'] = []
            #    response.envelope['logs'].append( { "code": 'InvalidTRAPI', "level": "ERROR", "message": "TRAPI validator reported an error: " + str(error),
            #                                        "timestamp": timestamp } )
            #    if 'description' not in reponse.envelope or response.envelope['description'] is None:
            #        response.envelope['description'] = ''
            #    response.envelope['description'] = 'ERROR: TRAPI validator reported an error: ' + str(error) + ' --- ' + response.envelope['description']
            #    response.envelope['validation_result'] = { 'status': 'FAIL', 'version': trapi_version, 'message': 'TRAPI validator reported an error: ' + str(error) + ' --- ' + response.envelope['description'] }


            #from ARAX_attribute_parser import ARAXAttributeParser
            #attribute_parser = ARAXAttributeParser(response.envelope,response.envelope['message'])
            #response.envelope.validation_result['provenance_summary'] = attribute_parser.summarize_provenance_info()
            #
            #response.envelope.validation_result = { 'status': 'PASS', 'version': trapi_version, 'size': '?', 'message': '' }
            #

            #### Switch OK to Success for TRAPI compliance
            if response.envelope.status == 'OK':
                response.envelope.status = 'Success'

            if response.envelope.query_options is None:
                response.envelope.query_options = {}
            response.envelope.query_options['query_plan'] = response.query_plan

            # If store=true, then put the message in the database
            response_id = None
            if return_action['parameters']['store'] == 'true':
                response.debug("Storing resulting Message")
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
                    response.info("Processing is complete. Attempting to send the result to the callback URL.")
                    self.send_to_callback(callback, response)
                else:
                    response.info("Processing is complete. Transmitting resulting Message back to client.")
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
        envelope_dict = response.envelope.to_dict()
        post_succeeded = False
        send_attempts = 0
        timeout = 300

        while send_attempts < 3 and not post_succeeded:
            response.info(f"Attempting to send (with timeout {timeout}) the Response to callback URL: {callback}")
            try:
                post_response_content = requests.post(callback, json=envelope_dict, headers={'accept': 'application/json'}, timeout=timeout)
                status_code = post_response_content.status_code
                if status_code in [ 200, 201 ]:
                    response.info(f"POST to callback URL succeeded with status code {status_code}")
                    post_succeeded = True
                else:
                    response.warning(f"POST to callback URL failed with status code {status_code}")

            except Exception as error:
                if 'Read timed out' in f"{error}":
                    response.warning(f"Attempt to send Response to callback URL {callback} timed out after {timeout} seconds. We will assume that it was received but just not acknowledged")
                    post_succeeded = True
                else:
                    response.warning(f"Unable to make a connection to callback URL {callback} with error {error}")

            send_attempts += 1
            if not post_succeeded:
                response.info("Wait 10 seconds before trying again")
                time.sleep(10)

        if not post_succeeded:
            response.error(f"Did not received a positive acknowledgement from sending the Response to callback URL {callback} after {send_attempts} tries. Work may be lost", error_code="UnreachableCallback")

        self.track_query_finish()
        os._exit(0)


    ############################################################################################
    def inject_int_value_into_parameters(self, parameter_name, query_options, parameters, error_code):
        parameter_value = None
        if query_options is not None and parameter_name in query_options and query_options[parameter_name] is not None:
            parameter_value = query_options[parameter_name]
            #### Try to convery the value to an integer
            try:
                parameter_value = int(parameter_value)
            except (ValueError, TypeError):
                self.response.error(f"Unable to convert parameter {parameter_name} = '{parameter_value}' into an integer", error_code=error_code)
                return
        #### Only update the value in parameters if one was not explicitly specified
        if parameter_name not in parameters and parameter_value is not None:
            parameters[parameter_name] = parameter_value


    ############################################################################################
    def inject_boolean_value_into_parameters(self, parameter_name, query_options, parameters, error_code):
        parameter_value = False
        if query_options is not None and parameter_name in query_options and query_options[parameter_name] is not None:
            if query_options[parameter_name] is True:
                parameter_value = True
        parameters[parameter_name] = parameter_value


##################################################################################################
def stringify_dict(inputDict):
    outString = "{"
    for key,value in sorted(inputDict.items(), key=lambda t: t[0]):
        if outString != "{":
            outString += ","
        outString += "'"+str(key)+"':'"+str(value)+"'"
    outString += "}"
    return(outString)
