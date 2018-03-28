#!/usr/bin/python3
from __future__ import print_function
import sys
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

import re
import os
from QueryPharos import QueryPharos
import sys
import subprocess
from QueryMeSH import QueryMeSH
import json
import datetime



class RTXQuery:

  def query(self,query):

    qph = QueryPharos()

    id = query["knownQueryTypeId"]
    terms = query["terms"]
    result = [ { "id": 536, "code": 100, "codeString": "UnsupportedQueryID", "message": "The specified query id '"+id+"' is not supported at this time", "text": [ "The specified query id '"+id+"' is not supported at this time" ] } ]


    if id == 'Q0':
      # call out to QueryMeSH here to satify the query "What is XXXXXX?"
      query = QueryMeSH()
      response = query.queryTerm(terms[0])
      id = response.id
      codeString = response.result_code
      self.logQuery(id,codeString,terms)
      return(response)

    if id == 'Q1':
      # call out to OrangeBoard here to satify the query "What genetic conditions might offer protection against XXXXXX?"
      cwd = os.getcwd()
      os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../..//reasoningtool/QuestionAnswering")
      eprint("python3 Q1Solution.py -j -i '"+terms[0]+"'" )
      returnedText = subprocess.run( [ "python3 Q1Solution.py -j -i '"+terms[0]+"'" ], stdout=subprocess.PIPE, shell=True )
      os.chdir(cwd)
      reformattedText = returnedText.stdout.decode('utf-8')
      #print(reformattedText)
      try:
          #eprint(reformattedText)
          returnedData = json.loads(reformattedText)
          text = returnedData["text"]
      except:
          returnedData = { "status": "ERROR" }
          text = "ERROR: Unable to properly parse the JSON response:<BR>\n"+reformattedText
      prettyText = re.sub("\n","\n<LI>",text)
      prettyText = "<UL><LI>" + prettyText + "</UL>"
      codeString = "OK"
      result = [ { "id": 537, "code": 1, "codeString": codeString, "message": "AnswerFound", "result": returnedData, "text": [ prettyText ] } ]
      self.logQuery(id,codeString,terms)
      return(result)

    if id == 'Q2':
      # call out to OrangeBoard here to satify the query "What is the clinical outcome pathway of XXXXXX for treatment of YYYYYYY?"
      cwd = os.getcwd()
      os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../..//reasoningtool/QuestionAnswering")
      eprint("python3 Q2Solution.py -r '"+terms[0]+"' -d '"+terms[1]+"'" )
      returnedText = subprocess.run( [ "python3 Q2Solution.py -d '"+terms[0]+"' -r '"+terms[1]+"'" ], stdout=subprocess.PIPE, shell=True )
      os.chdir(cwd)
      #reformattedText = returnedText.stdout.decode('utf-8')
      response = json.loads(returnedText)
      id = response.id
      codeString = response.result_code
      self.logQuery(id,codeString,terms)
      return(response)

    if id == 'Q3':
      targets = qph.query_drug_name_to_targets(terms[0])
      if targets:
        list = '<UL>\n'
        for target in targets:
          list += "<LI> "+target["name"]+"\n"
        list += "</UL>\n"
        codeString = "OK"
        result = [ { "id": 537, "code": 1, "codeString": codeString, "message": "AnswerFound", "result": targets, "text": [ terms[0]+" is known to target: "+list ] } ]
        self.logQuery(id,codeString,terms)
      else:
        codeString = "DrugNotFound"
        result = [ { "id": 537, "code": 11, "codeString": codeString, "message": "DrugNotFound", "text": [ "Unable to find drug '"+terms[0]+"'." ] } ]
        self.logQuery(id,codeString,terms)
      return(result);


    return(result)


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
  query = { "knownQueryTypeId": "Q2", "terms": [ "physostigmine", "DOID:1686" ] }
  #query = { "knownQueryTypeId": "Q3", "terms": [ "acetaminophen" ] }
  result = rtxq.query(query)
  #print(" Result is:")
  print(result)


if __name__ == "__main__": main()
