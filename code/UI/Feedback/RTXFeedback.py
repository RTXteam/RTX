#!/usr/bin/python3
# Database definition and RTXFeedback class
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import sys
import re
import json
import ast
from datetime import datetime
import pickle
import hashlib
import collections
import requests
import json
from flask import Flask,redirect

from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime, Text, PickleType, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from sqlalchemy import inspect
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.result_feedback import ResultFeedback
from swagger_server.models.feedback import Feedback
from swagger_server.models.message import Message as TxMessage
from swagger_server.models.previous_message_processing_plan import PreviousMessageProcessingPlan

#import Enricher
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ARAX/ARAXQuery")
from actions_parser import ActionsParser
from ARAX_filter import ARAXFilter

Base = declarative_base()

#### Define the database tables as classes
class Message(Base):
  __tablename__ = 'message09'
  message_id = Column(Integer, primary_key=True)
  message_datetime = Column(DateTime, nullable=False)
  restated_question = Column(String(255), nullable=False)
  query_type = Column(String(50), nullable=False)
  terms = Column(String(1024), nullable=False)
  tool_version = Column(String(50), nullable=False)
  result_code = Column(String(50), nullable=False)
  message = Column(Text, nullable=False)
  n_results = Column(Integer, nullable=False)
  # PickleType uses BLOB on MySQL, which is only 65k. Could not seem to work around it. Resort to LargeBinary with explicit length and my own pickling.
  #message_object = Column(PickleType, nullable=False)
  message_object = Column(LargeBinary(length=100500500), nullable=False)

class Result(Base):
  __tablename__ = 'result09'
  result_id = Column(Integer, primary_key=True)
  message_id = Column(Integer, ForeignKey('message09.message_id'))   # for backward compat, this is retained as the *first* message_id
  confidence = Column(Float, nullable=False)
  n_nodes = Column(Integer, nullable=False)
  n_edges = Column(Integer, nullable=False)
  result_text = Column(Text, nullable=False)
  result_object = Column(LargeBinary(length=16777200), nullable=False)
  result_hash = Column(String(255), nullable=False)
  message = relationship(Message)

class Message_result(Base):
  __tablename__ = 'message_result09'
  message_result_id = Column(Integer, primary_key=True)
  result_id = Column(Integer, ForeignKey('result09.result_id'))
  message_id = Column(Integer, ForeignKey('message09.message_id'))

class Commenter(Base):
  __tablename__ = 'commenter09'
  commenter_id = Column(Integer, primary_key=True)
  full_name = Column(String(255), nullable=False)
  email_address = Column(String(255), nullable=False)
  password = Column(String(255), nullable=False)


class Rating(Base):
  __tablename__ = 'rating09'
  rating_id = Column(Integer, primary_key=True)
  score = Column(Integer, nullable=False)
  tag = Column(String(50), nullable=False)
  name = Column(String(255), nullable=False)
  description = Column(String(255), nullable=False)


class Expertise_level(Base):
  __tablename__ = 'expertise_level09'
  expertise_level_id = Column(Integer, primary_key=True)
  score = Column(Integer, nullable=False)
  tag = Column(String(50), nullable=False)
  name = Column(String(255), nullable=False)
  description = Column(String(255), nullable=False)


class Result_rating(Base):
  __tablename__ = 'result_rating09'
  result_rating_id = Column(Integer, primary_key=True)
  result_id = Column(Integer, ForeignKey('result09.result_id'))
  commenter_id = Column(Integer, ForeignKey('commenter09.commenter_id'))
  expertise_level_id = Column(Integer, ForeignKey('expertise_level09.expertise_level_id'))
  rating_id = Column(Integer, ForeignKey('rating09.rating_id'))
  comment_datetime = Column(DateTime, nullable=False)
  comment = Column(Text, nullable=True)
  result = relationship(Result)
  commenter = relationship(Commenter)
  expertise_level = relationship(Expertise_level)
  rating = relationship(Rating)


