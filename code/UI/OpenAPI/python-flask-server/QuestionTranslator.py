#!/usr/bin/python3
import re

class QuestionTranslator:

  def translate(self,question):

    text=question["text"]

    #print(question)
    print("Trying to translate question '"+text+"'")

    match = re.match( "(Which|What) genetic conditions (might )*offer protection against (.+)[\?]*", text, re.I )
    if match:
      term = match.group(3)
      query = [ { "knownQueryTypeId": "Q1", "terms": [ term ], "restatedQuestion": "Which genetic conditions may offer protection against "+term+"?", "originalQuestion": text } ]
      return(query)

    match = re.match( "what is the clinical outcome pathway of (.+) for treatment of (.+)[\?]*", text, re.I )
    if match:
      term1 = match.group(1)
      term2 = match.group(2)
      query = [ { "knownQueryTypeId": "Q2", "terms": [ term1,term2 ], "restatedQuestion": "What is the clinical outcome pathway of "+term1+" for treatment of "+term2+"?", "originalQuestion": text } ]
      return(query)

    match = re.match( "(Which|What) protein(s)? does (.+) target[\?]*", text, re.I )
    if match:
      term = match.group(3)
      query = [ { "knownQueryTypeId": "Q3", "terms": [ term ], "restatedQuestion": "Which proteins does "+term+" target?", "originalQuestion": text } ]
      return(query)

    match = re.match( "what is (.+)[\?]*", text, re.I )
    if match:
      term = match.group(1)
      query = [ { "knownQueryTypeId": "Q0", "terms": [ term ], "restatedQuestion": "What is "+term+"?", "originalQuestion": text } ]
      return(query)

    query = [ { "knownQueryTypeId": "", "message": "I do not understand the question '"+text+"'", "restatedQuestion": "", "originalQuestion": text } ]
    return(query)


  def __init__(self):
     None


def main():
  txltr = QuestionTranslator()
  #question = { "language": "English", "text": "what is lovastatin" }
  question = { "language": "English", "text": "what genetic conditions offer protection against malaria" }
  query = txltr.translate(question)
  print(" Result is:")
  print(query)


if __name__ == "__main__": main()
