#!/usr/bin/python3
# Database definition and RTXFeedback class
from __future__ import print_function
import sys
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

import os
import sys
import json
import ast
from datetime import datetime
import pickle
import hashlib
import collections

from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime, Text, PickleType, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from sqlalchemy import inspect

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

#sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.result_feedback import ResultFeedback
from swagger_server.models.feedback import Feedback

Base = declarative_base()

#### Define the database tables as classes
class Response(Base):
  __tablename__ = 'response'
  response_id = Column(Integer, primary_key=True)
  response_datetime = Column(DateTime, nullable=False)
  restated_question = Column(String(255), nullable=False)
  query_type = Column(String(50), nullable=False)
  terms = Column(String(1024), nullable=False)
  tool_version = Column(String(50), nullable=False)
  result_code = Column(String(50), nullable=False)
  message = Column(String(255), nullable=False)
  n_results = Column(Integer, nullable=False)
  # PickleType uses BLOB on MySQL, which is only 65k. Could not seem to work around it. Resort to LargeBinary with explicit length and my own pickling.
  #response_object = Column(PickleType, nullable=False)
  response_object = Column(LargeBinary(length=100500500), nullable=False)

class Result(Base):
  __tablename__ = 'result'
  result_id = Column(Integer, primary_key=True)
  response_id = Column(Integer, ForeignKey('response.response_id'))   # for backward compat, this is retained as the *first* response_id
  confidence = Column(Float, nullable=False)
  n_nodes = Column(Integer, nullable=False)
  n_edges = Column(Integer, nullable=False)
  result_text = Column(String(1024), nullable=False)
  result_object = Column(LargeBinary(length=16777200), nullable=False)
  result_hash = Column(String(255), nullable=False)
  response = relationship(Response)

class Response_result(Base):
  __tablename__ = 'response_result'
  response_result_id = Column(Integer, primary_key=True)
  result_id = Column(Integer, ForeignKey('result.result_id'))
  response_id = Column(Integer, ForeignKey('response.response_id'))

class Commenter(Base):
  __tablename__ = 'commenter'
  commenter_id = Column(Integer, primary_key=True)
  full_name = Column(String(255), nullable=False)
  email_address = Column(String(255), nullable=False)
  password = Column(String(255), nullable=False)


class Rating(Base):
  __tablename__ = 'rating'
  rating_id = Column(Integer, primary_key=True)
  score = Column(Integer, nullable=False)
  tag = Column(String(50), nullable=False)
  name = Column(String(255), nullable=False)
  description = Column(String(255), nullable=False)


class Expertise_level(Base):
  __tablename__ = 'expertise_level'
  expertise_level_id = Column(Integer, primary_key=True)
  score = Column(Integer, nullable=False)
  tag = Column(String(50), nullable=False)
  name = Column(String(255), nullable=False)
  description = Column(String(255), nullable=False)


