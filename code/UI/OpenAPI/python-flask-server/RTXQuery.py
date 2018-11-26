#!/usr/bin/python3
from __future__ import print_function
import sys
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

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

from QueryMeSH import QueryMeSH
from swagger_server.models.message import Message

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/QuestionAnswering/")
from ParseQuestion import ParseQuestion

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

    #### Determine a plan for what to do based on the input
    result = examineIncomingQuery(query)
    if result["response_code"] is not "OK":
      response.response_code = result["response_code"]
      response.code_description = result["code_description"]
      return response

    #### Check to see if the query_options indicates to query named resource and integrate the results
    if result["have_query_type_id_and_terms"] and and "integrate" in query.query_message.query_options:
      response = self.integrate(query)
      #self.logQuery(query,response,'remote')
      return response


    #### Extract the id and the terms from the incoming parameters
    id = query["query_type_id"]
    terms = query["terms"]

    eprint(query)


    #### Create an RTX Feedback management object
    #eprint(query)
    rtxFeedback = RTXFeedback()
    rtxFeedback.connect()
    cachedMessage = rtxFeedback.getCachedMessage(query)

    #### If we can find a cached message for this query and this version of RTX, then return the cached message
    if ( cachedMessage is not None ):
      apiMessage = Message().from_dict(cachedMessage)
      rtxFeedback.disconnect()
      self.limitMessage(apiMessage,query)

      if apiMessage.message_code is None:
        if apiMessage.result_code is not None:
          apiMessage.message_code = apiMessage.result_code
        else:
          apiMessage.message_code = "wha??"

      self.logQuery(query,apiMessage,'cached')
      return apiMessage

    #### Still have special handling for Q0
    if id == 'Q0':
      # call out to QueryMeSH here to satify the query "What is XXXXXX?"
      meshQuery = QueryMeSH()
      message = meshQuery.queryTerm(terms["term"])
      if 'original_question' in query:
        message.original_question = query["original_question"]
        message.restated_question = query["restated_question"]
      message.query_type_id = query["query_type_id"]
      message.terms = query["terms"]
      id = message.id
      codeString = message.message_code
      self.logQuery(query,message,'new')
      rtxFeedback.addNewMessage(message,query)
      rtxFeedback.disconnect()
      self.limitMessage(message,query)
      return(message)

    #### Call out to OrangeBoard to answer the other types of queries
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
      if 'original_question' in query:
        message.original_question = query["original_question"]
        message.restated_question = query["restated_question"]
      message.query_type_id = query["query_type_id"]
      message.terms = query["terms"]

      #### Log the result and return the Message object
      self.logQuery(query,message,'new')
      rtxFeedback.addNewMessage(message,query)
      rtxFeedback.disconnect()

      #### Limit message
      self.limitMessage(message,query)
      return(message)


    #### If the query type id is not triggered above, then return an error
    message = Message()
    message.message_code = "UnsupportedQueryTypeID"
    message.code_description = "The specified query id '" + id + "' is not supported at this time"
    rtxFeedback.disconnect()
    return(message)


  def logQuery(self,query,message,cacheStatus):
    datetimeString = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "query_type_id" not in query or query["query_type_id"] is None:
      id = "?"
    else:
      id = query['query_type_id']

    if "terms" not in query or query['terms'] is None:
      terms = "{}"
    else:
      terms = stringifyDict(query['terms'])

    if "restated_question" not in query or query["restated_question"] is None:
      restated_question = ""
    else:
      restated_question = query["restated_question"]

    message_code = message.message_code

    with open(os.path.dirname(os.path.abspath(__file__))+"/RTXQueries.log","a") as logfile:
      logfile.write(datetimeString+"\t"+cacheStatus+"\t"+message_code+"\t"+id+"\t"+terms+"\t"+restated_question+"\n")
  def examineIncomingQuery(self,query):
    #### Examine the query object to see what we got and set some flags
    response = { message_code = "OK", code_description = "Query examined" }

    #### Check to see if there's a processing plan
    if "previous_message_processing_plan" in query:
      response["have_previous_message_processing_plan"] = 1
    }

    #### Check to see if there's a query message to process
    if "query_message" in query:
      response["have_query_message"] = 1

      #### Check the query_type_id and terms to make sure there is information in both
      if query.query_message.query_type_id is not None:
        if query.query_message.terms is not None:
          response["have_query_type_id_and_terms"] = 1
        else:
          response["message_code"] = "QueryTypeIdWithoutTerms"
          response["code_description"] = "query_type_id was provided but terms is empty"
          return response
      elif query.query_message.terms is not None:
        response["message_code"] = "TermsWithoutQueryTypeId"
        response["code_description"] = "terms hash was provided without a query_type_id"
        return response

      #### Check if there is a query_graph
      if query.query_message.query_graph is not None:
        response["have_query_graph"] = 1

      #### If there is both a query_type_id and a query_graph, then return an error
      if "have_query_graph" in response and "have_query_type_id_and_terms" in response:
        response["message_code"] = "BothQueryTypeIdAndQueryGraph"
        response["code_description"] = "Message contains both a query_type_id and a query_graph, which is disallowed"
        return response

    #### Check to see if there is at least a query_message or a previous_message_processing_plan
    if "have_query_message" not in response and "have_previous_message_processing_plan" not in response:
      response["message_code"] = "NoQueryMessageOrPreviousMessageProcessingPlan"
      response["code_description"] = "No query_message or previous_message_processing_plan present in Query"
      return response

    #### If we got this far, then everything seems to be good enough to proceed
    return response


  def limitMessage(self,message,query):
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
            url = "https://rtx.ncats.io/devED/api/rtx/v1/query"
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
      base_url = "https://rtx.ncats.io/devED/api/rtx/v1"
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


  def __init__(self):
     None

def stringifyDict(inputDict):
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
