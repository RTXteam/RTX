#!/usr/bin/python3
import re

class QuestionTranslator:

  def translate(self,question):

    text=question["text"]

    #print(question)
    print("Trying to translate question '"+text+"'")
    originalText = text
    text = re.sub("\?","", text)
    text = re.sub("^\s+","", text)
    text = re.sub("\s+$","", text)
    text = text.lower()

    match = re.search( "(;|>|<|\|)", text )
    if match:
        query = [ { "knownQueryTypeId": "", "message": "Illegal characters in the question '"+text+"'", "restatedQuestion": "", "originalQuestion": originalText } ]
        print(query)
        return(query)

    match = re.match( "(Which|What) genetic conditions (might )*offer protection against\s+(.+)$", text, re.I )
    if match:
        term = match.group(3)
        term = re.sub("^\s+","", term)
        term = re.sub("\s+$","", term)
        query = [ { "knownQueryTypeId": "Q1", "terms": [ term ], "restatedQuestion": "Which genetic conditions may offer protection against "+term+"?", "originalQuestion": originalText } ]
        print(query)
        return(query)

    match = re.match( "what is the clinical outcome pathway of\s+(.+)\s+for treatment of\s+(.+)", text, re.I )
    if match:
      term1 = match.group(1)
      term1 = re.sub("^\s+","", term1)
      term1 = re.sub("\s+$","", term1)
      term2 = match.group(2)
      term2 = re.sub("^\s+","", term2)
      term2 = re.sub("\s+$","", term2)
      query = [ { "knownQueryTypeId": "Q2", "terms": [ term1,term2 ], "restatedQuestion": "What is the clinical outcome pathway of "+term1+" for treatment of "+term2+"?", "originalQuestion": originalText } ]
      print(query)
      return(query)

    match = re.match( "(Which|What) protein(s)? does\s+(.+)\s+target", text, re.I )
    if match:
      term = match.group(3)
      term = re.sub("^\s+","", term)
      term = re.sub("\s+$","", term)
      query = [ { "knownQueryTypeId": "Q3", "terms": [ term ], "restatedQuestion": "Which proteins does "+term+" target?", "originalQuestion": originalText } ]
      return(query)

    match = re.match( "what is\s+(.+)", text, re.I )
    if match:
      term = match.group(1)
      term = re.sub("^\s+","", term)
      term = re.sub("\s+$","", term)
      query = [ { "knownQueryTypeId": "Q0", "terms": [ term ], "restatedQuestion": "What is "+term+"?", "originalQuestion": originalText } ]
      return(query)

    query = [ { "knownQueryTypeId": "", "message": "I do not understand the question '"+text+"'", "restatedQuestion": "", "originalQuestion": originalText } ]
    return(query)


  def __init__(self):
     None


def main():
  txltr = QuestionTranslator()
  #question = { "language": "English", "text": "what is lovastatin" }
  question = { "language": "English", "text": "what genetic conditions offer protection against |malaria" }
  query = txltr.translate(question)
  print(" Result is:")
  print(query)


if __name__ == "__main__": main()