class Result_rating(Base):
  __tablename__ = 'result_rating'
  result_rating_id = Column(Integer, primary_key=True)
  result_id = Column(Integer, ForeignKey('result.result_id'))
  commenter_id = Column(Integer, ForeignKey('commenter.commenter_id'))
  expertise_level_id = Column(Integer, ForeignKey('expertise_level.expertise_level_id'))
  rating_id = Column(Integer, ForeignKey('rating.rating_id'))
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
    engine = create_engine("mysql+pymysql://rt:Steve1000Ramsey@localhost/"+self.databaseName)
    Base.metadata.create_all(engine)
    self.connect()

  #### Create and store a database connection
  def connect(self):
    #engine = create_engine("sqlite:///"+self.databaseName)
    engine = create_engine("mysql+pymysql://rt:Steve1000Ramsey@localhost/"+self.databaseName)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    self.session = session
    self.engine = engine

  #### Create and store a database connection
  def disconnect(self):
    session = self.session
    engine = self.engine
    session.close()
    engine.dispose()

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


  #### Store a new Response into the database
  def addNewResponse(self,response,query):
    session = self.session
    n_results = 0
    if response.result_list is not None:
      n_results = len(response.result_list)

    #### Add result metadata
    if response.result_list is not None:
      for result in response.result_list:
        result.reasoner_id = "RTX"

    #### Update the response with current information
    rtxConfig = RTXConfiguration()
    response.tool_version = rtxConfig.version
    response.schema_version = "0.8.0"
    response.reasoner_id = "RTX"
    response.n_reasoner = n_results
    response.type = "medical_translator_query_response"
    response.context = "https://raw.githubusercontent.com/biolink/biolink-model/master/context.jsonld"
    response.datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if response.restated_question_text is None:
      response.restated_question_text = ""
    if response.original_question_text is None:
      response.original_question_text = ""

    termsString = stringifyDict(query["terms"])
    storedResponse = Response(response_datetime=datetime.now(),restated_question=response.restated_question_text,query_type=query["query_type_id"],
      terms=termsString,tool_version=rtxConfig.version,result_code=response.response_code,message=response.message,n_results=n_results,response_object=pickle.dumps(ast.literal_eval(repr(response))))
    session.add(storedResponse)
    session.flush()
    response.id = "https://rtx.ncats.io/api/rtx/v1/response/"+str(storedResponse.response_id)

    self.addNewResults(storedResponse.response_id,response)

    #### After updating all the ids, store an updated object
    storedResponse.response_object=pickle.dumps(ast.literal_eval(repr(response)))
    session.commit()

    return storedResponse.response_id


  #### Store all the results from a response into the database
  def addNewResults(self,response_id,response):
    session = self.session
    result_hash = "xxxx"
    if response.result_list is not None:
      for result in response.result_list:
        n_nodes = 0
        n_edges = 0
        result_hash = result.text
        if result.result_type is None:
          result.result_type = "individual query answer"
        if result.confidence is None:
          result.confidence = 0
        if result.result_graph is not None:
          #### Calculate a hash from the list of nodes and edges in the result
          result_hash = self.calcResultHash(result)
          if result.result_graph.node_list is not None:
            n_nodes = len(result.result_graph.node_list)
          if result.result_graph.edge_list is not None:
            n_edges = len(result.result_graph.edge_list)

        #### See if there is an existing result that matches this hash
        previousResult = session.query(Result).filter(Result.result_hash==result_hash).order_by(desc(Result.result_id)).first()
        if previousResult is not None:
          result.id = "https://rtx.ncats.io/api/rtx/v1/result/"+str(previousResult.result_id)
          #eprint("Reused result_id " + str(result.id))

          #### Also update the linking table
          storedLink = Response_result(response_id=response_id,result_id=previousResult.result_id)
          session.add(storedLink)
          session.flush()

        else:
          storedResult = Result(response_id=response_id,confidence=result.confidence,n_nodes=n_nodes,n_edges=n_edges,result_text=result.text,result_object=pickle.dumps(ast.literal_eval(repr(result))),result_hash=result_hash)
          session.add(storedResult)
          session.flush()

          #### Also update the linking table
          storedLink = Response_result(response_id=response_id,result_id=storedResult.result_id)
          session.add(storedLink)
          session.flush()

          result.id = "https://rtx.ncats.io/api/rtx/v1/result/"+str(storedResult.result_id)
          #eprint("Returned result_id is "+str(storedResult.result_id)+", n_nodes="+str(n_nodes)+", n_edges="+str(n_edges)+", hash="+result_hash)
          storedResult.result_object=pickle.dumps(ast.literal_eval(repr(result)))

    session.commit()
    return


  #### Calculate a hash from the list of nodes and edges in a result
  def calcResultHash(self,result):

    #### Get a sorted list of node ids
    nodes = []
    if result.result_graph.node_list is not None:
      for node in result.result_graph.node_list:
        nodes.append(node.id)
    nodes.sort()

    #### Get a sorted list of edge types
    edges = []
    if result.result_graph.edge_list is not None:
      for edge in result.result_graph.edge_list:
        edges.append(edge.type)
    edges.sort()

    hashing_string = ",".join(nodes)+"_"+"-".join(edges)
    result_hash = hashlib.md5(hashing_string.encode('utf-8'))
    result_hash_string = result_hash.hexdigest()
    #eprint(result_hash_string + " from " + hashing_string)
    return result_hash_string


  #### Get a previously stored response for this query from the database
  def getCachedResponse(self,query):
    if "bypass_cache" in query and query["bypass_cache"] == "true":
      return
    session = self.session
    rtxConfig = RTXConfiguration()
    tool_version = rtxConfig.version
    termsString = stringifyDict(query["terms"])

    #### Look for previous responses we could use
    storedResponse = session.query(Response).filter(Response.query_type==query["query_type_id"]).filter(Response.tool_version==tool_version).filter(Response.terms==termsString).order_by(desc(Response.response_datetime)).first()
    if ( storedResponse is not None ):
      return pickle.loads(storedResponse.response_object)
    return


  #### Get the list of ratings
  def getRatings(self):
    session = self.session
    response = { "ratings": [] }
    count = 0
    for rating in session.query(Rating).all():
      response["ratings"].append(object_as_dict(rating))
      count += 1
    response["n_ratings"] = count
    return(response)


  #### Get the list of expertise levels
  def getExpertiseLevels(self):
    session = self.session
    response = { "expertise_levels": [] }
    count = 0
    for level in session.query(Expertise_level).all():
      response["expertise_levels"].append(object_as_dict(level))
      count += 1
    response["n_expertise_levels"] = count
    return(response)


  #### Store all the results from a response into the database
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

    return( { "status": 200, "title": "Feedback stored", "detail": "Your feedback has been stored by RTX as id="+str(insertResult.result_rating_id), "type": "about:blank" }, 200 )


  #### Fetch all available feedback
  def getAllFeedback(self):
    session = self.session

    storedRatings = session.query(Result_rating).all()
    if storedRatings is not None:
      resultRatings = []
      for rating in storedRatings:
        resultRating = Feedback()
        resultRating.result_id = "https://rtx.ncats.io/api/rtx/v1/result/"+str(rating.result_id)
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
        resultRating.result_id = "https://rtx.ncats.io/api/rtx/v1/result/"+str(result_id)
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


  #### Fetch the feedback for a response
  def getResponseFeedback(self, response_id):
    session = self.session

    if response_id is None:
      return( { "status": 450, "title": "response_id missing", "detail": "Required attribute response_id is missing from URL", "type": "about:blank" }, 450)

    #### Look for results for this response
    storedResponseResults = session.query(Response_result).filter(Response_result.response_id==response_id).all()
    #eprint("DEBUG: Getting results for response_id="+str(response_id))
    if storedResponseResults is not None:
      allResultRatings = []
      for storedResponseResult in storedResponseResults:
        #eprint("DEBUG:   Getting feedback for result_id="+str(storedResponseResult.result_id))
        resultRatings = self.getResultFeedback(storedResponseResult.result_id)
        if resultRatings is not None:
          for resultRating in resultRatings:
            allResultRatings.append(resultRating)
      if len(allResultRatings) > 0:
        return(allResultRatings)
      else:
        return( { "status": 404, "title": "Ratings not found", "detail": "There were no ratings found for this response", "type": "about:blank" }, 404)
    else:
      return( { "status": 404, "title": "Results not found", "detail": "There were no results found for this response", "type": "about:blank" }, 404)


  #### Fetch a cached response
  def getResponse(self, response_id):
    session = self.session

    if response_id is None:
      return( { "status": 450, "title": "response_id missing", "detail": "Required attribute response_id is missing from URL", "type": "about:blank" }, 450)

    #### Find the response
    storedResponse = session.query(Response).filter(Response.response_id==response_id).first()
    if storedResponse is not None:
      return pickle.loads(storedResponse.response_object)
    else:
      return( { "status": 404, "title": "Response not found", "detail": "There is no response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)


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


  #### Get a previously stored response for this query from the database
  def processExternalResponseEnvelope(self,envelope):
    debug = 1
    if debug: eprint("DEBUG: Entering processExternalResponseEnvelope")
    if responseURIs in envelope:
      if debug: eprint("DEBUG: Got responseURIs")
      
    if debug: eprint("DEBUG: Exiting processExternalResponseEnvelope")
    return()




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



#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

  #### Create a new RTXFeedback object
  rtxFeedback = RTXFeedback()

  #### Careful, don't destroy an important database!!!
  ##rtxFeedback.createDatabase()
  ##rtxFeedback.prepopulateDatabase()
  sys.exit()

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
