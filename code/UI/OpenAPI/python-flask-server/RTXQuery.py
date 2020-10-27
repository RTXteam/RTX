#!/usr/bin/python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import re
import os
import sys
import subprocess
import json
import datetime
import ast
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")
from RTXConfiguration import RTXConfiguration

from swagger_server.models.message import Message
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/QuestionAnswering/")
from ParseQuestion import ParseQuestion
from Q0Solution import Q0
import ReasoningUtilities
from QueryGraphReasoner import QueryGraphReasoner

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/kg-construction/")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/SemMedDB/")
from SynonymMapper import SynonymMapper

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../Feedback/")
from RTXFeedback import RTXFeedback


class RTXQuery:

    def query(self,query):

        #### Get our configuration information
        
        #### Create a Message object as a response
        response = Message()
        execution_string = None

        #### Determine a plan for what to do based on the input
        result = self.examine_incoming_query(query)
        if result["message_code"] != "OK":
            response.message_code = result["message_code"]
            response.code_description = result["code_description"]
            return response

        #### If we have a previous message processing plan, handle that
        if "have_previous_message_processing_plan" in result:
            rtxFeedback = RTXFeedback()       # FIXME. This should be a separate class I think, not the Feedback class. TODO: Separate them
            rtxFeedback.connect()
            message = rtxFeedback.processExternalPreviousMessageProcessingPlan(query)
            rtxFeedback.disconnect()
            return(message)

        #### If we have a query_graph, pass this on to the QueryGraphReasoner
        if "have_query_graph" in result:
            qgr = QueryGraphReasoner()
            message = qgr.answer(query["message"]["query_graph"], TxltrApiFormat=True)
            #self.log_query(query,message,'new')
            rtxFeedback = RTXFeedback()
            rtxFeedback.connect()
            rtxFeedback.addNewMessage(message,query)
            rtxFeedback.disconnect()
            self.limit_message(message,query)
            return(message)


        #### Otherwise extract the id and the terms from the incoming parameters
        else:
            id = query["message"]["query_type_id"]
            terms = query["message"]["terms"]

        #### Check to see if the query_options indicates to query named resource and integrate the results
        if "have_query_type_id_and_terms" in result and "message" in query and "query_options" in query["message"] and "integrate" in query["message"]["query_options"]:
            response = self.integrate(query)
            #self.log_query(query,response,'remote')
            return response

        #### Create an RTX Feedback management object
        #eprint(query)
        rtxFeedback = RTXFeedback()
        rtxFeedback.connect()
        cachedMessage = rtxFeedback.getCachedMessage(query)

        #### If we can find a cached message for this query and this version of RTX, then return the cached message
        if ( cachedMessage is not None ):
            apiMessage = Message().from_dict(cachedMessage)
            rtxFeedback.disconnect()
            self.limit_message(apiMessage,query)

            if apiMessage.message_code is None:
                if apiMessage.result_code is not None:
                    apiMessage.message_code = apiMessage.result_code
                else:
                    apiMessage.message_code = "wha??"

            self.log_query(query,apiMessage,'cached')
            return apiMessage

        #### Still have special handling for Q0
        if id == 'Q0':
            q0 = Q0()
            message = q0.answer(terms["term"],use_json=True)
            if 'original_question' in query["message"]:
              message.original_question = query["message"]["original_question"]
              message.restated_question = query["message"]["restated_question"]
            message.query_type_id = query["message"]["query_type_id"]
            message.terms = query["message"]["terms"]
            id = message.id
            codeString = message.message_code
            self.log_query(query,message,'new')
            rtxFeedback.addNewMessage(message,query)
            rtxFeedback.disconnect()
            self.limit_message(message,query)
            return(message)

        #### Else call out to original solution scripts for an answer
        else:

            #### If some previous processing has determined what the solution script to use is, then use that
            if execution_string is not None:
                command = "python3 " + execution_string

            #### Else use the ParseQuestion system to determine what the execution_string should be
            else:
                txltr = ParseQuestion()
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
                message = Message()
                message.message_code = "InternalError"
                message.code_description = "Error parsing the message from the reasoner. This is an internal bug that needs to be fixed. Unable to respond to this question at this time. The unparsable message was: " + reformattedText

            #print(query)
            if 'original_question' in query["message"]:
                message.original_question = query["message"]["original_question"]
                message.restated_question = query["message"]["restated_question"]
            message.query_type_id = query["message"]["query_type_id"]
            message.terms = query["message"]["terms"]

            #### Log the result and return the Message object
            self.log_query(query,message,'new')
            rtxFeedback.addNewMessage(message,query)
            rtxFeedback.disconnect()

            #### Limit message
            self.limit_message(message,query)
            return(message)


        #### If the query type id is not triggered above, then return an error
        message = Message()
        message.message_code = "UnsupportedQueryTypeID"
        message.code_description = "The specified query id '" + id + "' is not supported at this time"
        rtxFeedback.disconnect()
        return(message)


    def log_query(self,query,message,cacheStatus):
        datetimeString = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "query_type_id" not in query["message"] or query["message"]["query_type_id"] is None:
            id = "?"
        else:
            id = query["message"]['query_type_id']

        if "terms" not in query["message"] or query["message"]['terms'] is None:
            terms = "{}"
        else:
            terms = stringify_dict(query["message"]['terms'])

        if "restated_question" not in query["message"] or query["message"]["restated_question"] is None:
            restated_question = ""
        else:
            restated_question = query["message"]["restated_question"]

        message_code = message.message_code

        with open(os.path.dirname(os.path.abspath(__file__))+"/RTXQueries.log","a") as logfile:
            logfile.write(datetimeString+"\t"+cacheStatus+"\t"+message_code+"\t"+id+"\t"+terms+"\t"+restated_question+"\n")
        return


    def examine_incoming_query(self,query):

        #### Examine the query object to see what we got and set some flags
        response = { "message_code": "OK", "code_description": "Query examined" }

        #### Check to see if there's a processing plan
        if "previous_message_processing_plan" in query:
            response["have_previous_message_processing_plan"] = 1

        #### Temporary band-aid for old-style queries. Put the old-style top level content into message. This should be disallowed eventually. FIXME
        if "query_type_id" in query:
            query["message"] = query

        #### Check to see if the pre-0.9.2 query_message has come through
        if "query_message" in query:
            response["message_code"] = "OldStyleQuery"
            response["code_description"] = "Query specified 'query_message' instead of 'message', which is pre-0.9.2 style. Please update."
            return response

        #### Check to see if there's a query message to process
        if "message" in query:
            response["have_message"] = 1

            #### Check the query_type_id and terms to make sure there is information in both
            if "query_type_id" in query["message"] and query["message"]["query_type_id"] is not None:
                if "terms" in query["message"] is not None:
                    response["have_query_type_id_and_terms"] = 1
                else:
                    response["message_code"] = "QueryTypeIdWithoutTerms"
                    response["code_description"] = "query_type_id was provided but terms is empty"
                    return response
            elif "terms" in query["message"] and query["message"]["terms"] is not None:
                response["message_code"] = "TermsWithoutQueryTypeId"
                response["code_description"] = "terms hash was provided without a query_type_id"
                return response

            #### Check if there is a query_graph
            if "query_graph" in query["message"] and query["message"]["query_graph"] is not None:
                response["have_query_graph"] = 1

            #### If there is both a query_type_id and a query_graph, then return an error
            if "have_query_graph" in response and "have_query_type_id_and_terms" in response:
                response["message_code"] = "BothQueryTypeIdAndQueryGraph"
                response["code_description"] = "Message contains both a query_type_id and a query_graph, which is disallowed"
                return response

        #### Check to see if there is at least a message or a previous_message_processing_plan
        if "have_message" not in response and "have_previous_message_processing_plan" not in response:
            response["message_code"] = "NoQueryMessageOrPreviousMessageProcessingPlan"
            response["code_description"] = "No message or previous_message_processing_plan present in Query"
            return response

        #### If we got this far, then everything seems to be good enough to proceed
        return response


    def interpret_query_graph(self,query):
        """Try to interpret a QueryGraph and convert it into something RTX can process
        """

        #### Create a default response dict
        response = { "message_code": "InternalError", "code_description": "interpret_query_graph exited abnormally" }

        query_graph = query["message"]["query_graph"]
        nodes = query_graph["nodes"]
        edges = query_graph["edges"]
        n_nodes = len(nodes)
        n_edges = len(edges)
        eprint("DEBUG: n_nodes = %d, n_edges = %d" % (n_nodes,n_edges))

        #### Handle impossible cases
        if n_nodes == 0:
            response = { "message_code": "QueryGraphZeroNodes", "code_description": "Submitted QueryGraph has 0 nodes. At least 1 node is required" }
            return(response)
        if n_nodes == 1 and n_edges > 0:
            response = { "message_code": "QueryGraphTooManyEdges", "code_description": "Submitted QueryGraph may not have edges if there is only one node" }
            return(response)
        if n_nodes == 2 and n_edges > 1:
            response = { "message_code": "QueryGraphTooManyEdges", "code_description": "Submitted QueryGraph may not have more than 1 edge if there are only 2 nodes" }
            return(response)
        if n_nodes > 2:
            response = { "message_code": "UnsupportedQueryGraph", "code_description": "Submitted QueryGraph may currently only have 1 or 2 node. Support for 3 or more nodes coming soon." }
            return(response)

        #### Handle the single node case
        if n_nodes == 1:
            response = { "message_code": "OK", "code_description": "Interpreted QueryGraph as single node Q0" }
            response["id"] = "Q0"
            entity = nodes[0]["curie"]
            eprint("DEBUG: Q0 - entity = %s" % entity)
            response["terms"] = { "term": entity }
            response["original_question"] = "Submitted QueryGraph"
            response["restated_question"] = "What is %s?" % entity
            return(response)

        #### Handle the 2 node case
        if n_nodes == 2:
            eprint("DEBUG: Handling the 2-node case")
            source_type = None
            source_name = None
            target_type = None
            edge_type = None

            #### Loop through nodes trying to figure out which is the source and target
            for qnode in nodes:
                node = QNode.from_dict(qnode)

                if node.type == "gene":
                    if node.curie is None:
                        node.type = "protein"
                    else:
                        response = { "message_code": "UnsupportedNodeType", "code_description": "At least one of the nodes in the QueryGraph is a specific gene, which cannot be handled at the moment, a generic gene type with no curie is translated into a protein by RTX." }
                        return(response)

                if node.curie is None:
                    if node.type is None:
                        response = { "message_code": "UnderspecifiedNode", "code_description": "At least one of the nodes in the QueryGraph has neither a CURIE nor a type. It must have one of those." }
                        return(response)
                    else:
                        if target_type is None:
                            target_type = node.type
                        else:
                            response = { "message_code": "TooManyTargets", "code_description": "Both nodes have only types and are interpreted as targets. At least one node must have an exact identity." }
                            return(response)
                else:
                    if re.match(r"'",node.curie):
                        response = { "message_code": "IllegalCharacters", "code_description": "Node type contains one or more illegal characters." }
                        return(response)
                    if source_name is None:
                        if node.type is None:
                            response = { "message_code": "UnderspecifiedSourceNode", "code_description": "The source node must have a type in addition to a curie." }
                            return(response)
                        else:
                            source_name = node.curie
                            source_type = node.type
                    else:
                        response = { "message_code": "OverspecifiedQueryGraph", "code_description": "All nodes in the QueryGraph have exact identities, so there is really nothing left to query." }
                        return(response)

            #### Loop over the edges (should be just 1), ensuring that it has a type and recording it
            for qedge in edges:
                edge = QEdge.from_dict(qedge)
                if edge.type is None:
                    response = { "message_code": "EdgeWithNoType", "code_description": "At least one edge has no type. All edges must have a type." }
                    return(response)
                else:
                    edge_type = edge.type

            #### Perform a crude sanitation of the input parameters to make sure the shell command won't fail or cause harm
            if re.match(r"'",edge_type) or re.match(r"'",target_type) or re.match(r"'",source_name):
                response = { "message_code": "IllegalCharacters", "code_description": "The input query_graph entities contain one or more illegal characters." }
                return(response)

            #### Create the necessary components to hand off the queries to Q3Solution.py
            response = { "message_code": "OK", "code_description": "Interpreted QueryGraph as a single hop question" }
            response["id"] = "1hop"
            response["terms"] = { source_type: source_name, "target_label": target_type, "rel_type": edge_type }
            response["original_question"] = "Submitted QueryGraph"
            response["restated_question"] = "Which %s(s) are connected to the %s %s via edge type %s?" % (target_type,source_type,source_name,edge_type)
            #response["execution_string"] = "Q3Solution.py -s '%s' -t '%s' -r '%s' -j --directed" % (source_name,target_type,edge_type)
            response["execution_string"] = "Q3Solution.py -s '%s' -t '%s' -r '%s' -j" % (source_name,target_type,edge_type)
            return(response)

        return(response)



    def limit_message(self,message,query):
        if "max_results" in query and query["max_results"] is not None:
            if message.results is not None:
                if len(message.results) > query["max_results"]:
                    del message.results[query["max_results"]:]
                    message.code_description += " (output is limited to "+str(query["max_results"]) + " results)"


    def integrate(self,query):
        if "options" in query and query["options"] is not None:
            if re.search("integrate=.+",query["options"]):
                integrate_option = query["options"]
                eprint(integrate_option)
                target_string = re.sub("integrate=","",integrate_option)
                targets = re.split(",",target_string)
                eprint(targets)

                final_message = Message()

                for reasoner_id in targets:
                    eprint("Looping with reasoner_id="+reasoner_id)
                    query["options"] = "foo"
                    url = None
                    if reasoner_id == "RTX":
                        url = "https://arax.ncats.io/devED/api/rtx/v1/query"
                    elif reasoner_id == "Robokop":
                        url = "http://robokop.renci.org:6011/api/query"
                    elif reasoner_id == "Indigo":
                        url = "https://indigo.ncats.io/reasoner/api/v0/query"
                        url = None
                    else:
                        eprint("ERROR: Unrecognized target '"+target+"'")
                    if url is not None:
                        eprint("Querying url "+url)
                        message_content = requests.post(url, headers={'accept': 'application/json'}, json=query)
                        status_code = message_content.status_code
                        message_dict = message_content.json()
                        message = Message.from_dict(message_dict)
                        if reasoner_id == "RTX":
                            final_message = message
                        if reasoner_id == "Robokop" or reasoner_id == "Indigo":
                        #if reasoner_id == "Robokop":
                            eprint("Merging in "+reasoner_id)
                            message = self.fix_message(query,message,reasoner_id)
                            if message.results is not None:
                                final_message = self.merge_message2(final_message,message)

                return(final_message)
            return(None)
        return(None)


    def fix_message(self,query,message,reasoner_id):

        if reasoner_id == "RTX":
            base_url = "https://arax.ncats.io/devED/api/rtx/v1"
        elif reasoner_id == "Robokop":
            base_url = "http://robokop.renci.org:6011/api"
        elif reasoner_id == "Indigo":
            base_url = "https://indigo.ncats.io/reasoner/api/v0"
        else:
            eprint("ERROR: Unrecognized target '"+target+"'")

        if message.context is None:
            message.context = "https://raw.githubusercontent.com/biolink/biolink-model/master/context.jsonld"
        if message.id is None or message.id == "":
            message.id = base_url + "/message/1234"
        message.original_question = query["original_question"]
        message.restated_question = query["restated_question"]
        message.reasoner_id = reasoner_id
        if message.message_code is None or message.message_code == "":
            message.message_code = "OK"
        if message.n_results is None:
            if message.results is not None:
                message.n_results = len(message.results)
            else:
                message.n_results = 0
        if message.code_description is None or message.code_description == "":
            message.code_description = str(message.n_results) + " results returned"

        if message.results is not None:
            result_id = 2345
            for result in message.results:
                if result.id is None or result.id == "":
                    result.id = base_url + "/result/" + str(result_id)
                    result_id += 1
                if result.reasoner_id is None or result.reasoner_id == "":
                    result.reasoner_id = reasoner_id
                if result.confidence is None:
                    result.confidence = 0

        return(message)


    def merge_message(self,final_message,message_to_merge):
        for result in message_to_merge.results:
            final_message.results.append(result)
        final_message.n_results = len(final_message.results)
        final_message.code_description = str(final_message.n_results) + " merged reults"
        return(final_message)


    def merge_message2(self,final_message,message_to_merge):
        new_results = []
        mapper = SynonymMapper()
        result_group_counter = 1
        if final_message.results is None: final_message.results = []
        for main_result in final_message.results:
            new_results.append(main_result)
            if main_result.result_group is None:
              main_result.result_group = "G"+str(result_group_counter)
              result_group_counter += 1
            else:
              num = re.sub("G","",main_result.result_group)
              result_group_counter = int(num) + 1
            protein = None
            for node in main_result.knowledge_graph.nodes:
              if node.type == "protein":
                protein = node.id
            if protein is not None:
                eprint("protein="+protein)
                for other_result in message_to_merge.results:
                    for node in other_result.knowledge_graph.nodes:

                        #### Custom code for Indigo proteins/genes
                        if node.type == "Target":
                            match = mapper.prot_to_gene(protein)
                            eprint("  "+node.id)
                            if node.node_attributes is not None:
                                for attribute in node.node_attributes:
                                    if attribute.name == "uniprot_id" and protein == "UniProtKB:"+attribute.value:
                                        new_results.append(other_result)
                                        other_result.result_group = main_result.result_group
                                        eprint("             "+attribute.value)

                        #### Custom code for Robokop proteins/genes
                        elif node.type == "gene":
                            match = mapper.prot_to_gene(protein)
                            eprint("  "+node.id)
                            if node.id in match:
                                new_results.append(other_result)
                                other_result.result_group = main_result.result_group
                                eprint("  "+node.name)
                        else:
                            pass

        for other_result in message_to_merge.results:
            if other_result.result_group is None:
                new_results.append(other_result)
                other_result.result_group = "G"+str(result_group_counter)
                result_group_counter += 1

        final_message.results = new_results
        final_message.n_results = len(final_message.results)
        final_message.code_description = str(final_message.n_results) + " merged results"
        return(final_message)


    def get_node_types(self):
        return(ReasoningUtilities.get_node_labels())


    def get_all_edge_types(self):
        return(ReasoningUtilities.get_relationship_types())


    def get_node_to_node_edge_types(self,node_type1,node_type2):
        return(ReasoningUtilities.get_relationship_types_between(None,node_type1,None,node_type2,1))


    def get_node_edge_types(self,node_type):
        return(ReasoningUtilities.get_relationship_types_between(None,node_type,None,None,1))


    def __init__(self):
        None

