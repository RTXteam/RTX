#!/usr/bin/python3
import re
from QueryPharos import QueryPharos

class RTXQuery:

  def query(self,query):

    qph = QueryPharos()

    id = query["knownQueryTypeId"]
    terms = query["terms"]
    result = [ { "id": 536, "code": 100, "codeString": "UnsupportedQueryID", "message": "The specified query id '"+id+"' is not supported at this time", "text": [ "The specified query id '"+id+"' is not supported at this time" ] } ]

    if id == 'Q0':
      # call out to OrangeBoard here to satify the query "What is XXXXXX?"
      drug_id = qph.query_drug_id_by_name(terms[0])
      if drug_id:
        description = qph.query_drug_description(str(drug_id))
        if description:
          result = [ { "id": 537, "code": 1, "codeString": "OK", "message": "AnswerFound", "text": [ terms[0]+" is "+description ] } ]
        else:
          result = [ { "id": 537, "code": 10, "codeString": "DrugDescriptionNotFound", "message": "DrugDescriptionNotFound", "text": [ "Unable to find a definition for drug '"+terms[0]+"'." ] } ]
      else:
          result = [ { "id": 537, "code": 11, "codeString": "DrugNotFound", "message": "DrugNotFound", "text": [ "Unable to find drug '"+terms[0]+"'." ] } ]
      return(result)

    if id == 'Q1':
      # call out to OrangeBoard here to satify the query "What genetic conditions might offer protection against XXXXXX?"
      simulatedResult = [ { "id": 537, "code": 1, "codeString": "OK", "message": "AnswerFound", "text": [ "There might be something that offers protection against "+terms[0]+"", "more information..." ] } ]
      return(simulatedResult)

    if id == 'Q2':
      # call out to OrangeBoard here to satify the query "What is the clinical outcome pathway of XXXXXX for treatment of YYYYYYY?"
      simulatedResult = [ { "id": 537, "code": 1, "codeString": "OK", "message": "AnswerFound", "text": [ "There might be something that links "+terms[0]+" to "+terms[1]+".", "more information..." ] } ]
      return(simulatedResult)

    if id == 'Q3':
      targets = qph.query_drug_name_to_targets(terms[0])
      if targets:
        list = '<UL>\n'
        for target in targets:
          list += "<LI> "+target["name"]+"\n"
        list += "</UL>\n"
        result = [ { "id": 537, "code": 1, "codeString": "OK", "message": "AnswerFound", "text": [ terms[0]+" is known to target: "+list ] } ]
      else:
        result = [ { "id": 537, "code": 11, "codeString": "DrugNotFound", "message": "DrugNotFound", "text": [ "Unable to find drug '"+terms[0]+"'." ] } ]
      return(result);


    return(result)


  def __init__(self):
     None


def main():
  rtxq = RTXQuery()
  #query = { "knownQueryTypeId": "Q0", "terms": [ "lovastatin" ] }
  #query = { "knownQueryTypeId": "Q1", "terms": [ "lovastatin" ] }
  #query = { "knownQueryTypeId": "Q2", "terms": [ "lovastatin", "hyperpidemia" ] }
  query = { "knownQueryTypeId": "Q3", "terms": [ "acetaminophen" ] }
  result = rtxq.query(query)
  print(" Result is:")
  print(result)


if __name__ == "__main__": main()
