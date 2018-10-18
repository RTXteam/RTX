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
from swagger_server.models.response import Response

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
    


    #### If there is no query_type_id, then return an error
    if "query_type_id" not in query:
      response = Response()
      response.response_code = "No_query_type_id"
      response.message = "There was no query_type_id specified in the query"
      return(response)

    #### If there is no terms, then return an error
    if "terms" not in query:
      response = Response()
      response.response_code = "No_terms"
      response.message = "There was no terms element specified in the query"
      return(response)

    #### Extract the id and the terms from the incoming parameters
    id = query["query_type_id"]
    terms = query["terms"]

    eprint(query)
    #### Check to see if the options indicate to query another resource
    if "options" in query and re.search("integrate=",query["options"]):
      response = self.integrate(query)
      #self.logQuery(query,response,'remote')
      return response



    #### Temportary hack FIXME
    if "chemical_substance" in terms:
      if re.match("CHEMBL:",terms["chemical_substance"]):
        terms["chemical_substance"] = re.sub("CHEMBL:","",terms["chemical_substance"])
    query["known_query_type_id"] = query["query_type_id"]



    #### Create an RTX Feedback management object
    #eprint(query)
    rtxFeedback = RTXFeedback()
    rtxFeedback.connect()
    cachedResponse = rtxFeedback.getCachedResponse(query)

    #### If we can find a cached response for this query and this version of RTX, then return the cached response
    if ( cachedResponse is not None ):
      apiResponse = Response().from_dict(cachedResponse)
      rtxFeedback.disconnect()
      self.limitResponse(apiResponse,query)

      if apiResponse.response_code is None:
        if apiResponse.result_code is not None:
          apiResponse.response_code = apiResponse.result_code
        else:
          apiResponse.response_code = "wha??"

      self.logQuery(query,apiResponse,'cached')
      return apiResponse

    #### Still have special handling for Q0
    if id == 'Q0':
      # call out to QueryMeSH here to satify the query "What is XXXXXX?"
      meshQuery = QueryMeSH()
      response = meshQuery.queryTerm(terms["term"])
      if 'original_question' in query:
        response.original_question_text = query["original_question"]
        response.restated_question_text = query["restated_question"]
      response.query_type_id = query["query_type_id"]
      response.terms = query["terms"]
      id = response.id
      codeString = response.response_code
      self.logQuery(query,response,'new')
      rtxFeedback.addNewResponse(response,query)
      rtxFeedback.disconnect()
      self.limitResponse(response,query)
      return(response)

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

      #### Try to decode that string into a response object
      try:
          #data = ast.literal_eval(reformattedText)
          data = json.loads(reformattedText)
          response = Response.from_dict(data)
          if response.response_code is None:
            if response.result_code is not None:
              response.response_code = response.result_code
            else:
              response.response_code = "wha??"

      #### If it fails, the just create a new Response object with a notice about the failure
      except:
          response = Response()
          response.response_code = "InternalError"
          response.message = "Error parsing the response from the reasoner. This is an internal bug that needs to be fixed. Unable to respond to this question at this time. The unparsable response was: " + reformattedText

      #print(query)
      if 'original_question' in query:
        response.original_question_text = query["original_question"]
        response.restated_question_text = query["restated_question"]
      response.query_type_id = query["query_type_id"]
      response.terms = query["terms"]

      #### Log the result and return the Response object
      self.logQuery(query,response,'new')
      rtxFeedback.addNewResponse(response,query)
      rtxFeedback.disconnect()

      #### Limit response
      self.limitResponse(response,query)
      return(response)


    #### If the query type id is not triggered above, then return an error
    response = Response()
    response.response_code = "UnsupportedQueryTypeID"
    response.message = "The specified query id '" + id + "' is not supported at this time"
    rtxFeedback.disconnect()
    return(response)


  def logQuery(self,query,response,cacheStatus):
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

    response_code = response.response_code

    with open(os.path.dirname(os.path.abspath(__file__))+"/RTXQueries.log","a") as logfile:
      logfile.write(datetimeString+"\t"+cacheStatus+"\t"+response_code+"\t"+id+"\t"+terms+"\t"+restated_question+"\n")


  def limitResponse(self,response,query):
    if "max_results" in query and query["max_results"] is not None:
      if response.result_list is not None:
        if len(response.result_list) > query["max_results"]:
          del response.result_list[query["max_results"]:]
          response.message += " (output is limited to "+str(query["max_results"]) + " results)"


  def integrate(self,query):
    if "options" in query and query["options"] is not None:
      if re.search("integrate=.+",query["options"]):
        integrate_option = query["options"]
        eprint(integrate_option)
        target_string = re.sub("integrate=","",integrate_option)
        targets = re.split(",",target_string)
        eprint(targets)

        final_response = Response()

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
            response_content = requests.post(url, headers={'accept': 'application/json'}, json=query)
            status_code = response_content.status_code
            response_dict = response_content.json()
            response = Response.from_dict(response_dict)
            if reasoner_id == "RTX":
              final_response = response
            if reasoner_id == "Robokop" or reasoner_id == "Indigo":
            #if reasoner_id == "Robokop":
              eprint("Merging in "+reasoner_id)
              response = self.fix_response(query,response,reasoner_id)
              if response.result_list is not None:
                final_response = self.merge_response2(final_response,response)

        return(final_response)
      return(None)
    return(None)


  def fix_response(self,query,response,reasoner_id):

    if reasoner_id == "RTX":
      base_url = "https://rtx.ncats.io/devED/api/rtx/v1"
    elif reasoner_id == "Robokop":
      base_url = "http://robokop.renci.org:6011/api"
    elif reasoner_id == "Indigo":
      base_url = "https://indigo.ncats.io/reasoner/api/v0"
    else:
      eprint("ERROR: Unrecognized target '"+target+"'")

    if response.context is None:
      response.context = "https://raw.githubusercontent.com/biolink/biolink-model/master/context.jsonld"
    if response.id is None or response.id == "":
      response.id = base_url + "/response/1234"
    response.original_question_text = query["original_question"]
    response.restated_question_text = query["restated_question"]
    response.reasoner_id = reasoner_id
    if response.response_code is None or response.response_code == "":
      response.response_code = "OK"
    if response.n_results is None:
      if response.result_list is not None:
        response.n_results = len(response.result_list)
      else:
        response.n_results = 0
    if response.message is None or response.message == "":
      response.message = str(response.n_results) + " reults returned"

    if response.result_list is not None:
      result_id = 2345
      for result in response.result_list:
        if result.id is None or result.id == "":
          result.id = base_url + "/result/" + str(result_id)
          result_id += 1
        if result.reasoner_id is None or result.reasoner_id == "":
          result.reasoner_id = reasoner_id
        if result.confidence is None:
          result.confidence = 0

    return(response)


  def merge_response(self,final_response,response_to_merge):
    for result in response_to_merge.result_list:
      final_response.result_list.append(result)
    final_response.n_results = len(final_response.result_list)
    final_response.message = str(final_response.n_results) + " merged reults"
    return(final_response)


  def merge_response2(self,final_response,response_to_merge):
    new_result_list = []
    mapper = SynonymMapper()
    result_group_counter = 1
    if final_response.result_list is None: final_response.result_list = []
    for main_result in final_response.result_list:
      new_result_list.append(main_result)
      if main_result.result_group is None:
        main_result.result_group = "G"+str(result_group_counter)
        result_group_counter += 1
      else:
        num = re.sub("G","",main_result.result_group)
        result_group_counter = int(num) + 1
      protein = None
      for node in main_result.result_graph.node_list:
        if node.type == "protein":
          protein = node.id
      if protein is not None:
        eprint("protein="+protein)
        for other_result in response_to_merge.result_list:
          for node in other_result.result_graph.node_list:

            #### Custom code for Indigo proteins/genes
            if node.type == "Target":
              match = mapper.prot_to_gene(protein)
              eprint("  "+node.id)
              if node.node_attributes is not None:
                for attribute in node.node_attributes:
                  if attribute.name == "uniprot_id" and protein == "UniProtKB:"+attribute.value:
                    new_result_list.append(other_result)
                    other_result.result_group = main_result.result_group
                    eprint("             "+attribute.value)

            #### Custom code for Robokop proteins/genes
            elif node.type == "gene":
              match = mapper.prot_to_gene(protein)
              eprint("  "+node.id)
              if node.id in match:
                new_result_list.append(other_result)
                other_result.result_group = main_result.result_group
                eprint("  "+node.name)
            else:
              pass

    for other_result in response_to_merge.result_list:
      if other_result.result_group is None:
        new_result_list.append(other_result)
        other_result.result_group = "G"+str(result_group_counter)
        result_group_counter += 1

    final_response.result_list = new_result_list
    final_response.n_results = len(final_response.result_list)
    final_response.message = str(final_response.n_results) + " merged reults"
    return(final_response)


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
  response = rtxq.query(query)
  print(json.dumps(ast.literal_eval(repr(response)),sort_keys=True,indent=2))
  #print(response)


if __name__ == "__main__": main()
