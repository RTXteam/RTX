#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
from datetime import datetime

from response import Response
from query_graph_info import QueryGraphInfo
from knowledge_graph_info import KnowledgeGraphInfo
from actions_parser import ActionsParser
from ARAX_filter import ARAXFilter

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
import ReasoningUtilities
from QueryGraphReasoner import QueryGraphReasoner

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/Feedback/")
from RTXFeedback import RTXFeedback


class ARAXQuery:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None


    def query_return_message(self,query):

        result = self.query(query)
        message = self.message
        if message is None:
            message = Message()
        message.message_code = result.error_code
        message.code_description = result.message
        message.log = result.messages
        return message


    def query(self,query):

        #### Define a default response
        response = Response()
        self.response = response
        response.info(f"ARAXQuery launching")

        #### Determine a plan for what to do based on the input
        result = self.examine_incoming_query(query)
        if result.status != 'OK':
            return response
        query_attributes = result.data

        #### If we have a previous message processing plan, handle that
        if "have_previous_message_processing_plan" in query_attributes:
            response.info(f"Found input processing plan. Sending to the ProcessingPlanExecutor")
            result = self.executeProcessingPlan(query)
            return response

        #### If we have a query_graph, pass this on to the QueryGraphReasoner
        if "have_query_graph" in query_attributes:
            response.info(f"Found input query_graph. Sending to the QueryGraphReasoner")
            qgr = QueryGraphReasoner()
            message = qgr.answer(query["message"]["query_graph"], TxltrApiFormat=True)
            #self.log_query(query,message,'new')
            rtxFeedback = RTXFeedback()
            rtxFeedback.connect()
            rtxFeedback.addNewMessage(message,query)
            rtxFeedback.disconnect()
            self.limit_message(message,query)
            self.message = message
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
            codeString = message.message_code
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
            os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/QuestionAnswering")
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

        #### If we got this far, then everything seems to be good enough to proceed
        return response



    def limit_message(self,message,query):
        if "max_results" in query and query["max_results"] is not None:
            if message.results is not None:
                if len(message.results) > query["max_results"]:
                    del message.results[query["max_results"]:]
                    message.code_description += " (output is limited to "+str(query["max_results"]) + " results)"



    #### Get a previously stored message for this query from the database
    def executeProcessingPlan(self,inputEnvelope):

        response = self.response
        response.debug(f"Entering executeProcessingPlan")
        messages = []
        message = None
        message_id = None
        query = None

        #### Pull out the main processing plan envelope
        envelope = PreviousMessageProcessingPlan.from_dict(inputEnvelope["previous_message_processing_plan"])

        #### Connect to the message store just once, even if we won't use it
        rtxFeedback = RTXFeedback()
        rtxFeedback.connect()

        #### If there are URIs provided, try to load them
        if envelope.previous_message_uris is not None:
            response.debug(f"Found previous_message_uris")
            for uri in envelope.previous_message_uris:
                response.debug(f"    messageURI={uri}")
                matchResult = re.match( r'http[s]://arax.rtx.ai/.*api/rtx/.+/message/(\d+)',uri,re.M|re.I )
                if matchResult:
                    referenced_message_id = matchResult.group(1)
                    response.debug(f"Found local RTX identifier corresponding to respond_id {referenced_message_id}")
                    response.debug(f"Loading message_id {referenced_message_id}")
                    referenced_message = rtxFeedback.getMessage(referenced_message_id)
                    #eprint(type(message))
                    if not isinstance(referenced_message,tuple):
                        response.debug(f"Original question was: "+referenced_message["original_question"])
                        messages.append(referenced_message)
                        message_id = referenced_message_id
                        query = { "query_type_id": referenced_message["query_type_id"], "restated_question": referenced_message["restated_question"], "terms": referenced_message["terms"] }
                    else:
                        response.error(f"Unable to load message_id {referenced_message_id}", error_code="CannotLoadMessageById")
                        return response

        #### If there are one or more previous_messages embedded in the POST, process them
        if envelope.previous_messages is not None:
            response.debug(f"Received previous_messages")
            for uploadedMessage in envelope.previous_messages:
                response.debug(f"uploadedMessage is a "+str(uploadedMessage.__class__))
                if str(uploadedMessage.__class__) == "<class 'swagger_server.models.message.Message'>":
                    if uploadedMessage.results:
                        message = ast.literal_eval(repr(uploadedMessage))
                        messages.append(message)

                        if message["terms"] is None:
                            message["terms"] = { "dummyTerm": "giraffe" }
                        if message["query_type_id"] is None:
                            message["query_type_id"] = "UnknownQ"
                        if message["restated_question"] is None:
                            message["restated_question"] = "Unknown question"
                        if message["original_question"] is None:
                            message["original_question"] = "Unknown question"

                        query = { "query_type_id": message["query_type_id"], "restated_question": message["restated_question"], "original_question": message["original_question"], "terms": message["terms"] }
                    else:
                        response.error(f"Uploaded message does not contain a results. May be the wrong format")
                        return response
                else:
                    response.error(f"Uploaded message is not of type Message. It is of type"+str(uploadedMessage.__class__))
                    return response


        #### Take different actions based on the number of messages we now have in hand
        n_messages = len(messages)
        if n_messages == 0:
            response.debug(f"No starting messages were referenced. Will start with a blank template Message")
        elif n_messages == 1:
            response.debug(f"A single Message is ready and in hand")
            message = messages[0]
        else:
            response.debug(f"Multiple Messages were uploaded or loaded by reference. Proper merging code awaits! Will use just the first one for now.")
            message = TxMessage.from_dict(messages[0])
            counter = 1
            while counter < n_messages:
                messageToMerge = TxMessage.from_dict(messages[counter])
                if messageToMerge.reasoner_id is None:
                    messageToMerge.reasoner_id = "Unknown"
                #if messageToMerge.reasoner_id != "RTX":
                #    messageToMerge = self.fix_message(query,messageToMerge,messageToMerge.reasoner_id)

                #finalMessage = self.merge_message(finalMessage,messageToMerge)
                counter += 1
        message = ast.literal_eval(repr(message))

        #### Examine the options that were provided and act accordingly
        optionsDict = {}
        if envelope.options:
            response.debug(f"Processing options were provided, but these are not implemented at the moment and will be ignored")
            for option in envelope.options:
                response.debug(f"   option="+option)
                optionsDict[option] = 1


        #### If there are processing_actions, then fulfill those
        processing_actions = []
        if envelope.processing_actions:
            response.debug(f"Found processing_actions")
            actions_parser = ActionsParser()
            result = actions_parser.parse(envelope.processing_actions)
            response.merge(result)
            if result.error_code != 'OK':
                return response

            #### Message suffers from a dual life as a dict and an object. above we seem to treat it as a dict. Fix that. FIXME
            #### Below we start treating it as and object. This should be the way forward.
            #### This is not a good place to do this, but may need to convert here
            from ARAX_messenger import ARAXMessenger
            from ARAX_expander import ARAXExpander
            from ARAX_overlay import ARAXOverlay
            from ARAX_filter_kg import ARAXFilterKG
            messenger = ARAXMessenger()
            expander = ARAXExpander()
            filter = ARAXFilter()
            overlay = ARAXOverlay()
            filter_kg = ARAXFilterKG()

            message = ARAXMessenger().from_dict(message)

            #### Process each action in order
            action_stats = { }
            actions = result.data['actions']
            for action in actions:
                response.debug(f"Considering action '{action['command']}' with parameters {action['parameters']}")
                nonstandard_result = False

                if action['command'] == 'create_message':
                    result = messenger.create()
                    message = result.data['message']
                elif action['command'] == 'add_qnode':
                    result = messenger.add_qnode(message,action['parameters'])
                elif action['command'] == 'add_qedge':
                    result = messenger.add_qedge(message,action['parameters'])
                elif action['command'] == 'expand':
                    result = expander.apply(message,action['parameters'])
                elif action['command'] == 'filter':
                    result = filter.apply(message,action['parameters'])
                elif action['command'] == 'query_graph_reasoner':
                    response.info(f"Sending current query_graph to the QueryGraphReasoner")
                    qgr = QueryGraphReasoner()
                    message = qgr.answer(ast.literal_eval(repr(message.query_graph)), TxltrApiFormat=True)
                    nonstandard_result = True
                elif action['command'] == 'return':
                    action_stats['return_action'] = action
                    break
                elif action['command'] == 'overlay':  # recognize the overlay command
                    result = overlay.apply(message, action['parameters'])
                elif action['command'] == 'filter_kg':  # recognize the filter_kg command
                    result = filter_kg.apply(message, action['parameters'])
                else:
                    response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
                    print(response.show(level=Response.DEBUG))
                    return response

                #### Merge down this result and end if we're in an error state
                if nonstandard_result is False:
                    response.merge(result)
                    if result.status != 'OK':
                        return response


            #### At the end, process the explicit return() action, or implicitly perform one
            return_action = { 'command': 'return', 'parameters': { 'message': 'false', 'store': 'false' } }
            if action is not None and action['command'] == 'return':
                return_action = action
                #### If an explicit one left out some parameters, set the defaults
                if 'store' not in return_action['parameters']:
                    return_action['parameters']['store'] == 'false'
                if 'message' not in return_action['parameters']:
                    return_action['parameters']['message'] == 'false'

            if return_action['parameters']['store'] == 'true':
                response.debug(f"Storing resulting Message")
                message_id = rtxFeedback.addNewMessage(message,query)

            self.message = message

            #### If asking for the full message back
            if return_action['parameters']['message'] == 'true':
                return response

            #### Else just the id is returned
            else:
                #return( { "status": 200, "message_id": str(finalMessage_id), "n_results": finalMessage['n_results'], "url": "https://arax.rtx.ai/api/rtx/v1/message/"+str(finalMessage_id) }, 200)
                #return( { "status": 200, "message_id": str(finalMessage_id), "n_results": finalMessage.n_results, "url": "https://arax.rtx.ai/api/rtx/v1/message/"+str(finalMessage_id) }, 200)
                return response



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
    elif params.example_number == 3:
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=True, id=n01)",
            "add_qnode(type=drug, id=n02)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 4:
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(name=hypertension, id=n00)",
            "add_qnode(type=protein, is_set=True, id=n01)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "expand(edge_id=e00)",
            "filter(maximum_results=2)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 5:  # test overlay with ngd: hypertension->protein
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(name=hypertension, id=n00)",
            "add_qnode(type=protein, is_set=True, id=n01)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=compute_ngd)",
            "filter(maximum_results=2)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 6:  # test overlay with overlay_clinical_info, paired_concept_freq via COHD. Atherosclerosis-[:has_phenotype]-(:phenotypic_feature)
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:1936, id=n00)",  # Atherosclerosis
            "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=has_phenotype)",
            "expand(edge_id=e00)",
            "overlay(action=overlay_clinical_info, paired_concept_freq=true)",
            "filter(maximum_results=2)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 7:  # stub to test out the compute_jaccard feature
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:14330, id=n00)",  # parkinsons
            "add_qnode(type=protein, is_set=True, id=n01)",
            "add_qnode(type=chemical_substance, is_set=true, id=n02)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 8:  # to test jaccard with known result
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:8398, id=n00)",  # osteoarthritis
            "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
            "add_qnode(type=disease, is_set=true, id=n02)",
            "add_qedge(source_id=n01, target_id=n00, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01)",
            "expand(edge_id=[e00,e01])",
            "return(message=true, store=false)",
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
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 10:  # test case of drug prediction
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:1588, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "return(message=true, store=false)",
        ]}}
    elif params.example_number == 11:  # test overlay with overlay_clinical_info, paired_concept_freq via COHD
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(curie=DOID:0060227, id=n00)",  # Adam's oliver
            "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00, type=has_phenotype)",
            "expand(edge_id=e00)",
            "overlay(action=overlay_clinical_info, paired_concept_freq=true)",
            "filter(maximum_results=2)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 12:  # dry run of example 2 #TODO!!!!!
        query = { "previous_message_processing_plan": { "processing_actions": [
            "create_message",
            "add_qnode(name=DOID:14330, id=n00)",
            "add_qnode(type=protein, is_set=true, id=n01)",
            "add_qnode(type=chemical_substance, is_set=true, id=n02)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "add_qedge(source_id=n01, target_id=n02, id=e01, type=physically_interacts_with)",
            "expand(edge_id=[e00,e01])",
            "overlay(action=compute_jaccard, start_node_id=n00, intermediate_node_id=n01, end_node_id=n02, virtual_edge_type=J1)",
            "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_id=n02)",
            "return(message=true, store=false)",
            ] } }
    elif params.example_number == 13:  # add pubmed id's
        query = {"previous_message_processing_plan": {"processing_actions": [
            "create_message",
            "add_qnode(name=DOID:1227, id=n00)",
            "add_qnode(type=chemical_substance, is_set=true, id=n01)",
            "add_qedge(source_id=n00, target_id=n01, id=e00)",
            "expand(edge_id=e00)",
            "overlay(action=add_node_pmids, max_num=10)",
            "return(message=true, store=false)"
        ]}}
    else:
        eprint(f"Invalid test number {params.example_number}. Try 1 through 7")
        return

    if 0:
        message = araxq.query_return_message(query)
        print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))
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
    #print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.edges)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.query_graph)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.knowledge_graph.nodes)), sort_keys=True, indent=2))
    #print(json.dumps(ast.literal_eval(repr(message.id)), sort_keys=True, indent=2))
    #print(response.show(level=Response.DEBUG))
    print(response.show(level=Response.DEBUG))
    # ids = ['UniProtKB:P02675',
    #         'UniProtKB:P01375',
    #         'UniProtKB:P15559',
    #         'UniProtKB:P06213',
    #         'UniProtKB:P05231',
    #         'UniProtKB:Q99683',
    #         'UniProtKB:P10635',
    #         'UniProtKB:Q01959',
    #         'UniProtKB:P21728',
    #         'UniProtKB:P21397',
    #         'UniProtKB:P10636',
    #         'UniProtKB:P08183',
    #         'UniProtKB:P04062',
    #         'UniProtKB:P14416',
    #         'UniProtKB:Q5S007',
    #         'UniProtKB:P27338',
    #         'UniProtKB:P37840',
    #         'UniProtKB:P08069']
    vals = []
    for edge in message.knowledge_graph.edges:
        if hasattr(edge, 'edge_attributes') and edge.edge_attributes and len(edge.edge_attributes) >= 1:
            vals.append(edge.edge_attributes.pop().value)
    #        if edge.source_id in ids:
    #            print(edge.source_id)
    #        if edge.target_id in ids:
    #             print(edgge.target_id)
    print(sorted(vals))
    for node in message.knowledge_graph.nodes:
        print(f"{node.name} {node.type[0]}")
    #     print(node.qnode_id)


if __name__ == "__main__": main()