#### The main RTXFeedback class
class RTXFeedback:

  #### Constructor
  def __init__(self):
    self.databaseName = "RTXFeedback"
    self.connect()

  #### Destructor
  def __del__(self):
    self.disconnect()


  #### Define attribute session
  @property
  def session(self) -> str:
    return self._session

  @session.setter
  def session(self, session: str):
    self._session = session


  #### Define attribute engine
  @property
  def engine(self) -> str:
    return self._engine

  @engine.setter
  def engine(self, engine: str):
    self._engine = engine


  #### Define attribute databaseName
  @property
  def databaseName(self) -> str:
    return self._databaseName

  @databaseName.setter
  def databaseName(self, databaseName: str):
    self._databaseName = databaseName


  #### Delete and create the RTXFeedback SQLite database. Careful!
  def createDatabase(self):
    print("Creating database")
    #if os.path.exists(self.databaseName):
    #  os.remove(self.databaseName)
    #engine = create_engine("sqlite:///"+self.databaseName)
    rtxConfig = RTXConfiguration()
    engine = create_engine("mysql+pymysql://" + rtxConfig.mysql_feedback_username + ":" + rtxConfig.mysql_feedback_password + "@" + rtxConfig.mysql_feedback_host + "/" + self.databaseName)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    self.connect()

  #### Create and store a database connection
  def connect(self):
    #engine = create_engine("sqlite:///"+self.databaseName)
    rtxConfig = RTXConfiguration()
    engine = create_engine("mysql+pymysql://" + rtxConfig.mysql_feedback_username + ":" + rtxConfig.mysql_feedback_password + "@" + rtxConfig.mysql_feedback_host + "/" + self.databaseName)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    self.session = session
    self.engine = engine

  #### Create and store a database connection
  def disconnect(self):
    session = self.session
    engine = self.engine
    session.close()
    try:
      engine.dispose()
    except:
      pass


  #### Pre-populate the database with reference data
  def prepopulateDatabase(self):
    session = self.session
    rating = Rating(score=100,tag='Excellent',name='Excellent result',description='This result provides a correct and complete answer to the asked question.')
    session.add(rating)
    rating = Rating(score=90,tag='Very good',name='Very good result',description='This result provides a correct but slightly incomplete answer to the asked question.')
    session.add(rating)
    rating = Rating(score=80,tag='Intriguing',name='Intriguing result',description='This result may or may not be correct but provides a very intriguing thought process that bears further scrutiny.')
    session.add(rating)
    rating = Rating(score=50,tag='Good',name='Good result',description='This result provides a mostly correct but substantially incomplete answer to the asked question.')
    session.add(rating)
    rating = Rating(score=30,tag='Okay',name='Okay result',description='This result is not incorrect but is a vast oversimplification compared with a complete answer.')
    session.add(rating)
    rating = Rating(score=20,tag='Poor',name='Poor result',description='This result is some merit but includes thought paths that are incorrect.')
    session.add(rating)
    rating = Rating(score=10,tag='Irrelevant',name='Irrelevant result',description='This result does not address the question that was asked.')
    session.add(rating)
    rating = Rating(score=0,tag='Wrong',name='Wrong result',description='This result makes assertions that are wrong.')
    session.add(rating)
    session.commit()

    expertise_level = Expertise_level(score=100,tag='High',name='High expertise',description='Reviewer has a high degree of expertise related to this question and result. He or she writes papers on this question or treats patients with conditions related to this question.')
    session.add(expertise_level)
    expertise_level = Expertise_level(score=70,tag='Medium',name='Medium expertise',description='Reviewer has a medium degree of expertise related to this question and result. He or she is engaged in research or treats patients in a related field.')
    session.add(expertise_level)
    expertise_level = Expertise_level(score=50,tag='Some',name='Some expertise',description='Reviewer has some familiarity related with this question and result, but not enough to be authoritative.')
    session.add(expertise_level)
    expertise_level = Expertise_level(score=30,tag='Low',name='Low expertise',description='Reviewer has low familiarity with this question and result, but has basic understanding of biology and disease.')
    session.add(expertise_level)
    expertise_level = Expertise_level(score=10,tag='None',name='No expertise',description='Reviewer might best keep his thoughts on this to himself, but cannot prevent himself from amusing his colleagues with irrelevant nonsense. Coder.')
    session.add(expertise_level)
    session.commit()

    commenter = Commenter(full_name='Test User',email_address='testuser@systemsbioloy.org',password='None')
    session.add(commenter)
    session.commit()


  #### Store a new Message into the database
  def addNewMessage(self,message,query):
    session = self.session

    #### Update the n_results information
    n_results = 0
    if message.results is not None:
      n_results = len(message.results)
    if message.code_description is None:
      plural = "s"
      if n_results == 1: plural = ""
      message.code_description = "Query returned %i result%s" % (n_results,plural)

    #### Add result metadata
    if message.results is not None:
      for result in message.results:
        if result.reasoner_id is None:
          result.reasoner_id = "ARAX"

    #### Update the message with current information
    rtxConfig = RTXConfiguration()
    if message.tool_version is None:
      message.tool_version = rtxConfig.version
    if message.schema_version is None:
      message.schema_version = "0.9.3"
    if message.reasoner_id is None:
      message.reasoner_id = "ARAX"
    message.n_results = n_results
    message.type = "translator_reasoner_message"
    message.context = "https://raw.githubusercontent.com/biolink/biolink-model/master/context.jsonld"
    message.datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if message.restated_question is None:
      message.restated_question = ""
    if message.original_question is None:
      message.original_question = ""

    termsString = "{}"
    query_type_id = 0
    if query is not None and "query_type_id" in query:
      query_type_id = query["query_type_id"]
    if query_type_id == 0 and query is not None and "message" in query and "query_type_id" in query["message"]:
      query_type_id = query["message"]["query_type_id"]

    if query is not None and "message" in query:
      if "terms" in query["message"]:
        termsString = stringifyDict(query["message"]["terms"])
      elif "query_graph" in query["message"]:
        termsString = stringifyDict(query["message"]["query_graph"])

    storedMessage = Message(message_datetime=datetime.now(),restated_question=message.restated_question,query_type=query_type_id,
      terms=termsString,tool_version=rtxConfig.version,result_code=message.message_code,message=message.code_description,n_results=n_results,message_object=pickle.dumps(ast.literal_eval(repr(message))))
    session.add(storedMessage)
    session.flush()
    message.id = "https://arax.rtx.ai/api/rtx/v1/message/"+str(storedMessage.message_id)

    self.addNewResults(storedMessage.message_id,message)

    #### After updating all the ids, store an updated object
    storedMessage.message_object=pickle.dumps(ast.literal_eval(repr(message)))
    session.commit()

    return storedMessage.message_id


  #### Store all the results from a message into the database
  def addNewResults(self,message_id,message):
    session = self.session
    result_hash = "xxxx"
    if message.results is not None:
      for result in message.results:
        n_nodes = 0
        n_edges = 0
        #result_hash = result.description
        if result.result_type is None:
          result.result_type = "individual query answer"
        if result.confidence is None:
          result.confidence = 0
        if result.result_graph is not None:
          #### Calculate a hash from the list of nodes and edges in the result
          result_hash = self.calcResultHash(result)
          if result.result_graph.nodes is not None:
            n_nodes = len(result.result_graph.nodes)
          if result.result_graph.edges is not None:
            n_edges = len(result.result_graph.edges)
        else:
          result_hash = 'xxxx'

        #### See if there is an existing result that matches this hash
        previousResult = None
        #eprint(f"- {result_hash}")
        #if result_hash != 'xxxx':
        #  previousResult = session.query(Result).filter(Result.result_hash==result_hash).order_by(desc(Result.result_id)).first()
        #eprint("WARNING: Forcing chache miss for result at line 309")
        previousResult = None
        if previousResult is not None:
          result.id = "https://arax.rtx.ai/api/rtx/v1/result/"+str(previousResult.result_id)
          #eprint("Reused result_id " + str(result.id))

          #### Also update the linking table
          storedLink = Message_result(message_id=message_id,result_id=previousResult.result_id)
          session.add(storedLink)
          session.flush()

        else:
          storedResult = Result(message_id=message_id,confidence=result.confidence,n_nodes=n_nodes,n_edges=n_edges,result_text=result.description,result_object=pickle.dumps(ast.literal_eval(repr(result))),result_hash=result_hash)
          session.add(storedResult)
          session.flush()

          #### Also update the linking table
          storedLink = Message_result(message_id=message_id,result_id=storedResult.result_id)
          session.add(storedLink)
          session.flush()

          result.id = "https://arax.rtx.ai/api/rtx/v1/result/"+str(storedResult.result_id)
          #eprint("Stored new result. Returned result_id is "+str(storedResult.result_id)+", n_nodes="+str(n_nodes)+", n_edges="+str(n_edges)+", hash="+result_hash)
          storedResult.result_object=pickle.dumps(ast.literal_eval(repr(result)))

    session.commit()
    return


  #### Calculate a hash from the list of nodes and edges in a result
  def calcResultHash(self,result):

    #### Get a sorted list of node ids
    nodes = []
    if result.result_graph.nodes is not None:
      for node in result.result_graph.nodes:
        nodes.append(node.id)
    nodes.sort()

    #### Get a sorted list of edge types
    edges = []
    if result.result_graph.edges is not None:
      for edge in result.result_graph.edges:
        edges.append(edge.type)
    edges.sort()

    hashing_string = ",".join(nodes)+"_"+"-".join(edges)

    #### Hackathon hack!!! FIXME
    hashing_string = repr(result)

    result_hash = hashlib.md5(hashing_string.encode('utf-8'))
    result_hash_string = result_hash.hexdigest()
    #eprint(result_hash_string + " from " + hashing_string)
    return result_hash_string


  #### Get a previously stored message for this query from the database
  def getCachedMessage(self,query):
    if "bypass_cache" in query and query["bypass_cache"] == "true":
      return
    session = self.session
    rtxConfig = RTXConfiguration()
    tool_version = rtxConfig.version
    termsString = stringifyDict(query["message"]["terms"])

    #### Look for previous messages we could use
    storedMessage = session.query(Message).filter(Message.query_type==query["message"]["query_type_id"]).filter(Message.tool_version==tool_version).filter(Message.terms==termsString).order_by(desc(Message.message_datetime)).first()
    if ( storedMessage is not None ):
      return pickle.loads(storedMessage.message_object)
    return


  #### Get the list of ratings
  def getRatings(self):
    session = self.session
    message = { "ratings": [] }
    count = 0
    for rating in session.query(Rating).all():
      message["ratings"].append(object_as_dict(rating))
      count += 1
    message["n_ratings"] = count
    return(message)


  #### Get the list of expertise levels
  def getExpertiseLevels(self):
    session = self.session
    message = { "expertise_levels": [] }
    count = 0
    for level in session.query(Expertise_level).all():
      message["expertise_levels"].append(object_as_dict(level))
      count += 1
    message["n_expertise_levels"] = count
    return(message)


  #### Store all the results from a message into the database
  def addNewResultRating(self, result_id, rating):
    session = self.session

    if result_id is None:
      return( { "status": 450, "title": "result_id missing", "detail": "Required attribute result_id is missing from URL", "type": "about:blank" }, 450)
    if "expertise_level_id" not in rating or rating["expertise_level_id"] is None:
      return( { "status": 452, "title": "expertise_level_id missing", "detail": "Required attribute expertise_level_id missing from body content", "type": "about:blank" }, 452)
    if "rating_id" not in rating or rating["rating_id"] is None:
      return( { "status": 453, "title": "rating_id missing", "detail": "Required attribute rating_id missing from body content", "type": "about:blank" }, 453)
    if "comment" not in rating or rating["comment"] is None:
      return( { "status": 454, "title": "comment missing", "detail": "Required attribute comment missing from body content", "type": "about:blank" }, 454)
    if len(rating["comment"]) > 65000:
      return( { "status": 455, "title": "comment too long", "detail": "Comment attribute max lenth is 65 kB", "type": "about:blank" }, 455)

    if "commenter_id" not in rating or rating["commenter_id"] is None:
      if "commenter_full_name" not in rating or rating["commenter_full_name"] is None:
        return( { "status": 451, "title": "commenter_id and commenter_name are missing", "detail": "Required attributes either commenter_id or commenter_full_name are missing from body content", "type": "about:blank" }, 451)
      else:
        existingCommenter = session.query(Commenter).filter(Commenter.full_name==rating["commenter_full_name"]).first()
        if existingCommenter is None:
          newCommenter = Commenter(full_name=rating["commenter_full_name"],email_address="?",password="?")
          session.add(newCommenter)
          session.flush()
          rating["commenter_id"] = newCommenter.commenter_id
        else:
          rating["commenter_id"] = existingCommenter.commenter_id

    try:
      insertResult = Result_rating(result_id=result_id, commenter_id=rating["commenter_id"], expertise_level_id=rating["expertise_level_id"],
        rating_id = rating["rating_id"], comment=rating["comment"].encode('utf-8'), comment_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S") )
      session.add(insertResult)
      session.flush()
      session.commit()
    except Exception as error:
      return( { "status": 460, "title": "Error storing feedback", "detail": "Your feedback was not stored because of error: "+str(error), "type": "about:blank" }, 460 )

    return( { "status": 200, "title": "Feedback stored", "detail": "Your feedback has been stored by ARAX as id="+str(insertResult.result_rating_id), "type": "about:blank" }, 200 )


  #### Fetch all available feedback
  def getAllFeedback(self):
    session = self.session

    storedRatings = session.query(Result_rating).all()
    if storedRatings is not None:
      resultRatings = []
      for rating in storedRatings:
        resultRating = Feedback()
        resultRating.result_id = "https://arax.rtx.ai/api/rtx/v1/result/"+str(rating.result_id)
        resultRating.id = resultRating.result_id + "/feedback/" + str(rating.result_rating_id)
        resultRating.expertise_level_id = rating.expertise_level_id
        resultRating.rating_id = rating.rating_id
        resultRating.commenter_id = rating.commenter_id
        resultRating.commenter_name = 'not available'
        resultRating.comment = rating.comment
        resultRating.datetime = rating.comment_datetime
        resultRatings.append(resultRating)
      return(resultRatings)
    else:
      return


  #### Fetch the feedback for a result
  def getResultFeedback(self, result_id):
    session = self.session

    if result_id is None:
      return( { "status": 450, "title": "result_id missing", "detail": "Required attribute result_id is missing from URL", "type": "about:blank" }, 450)

    #### Look for ratings we could use
    storedRatings = session.query(Result_rating).filter(Result_rating.result_id==result_id).order_by(desc(Result_rating.comment_datetime)).all()
    if storedRatings is not None:
      resultRatings = []
      for rating in storedRatings:
        resultRating = Feedback()
        resultRating.result_id = "https://arax.rtx.ai/api/rtx/v1/result/"+str(result_id)
        resultRating.id = resultRating.result_id + "/feedback/" + str(rating.result_rating_id)
        resultRating.expertise_level_id = rating.expertise_level_id
        resultRating.rating_id = rating.rating_id
        resultRating.commenter_id = rating.commenter_id
        resultRating.comment = rating.comment
        resultRating.datetime = rating.comment_datetime
        resultRating.foobar = -1		# turns out you can put in anything you want, but it doesn't show up in the output unless the YAML says it can

        commenterFullName = session.query(Commenter).filter(Commenter.commenter_id==rating.commenter_id).first().full_name
        resultRating.commenter_full_name = commenterFullName

        resultRatings.append(resultRating)
      return(resultRatings)
    else:
      return


  #### Fetch the feedback for a message
  def getMessageFeedback(self, message_id):
    session = self.session

    if message_id is None:
      return( { "status": 450, "title": "message_id missing", "detail": "Required attribute message_id is missing from URL", "type": "about:blank" }, 450)

    #### Look for results for this message
    storedMessageResults = session.query(Message_result).filter(Message_result.message_id==message_id).all()
    #eprint("DEBUG: Getting results for message_id="+str(message_id))
    if storedMessageResults is not None:
      allResultRatings = []
      for storedMessageResult in storedMessageResults:
        #eprint("DEBUG:   Getting feedback for result_id="+str(storedMessageResult.result_id))
        resultRatings = self.getResultFeedback(storedMessageResult.result_id)
        if resultRatings is not None:
          for resultRating in resultRatings:
            allResultRatings.append(resultRating)
      if len(allResultRatings) > 0:
        return(allResultRatings)
      else:
        return( { "status": 404, "title": "Ratings not found", "detail": "There were no ratings found for this message", "type": "about:blank" }, 404)
    else:
      return( { "status": 404, "title": "Results not found", "detail": "There were no results found for this message", "type": "about:blank" }, 404)


  #### Fetch a cached message
  def getMessage(self, message_id):
    session = self.session

    if message_id is None:
      return( { "status": 450, "title": "message_id missing", "detail": "Required attribute message_id is missing from URL", "type": "about:blank" }, 450)

    #### Find the message
    storedMessage = session.query(Message).filter(Message.message_id==message_id).first()
    if storedMessage is not None:
      return pickle.loads(storedMessage.message_object)
    else:
      return( { "status": 404, "title": "Message not found", "detail": "There is no message corresponding to message_id="+str(message_id), "type": "about:blank" }, 404)


  #### Fetch a cached result
  def getResult(self, result_id):
    session = self.session

    if result_id is None:
      return( { "status": 450, "title": "result_id missing", "detail": "Required attribute result_id is missing from URL", "type": "about:blank" }, 450)

    #### Find the result
    storedResult = session.query(Result).filter(Result.result_id==result_id).first()
    if storedResult is not None:
      return pickle.loads(storedResult.result_object)
    else:
      return( { "status": 404, "title": "Result not found", "detail": "There is no result corresponding to result_id="+str(result_id), "type": "about:blank" }, 404)


  #### Get a previously stored message for this query from the database
  def processExternalPreviousMessageProcessingPlan(self,inputEnvelope):
    debug = 1
    if debug: eprint("DEBUG: Entering processExternalPreviousMessageProcessingPlan")
    messages = []
    finalMessage = None
    finalMessage_id = None
    query = None

    #### Pull out the main processing plan envelope
    envelope = PreviousMessageProcessingPlan.from_dict(inputEnvelope["previous_message_processing_plan"])

    #### If there are URIs provided, try to load them
    if envelope.previous_message_uris is not None:
      if debug: eprint("DEBUG: Got previous_message_uris")
      for uri in envelope.previous_message_uris:
        if debug: eprint("DEBUG:   messageURI="+uri)
        matchResult = re.match( r'http[s]://arax.rtx.ai/.*api/rtx/.+/message/(\d+)',uri,re.M|re.I )
        if matchResult:
          message_id = matchResult.group(1)
          if debug: eprint("DEBUG: Found local ARAX identifier corresponding to message_id "+message_id)
          if debug: eprint("DEBUG: Loading message_id "+message_id)
          message = self.getMessage(message_id)
          #eprint(type(message))
          if not isinstance(message,tuple):
            if debug: eprint("DEBUG: Original question was: "+message["original_question"])
            messages.append(message)
            finalMessage_id = message_id
            query = { "query_type_id": message["query_type_id"], "restated_question": message["restated_question"], "terms": message["terms"] }
          else:
            eprint("ERROR: Unable to load message_id "+message_id)
            return( { "status": 404, "title": "Message not found", "detail": "There is no local message corresponding to message_id="+str(message_id), "type": "about:blank" }, 404)

    #### If there are one or more previous_messages embedded in the POST, process them
    if envelope.previous_messages is not None:
      if debug: eprint("DEBUG: Got previous_messages")
      for uploadedMessage in envelope.previous_messages:
        if debug: eprint("DEBUG: uploadedMessage is a "+str(uploadedMessage.__class__))
        if str(uploadedMessage.__class__) == "<class 'swagger_server.models.message.Message'>":
          if uploadedMessage.results:
            message = ast.literal_eval(repr(uploadedMessage))
            messages.append(message)

            if message["terms"] is None:
              message["terms"] = { "dummyTerm": "giraffe" }
            if message["query_type_id"] is None:
              message["query_type_id"] = "UnknownQ"
            if message["restated_question"] is None:
              message["restated_question"] = "What is life?"
            if message["original_question"] is None:
              message["original_question"] = "what is life"

            query = { "query_type_id": message["query_type_id"], "restated_question": message["restated_question"], "original_question": message["original_question"], "terms": message["terms"] }
          else:
            eprint("Uploaded message does not contain a results. May be the wrong format")
            return( { "status": 404, "title": "Bad uploaded Message", "detail": "There is no results in the uploaded Message object=", "type": "about:blank" }, 404)
        else:
          eprint("Uploaded message is not of type Message. It is of type"+str(uploadedMessage.__class__))
          return( { "status": 404, "title": "Bad uploaded Message", "detail": "Uploaded message is not of type Message. It is of type"+str(uploadedMessage.__class__), "type": "about:blank" }, 404)

    #### Take different actions based on the number of messages we now have in hand
    n_messages = len(messages)
    if n_messages == 0:
      return( { "status": 499, "title": "No Messages", "detail": "Did not get any useful Message objects", "type": "about:blank" }, 499)
    elif n_messages == 1:
      finalMessage = messages[0]
    else:
      finalMessage = TxMessage.from_dict(messages[0])
      counter = 1
      while counter < n_messages:
        messageToMerge = TxMessage.from_dict(messages[counter])
        if messageToMerge.reasoner_id is None:
          messageToMerge.reasoner_id = "Unknown"
        if messageToMerge.reasoner_id != "ARAX":
          messageToMerge = self.fix_message(query,messageToMerge,messageToMerge.reasoner_id)

        finalMessage = self.merge_message(finalMessage,messageToMerge)
        counter += 1
      finalMessage = ast.literal_eval(repr(finalMessage))
      #return( { "status": 498, "title": "Multiple Messages", "detail": "I have multiple messages. Merging code awaits!", "type": "about:blank" }, 498)

    #### Examine the options that were provided and act accordingly
    optionsDict = {}
    if envelope.options:
      if debug: eprint("DEBUG: Got options")
      for option in envelope.options:
        if debug: eprint("DEBUG:   option="+option)
        optionsDict[option] = 1

    #### If there are processing_actions, then fulfill those
    processing_actions = []
    if envelope.processing_actions:
      if debug: eprint("DEBUG: Found processing_actions")
      actions_parser = ActionsParser()
      result = actions_parser.parse(envelope.processing_actions)
      if result.error_code != 'OK':
        eprint(result)
        raise()

      #### Message suffers from a dual life as a dict and an object. above we seem to treat it as a dict. Fix that. FIXME
      #### Below we start treating it as and object. This should be the way forward.
      #### This is not a good place to do this, but may need to convert here
      from ARAX_messenger import ARAXMessenger
      finalMessage = ARAXMessenger().from_dict(finalMessage)

      #### Process each action in order
      action_stats = { }
      actions = result.data['actions']
      for action in actions:
        if debug: eprint(f"DEBUG: Considering action '{action['command']}' with parameters {action['parameters']}")
        #### If we encounter a return, then this is the end of the line
        if action['command'] == 'return':
          action_stats['return_action'] = action
          break
        if action['command'] == 'filter':
          filter = ARAXFilter()
          result = filter.apply(finalMessage,action['parameters'])
        if result.error_code != 'OK':
            response = result
            break
        else:
          if debug: eprint(f"DEBUG: Action '{action['command']}' is not known")

      #### At the end, process the explicit return() action, or implicitly perform one
      return_action = { 'command': 'return', 'parameters': { 'message': 'false', 'store': 'false' } }
      if action is not None and action['command'] == 'return':
        return_action = action
        #### If an explicit one left out some parameters, set the defaults
        if 'store' not in return_action['parameters']:
          return_action['parameters']['store'] == 'false'
        if 'message' not in return_action['parameters']:
          return_action['parameters']['message'] == 'false'

    #if "AnnotateDrugs" in optionsDict:
    #  if debug: eprint("DEBUG: Annotating drugs")
    #  annotate_std_results(finalMessage)

    if return_action['parameters']['store'] == 'true':
      if debug: eprint("DEBUG: Storing resulting Message")
      finalMessage_id = self.addNewMessage(TxMessage.from_dict(finalMessage),query)

    #### If requesting a full redirect to the resulting message display. This doesn't really work I don't think
    #if "RedirectToMessage" in optionsDict:
    #  #redirect("https://arax.rtx.ai/api/rtx/v1/message/"+str(finalMessage_id), code=302)
    #  #return( { "status": 302, "redirect": "https://arax.rtx.ai/api/rtx/v1/message/"+str(finalMessage_id) }, 302)
    #  return( "Location: https://arax.rtx.ai/api/rtx/v1/message/"+str(finalMessage_id), 302)

    #### If asking for the full message back
    if return_action['parameters']['message'] == 'true':
      return(finalMessage)

    #### Else just the id is returned
    else:
      #return( { "status": 200, "message_id": str(finalMessage_id), "n_results": finalMessage['n_results'], "url": "https://arax.rtx.ai/api/rtx/v1/message/"+str(finalMessage_id) }, 200)
      return( { "status": 200, "message_id": str(finalMessage_id), "n_results": finalMessage.n_results, "url": "https://arax.rtx.ai/api/rtx/v1/message/"+str(finalMessage_id) }, 200)


  ##########################################################################################################################
  def fix_message(self,query,message,reasoner_id):

    if reasoner_id == "ARAX":
      base_url = "https://arax.rtx.ai/api/rtx/v1"
    elif reasoner_id == "Robokop":
      base_url = "http://robokop.renci.org:6011/api"
    elif reasoner_id == "Indigo":
      base_url = "https://indigo.ncats.io/reasoner/api/v0"
    else:
      base_url = "https://unknown.url.org/"
      eprint("ERROR: Unrecognized reasoner_id '"+reasoner_id+"'")

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




############################################ General functions ###############################################
#### Turn a row into a dict
def object_as_dict(obj):
  return {c.key: getattr(obj, c.key)
    for c in inspect(obj).mapper.column_attrs}

#### convert a dict into a string in guaranteed repeatable order i.e. sorted
def stringifyDict(inputDict):
  outString = "{"
  for key,value in sorted(inputDict.items(), key=lambda t: t[0]):
    if outString != "{":
      outString += ","
    outString += "'"+str(key)+"':'"+str(value)+"'"
  outString += "}"
  return(outString)



# This is from Kevin Xin from team orange.
# It performs MOD1 and MOD2 (annotation and scoring modules) of workflow 1
# input std API message format
# output std API message format

def annotate_drug(drug_id, id_type):
    """
    Provide annotation for drug
    """
    if id_type == 'chembl':
        query_template = 'http://mychem.info/v1/query?q=drugcentral.xrefs.chembl_id:{{drug_id}}&fields=drugcentral'
    elif id_type == 'chebi':
        query_template = 'http://mychem.info/v1/query?q=drugcentral.xrefs.chebi:"{{drug_id}}"&fields=drugcentral'
    query_url = query_template.replace('{{drug_id}}', drug_id)
    results = {'annotate': {'common_side_effects': None, 'approval': None, 'indication': None, 'EPC': None}}
    api_message = requests.get(query_url).json()

    # get drug approval information from mychem
    approval = DictQuery(api_message).get("hits/drugcentral/approval")
    if approval:
        results['annotate']['approval'] = 'Yes'
    # get drug approved indication information
    indication = DictQuery(api_message).get("hits/drugcentral/drug_use/indication")
    if len(indication) > 0 and indication[0] and not isinstance(indication[0], list):
        results['annotate']['indication'] = [_doc['snomed_full_name'] for _doc in indication if
                                             'snomed_full_name' in _doc]
    elif len(indication) > 0 and indication[0]:
        results['annotate']['indication'] = [_doc['snomed_full_name'] for _doc in indication[0] if
                                             'snomed_full_name' in _doc]
        # get drug established pharm class information
    epc = DictQuery(api_message).get("hits/drugcentral/pharmacology_class/fda_epc")
    if len(epc) > 0 and epc[0] and not isinstance(epc[0], list):
        results['annotate']['EPC'] = [_doc['description'] for _doc in epc if 'description' in _doc]
    elif len(epc) > 0 and epc[0]:
        results['annotate']['EPC'] = [_doc['description'] for _doc in epc[0] if 'description' in _doc]
        # get drug common side effects
    side_effects = DictQuery(api_message).get("hits/drugcentral/fda_adverse_event")
    if len(side_effects) > 0 and side_effects[0]:
        if isinstance(side_effects[0], list):
            # only keep side effects with likelihood higher than the threshold
            results['annotate']['common_side_effects'] = [_doc['meddra_term'] for _doc in side_effects[0] if
                                                          _doc['llr'] > _doc['llr_threshold']]
            if len(results['annotate']['common_side_effects']) > 10:
                results['annotate']['common_side_effects'] = results['annotate']['common_side_effects'][:10]
        elif isinstance(side_effects[0], dict) and 'meddra_term' in side_effects[0]:
          results['annotate']['common_side_effects'] = side_effects[0]['meddra_term']

    #### EWD: Now transform this into the schema!
    results = unlist(results)
    node_attributes = []
    for key,value in results["annotate"].items():
      if isinstance(value,list):
        counter = 0
        for item in value:
          node_attributes.append( { "name": key, "value": item } )
          counter += 1
          if counter > 11: break
      else:
        node_attributes.append( { "name": key, "value": value } )
    return node_attributes

    #return unlist(results)
    

"""
Helper functions
"""
def unlist(d):
    """
    If the list contain only one element, unlist it
    """
    for key, val in d.items():
            if isinstance(val, list):
                if len(val) == 1:
                    d[key] = val[0]
            elif isinstance(val, dict):
                unlist(val)
    return d

class DictQuery(dict):
    """
    Helper function to fetch value from a python dictionary
    """
    def get(self, path, default = None):
        keys = path.split("/")
        val = None

        for key in keys:
            if val:
                if isinstance(val, list):
                    val = [ v.get(key, default) if v else None for v in val]
                else:
                    val = val.get(key, default)
            else:
                val = dict.get(self, key, default)

            if not val:
                break;

        return val


def annotate_std_results(input_json_doc):
    """
    Annotate results from reasoner's standard output
    """
    for _doc in input_json_doc['results']:
        if 'result_graph' in _doc and _doc['result_graph'] is not None:
            eprint("Found result_graph and it is")
            eprint(_doc['result_graph'])
            for _node in _doc['result_graph']['nodes']:
                if _node['id'].startswith('CHEMBL'):
                    _drug = _node['id'].split(':')[-1]
                    _node['node_attributes'] = annotate_drug(_drug, 'chembl')
                elif _node['id'].startswith("CHEBI:"):
                    _node['node_attributes'] = annotate_drug(_node['id'], 'chebi')
    if 'knowledge_graph' in input_json_doc:
        for _node in input_json_doc['knowledge_graph']['nodes']:
            if _node['id'].startswith('CHEMBL'):
                _drug = _node['id'].split(':')[-1]
                _node['node_attributes'] = annotate_drug(_drug, 'chembl')
            elif _node['id'].startswith("CHEBI:"):
                _node['node_attributes'] = annotate_drug(_node['id'], 'chebi')
    return input_json_doc






#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

  #### Create a new RTXFeedback object
  rtxFeedback = RTXFeedback()
  envelope = PreviousMessageProcessingPlan()
  #envelope.options = [ "Store", "RedirectToMessage" ]
  envelope.options = [ "AnnotateDrugs", "Store", "ReturnMessageId" ]
  #envelope.options = [ "ReturnMessage" ]
  #envelope.options = [ "AnnotateDrugs", "ReturnMessage" ]
  envelope.message_ur_is = [ "https://arax.rtx.ai/api/rtx/v1/message/300" ]

  #result = rtxFeedback.processExternalPreviousMessageProcessingPlan(envelope)
  #print(result)



  #### Careful, don't destroy an important database!!!
  ##rtxFeedback.createDatabase()
  ##rtxFeedback.prepopulateDatabase()
  #sys.exit()

  #### Connect to the database
  session = rtxFeedback.session

  #### Query and print some rows from the reference tables
  print("Querying database")
  for rating in session.query(Rating).all():
    print(rating)
    print("rating_id="+str(rating.rating_id)+"  name="+rating.name+"\n")

  for expertise_level in session.query(Expertise_level).all():
    print(expertise_level)
    print("expertise_level_id="+str(expertise_level.expertise_level_id)+"  name="+expertise_level.name+"\n")

  print(rtxFeedback.getRatings())


if __name__ == "__main__": main()