def stringify_dict(inputDict):
    outString = "{"
    for key,value in sorted(inputDict.items(), key=lambda t: t[0]):
        if outString != "{":
            outString += ","
        outString += "'"+str(key)+"':'"+str(value)+"'"
    outString += "}"
    return(outString)


def main():
    rtxq = RTXQuery()
    query = { "query_type_id": "Q0", "terms": { "term": "lovastatin" } }
    #query = { "query_type_id": "Q0", "terms": { "term": "lovastatin" }, "bypass_cache": "true" }  # Use bypass_cache if the cache if bad for this question

    #query = { "knownQueryTypeId": "Q0", "terms": [ "foo" ] }
    #query = { "query_type_id": "Q1", "terms": [ "malaria" ] }
    #query = { "knownQueryTypeId": "Q2", "terms": [ "physostigmine", "glaucoma" ] }
    #query = { "query_type_id": "Q2", "terms": {'chemical_substance': 'CHEMBL154', 'disease': 'DOID:8398'} }
    #query = { "knownQueryTypeId": "Q2", "terms": [ "physostigmine", "DOID:1686" ] }
    #query = { "knownQueryTypeId": "Q2", "terms": [ "DOID:1686", "physostigmine" ] }
    #query = { "knownQueryTypeId": "Q3", "terms": [ "acetaminophen" ] }
    message = rtxq.query(query)
    print(json.dumps(ast.literal_eval(repr(message)),sort_keys=True,indent=2))
    #print(message)


if __name__ == "__main__": main()
