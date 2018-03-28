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

from QueryMeSH import QueryMeSH
from swagger_server.models.response import Response

class RTXQuery:

  def query(self,query):

    #### Extract the id and the terms from the incoming parameters
    id = query["knownQueryTypeId"]
    terms = query["terms"]

    if id == 'Q0':
      # call out to QueryMeSH here to satify the query "What is XXXXXX?"
      query = QueryMeSH()
      response = query.queryTerm(terms[0])
      id = response.id
      codeString = response.result_code
      self.logQuery(id,codeString,terms)
      return(response)

    #### Call out to OrangeBoard to answer the query "What genetic conditions might offer protection against XXXXXX?"
    if id == 'Q1':
      #### Set CWD to the QuestioningAnswering area and then invoke from the shell the Q1Solution code
      cwd = os.getcwd()
      os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/QuestionAnswering")
      command = "python3 Q1Solution.py -j -i '" + terms[0] + "'"
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

      #### If it fails, the just create a new Response object with a notice about the failure
      except:
          response = Response()
          response.result_code = "InternalError"
          response.message = "Error parsing the response from the reasoner. This is an internal bug that needs to be fixed. Unable to respond to this question at this time. The unparsable response was: " + reformattedText

      #### Log the result and return the Response object
      self.logQuery(response.id,response.result_code,terms)
      return(response)

    #### Call out to OrangeBoard to answer the query "What is the clinical outcome pathway of XXXXXX for treatment of YYYYYYY?"
    if id == 'Q2':
      #### Set CWD to the QuestioningAnswering area and then invoke from the shell the Q2Solution code
      cwd = os.getcwd()
      os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/QuestionAnswering")
      command = "python3 Q2Solution.py -j -d '" + terms[0] + "' -r '" + terms[1] + "'"
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

      #### If it fails, the just create a new Response object with a notice about the failure
      except:
          response = Response()
          response.result_code = "InternalError"
          response.message = "Error parsing the response from the reasoner. This is an internal bug that needs to be fixed. Unable to respond to this question at this time. The unparsable response was: " + reformattedText

      #### Log the result and return the Response object
      self.logQuery(response.id,response.result_code,terms)
      return(response)

    #### Call out to OrangeBoard to answer the query "Which proteins does X target?"
    if id == 'Q3':
      #### Set CWD to the QuestioningAnswering area and then invoke from the shell the Q3Solution code
      cwd = os.getcwd()
      os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../../reasoningtool/QuestionAnswering")
      command = "python3 Q3Solution.py -j -s '" + terms[0] + "' -t '" + terms[1] + "' -r '" + terms[2] + "' "
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

      #### If it fails, the just create a new Response object with a notice about the failure
      except:
          response = Response()
          response.result_code = "InternalError"
          response.message = "Error parsing the response from the reasoner. This is an internal bug that needs to be fixed. Unable to respond to this question at this time. The unparsable response was: " + reformattedText

      #### Log the result and return the Response object
      self.logQuery(response.id,response.result_code,terms)
      return(response)

    #### If the query type id is not triggered above, then return an error
    response = Response()
    response.result_code = "UnsupportedQueryTypeID"
    response.message = "The specified query id '" + id + "' is not supported at this time"
    return(response)


  def logQuery(self,id,codeString,terms):
    datetimeString = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if id == None:
      id = '000'
    with open(os.path.dirname(os.path.abspath(__file__))+"/RTXQueries.log","a") as logfile:
      logfile.write(datetimeString+"\t"+codeString+"\t"+id+"\t"+",".join(terms)+"\n")


  def __init__(self):
     None


def main():
  rtxq = RTXQuery()
  #query = { "knownQueryTypeId": "Q0", "terms": [ "lovastatin" ] }
  #query = { "knownQueryTypeId": "Q0", "terms": [ "foo" ] }
  #query = { "knownQueryTypeId": "Q1", "terms": [ "alkaptonuria" ] }
  query = { "knownQueryTypeId": "Q2", "terms": [ "physostigmine", "glaucoma" ] }
  #query = { "knownQueryTypeId": "Q2", "terms": [ "physostigmine", "glaucoma" ] }
  #query = { "knownQueryTypeId": "Q2", "terms": [ "physostigmine", "DOID:1686" ] }
  #query = { "knownQueryTypeId": "Q2", "terms": [ "DOID:1686", "physostigmine" ] }
  #query = { "knownQueryTypeId": "Q3", "terms": [ "acetaminophen" ] }
  response = rtxq.query(query)
  #print(json.dumps(response,sort_keys=True,indent=2))
  print(response)


if __name__ == "__main__": main()
