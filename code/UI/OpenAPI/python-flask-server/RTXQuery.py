#!/usr/bin/python3
import re
import os
from QueryPharos import QueryPharos
import sys
import subprocess
from QueryMeSH import QueryMeSH
import json


class RTXQuery:

  def query(self,query):

    qph = QueryPharos()

    id = query["knownQueryTypeId"]
    terms = query["terms"]
    result = [ { "id": 536, "code": 100, "codeString": "UnsupportedQueryID", "message": "The specified query id '"+id+"' is not supported at this time", "text": [ "The specified query id '"+id+"' is not supported at this time" ] } ]


    if id == 'Q0':
      # call out to QueryMeSH here to satify the query "What is XXXXXX?"
      query = QueryMeSH()
      attributes = query.findTermAttributesAndTypeByName(terms[0])
      html = query.prettyPrintAttributes(attributes)
      if attributes["status"] == "OK":
        if attributes["description"]:
          codeString = "OK"
          result = [ { "id": 537, "code": 1, "codeString": codeString, "message": "AnswerFound", "text": [ html ], "result": attributes } ]
          self.logQuery(query,codeString)
        else:
          codeString = "DrugDescriptionNotFound"
          result = [ { "id": 537, "code": 10, "codeString": codeString, "message": "DrugDescriptionNotFound", "text": [ "Unable to find a definition for drug '"+terms[0]+"'." ] } ]
          self.logQuery(query,codeString)
      else:
          codeString = "TermNotFound"
          result = [ { "id": 537, "code": 11, "codeString": codeString, "message": "TermNotFound", "text": [ html ] } ]
          self.logQuery(query,codeString)
      return(result)

    if id == 'Q1':
      # call out to OrangeBoard here to satify the query "What genetic conditions might offer protection against XXXXXX?"
      os.chdir("/mnt/data/orangeboard/code/NCATS/code/reasoningtool")
      #returnedText = answerQ1(terms[0], directed=True, max_path_len=3, verbose=True)
      returnedText = subprocess.run( [ "python3 Q1Solution.py -j -i '"+terms[0]+"'" ], stdout=subprocess.PIPE, shell=True )
      reformattedText = returnedText.stdout.decode('utf-8')
      #print(reformattedText)
      try:
          returnedData = json.loads(reformattedText)
          text = returnedData["text"]
      except:
          returnedData = { "status": "ERROR" }
          text = "ERROR: Unable to properly parse the JSON response:<BR>\n"+reformattedText
      prettyText = re.sub("\n","\n<LI>",text)
      prettyText = "<UL><LI>" + prettyText + "</UL>"
      result = [ { "id": 537, "code": 1, "codeString": "OK", "message": "AnswerFound", "result": returnedData, "text": [ prettyText ] } ]
      return(result)

    if id == 'Q2':
      # call out to OrangeBoard here to satify the query "What is the clinical outcome pathway of XXXXXX for treatment of YYYYYYY?"
      os.chdir("/mnt/data/orangeboard/code/NCATS/code/reasoningtool")
      returnedText = subprocess.run( [ "python3 Q2Solution.py -r '"+terms[0]+"' -d '"+terms[1]+"'" ], stdout=subprocess.PIPE, shell=True )
      reformattedText = returnedText.stdout.decode('utf-8')
      reformattedText = re.sub("\n","<BR>\n",reformattedText)
      #reformattedText = "<UL><LI>" + reformattedText + "</UL>"
      result = [ { "id": 537, "code": 1, "codeString": "OK", "message": "AnswerFound", "text": [ reformattedText ] } ]
      return(result)


    if id == 'Q3':
      targets = qph.query_drug_name_to_targets(terms[0])
      if targets:
        list = '<UL>\n'
        for target in targets:
          list += "<LI> "+target["name"]+"\n"
        list += "</UL>\n"
        result = [ { "id": 537, "code": 1, "codeString": "OK", "message": "AnswerFound", "result": targets, "text": [ terms[0]+" is known to target: "+list ] } ]
      else:
        result = [ { "id": 537, "code": 11, "codeString": "DrugNotFound", "message": "DrugNotFound", "text": [ "Unable to find drug '"+terms[0]+"'." ] } ]
      return(result);


    return(result)


  def logQuery(self,query,resultCode):
    id = query["knownQueryTypeId"]
    terms = query["terms"]
    with open("RTXQueries.log","a") as logfile
      logfile.write(datetime+"\t"+resultCode+"\t"+id+"\t"+",".join(terms))


  def __init__(self):
     None


def main():
  rtxq = RTXQuery()
  #query = { "knownQueryTypeId": "Q0", "terms": [ "lovastatin" ] }
  query = { "knownQueryTypeId": "Q1", "terms": [ "alkaptonuria" ] }
  #query = { "knownQueryTypeId": "Q2", "terms": [ "physostigmine", "glaucoma" ] }
  #query = { "knownQueryTypeId": "Q3", "terms": [ "acetaminophen" ] }
  result = rtxq.query(query)
  #print(" Result is:")
  print(result)


if __name__ == "__main__": main()
