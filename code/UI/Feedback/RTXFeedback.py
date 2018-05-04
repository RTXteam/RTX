#!/usr/bin/python3
# Database definition and RTXFeedback class

import os
import sys
import json
import ast
from datetime import datetime
import pickle

from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime, Text, PickleType, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc

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
  response_id = Column(Integer, ForeignKey('response.response_id'))
  confidence = Column(Float, nullable=False)
  n_nodes = Column(Integer, nullable=False)
  n_edges = Column(Integer, nullable=False)
  result_text = Column(String(1024), nullable=False)
  #result_object = Column(PickleType, nullable=False)
  result_object = Column(LargeBinary(length=16777200), nullable=False)
  result_hash = Column(String(255), nullable=False)
  response = relationship(Response)

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
  comment = Column(Text, nullable=True)
  result = relationship(Result)
  commenter = relationship(Commenter)
  expertise_level = relationship(Expertise_level)
  rating = relationship(Rating)


#### The main RTXFeedback class
class RTXFeedback:

  #### Constructor
  def __init__(self):
    #self.databaseName = "RTXFeedback.sqlite.db"
    self.databaseName = "RTXFeedback"


  #### Define attribute session
  @property
  def session(self) -> str:
    return self._session

  @session.setter
  def session(self, session: str):
    self._session = session


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


  #### Store a new Response into the database
  def addNewResponse(self,response,query):
    session = self.session
    n_results = 0
    if response.result_list is not None:
      n_results = len(response.result_list)
    if response.tool_version is None:
      response.tool_version = "RTX 0.4"

    storedResponse = Response(response_datetime=datetime.now(),restated_question=response.restated_question_text,query_type=query["known_query_type_id"],
      terms=str(query["terms"]),tool_version=response.tool_version,result_code=response.result_code,message=response.message,n_results=n_results,response_object=pickle.dumps(ast.literal_eval(repr(response))))
    session.add(storedResponse)
    session.flush()
    #print("Returned response_id is "+str(storedResponse.response_id))
    response.id = "http://rtx.ncats.io/api/v1/response/"+str(storedResponse.response_id)

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
        if result.result_graph.node_list is not None:
          n_nodes = len(result.result_graph.node_list)
        if result.result_graph.edge_list is not None:
          n_edges = len(result.result_graph.edge_list)

        #### Calculate a hash from the list of nodes and edges in the result
        result_hash = self.calcResultHash(result)
        storedResult = Result(response_id=response_id,confidence=result.confidence,n_nodes=n_nodes,n_edges=n_edges,result_text=result.text,result_object=pickle.dumps(ast.literal_eval(repr(result))),result_hash=result_hash)
        session.add(storedResult)
        session.flush()
        result.id = response.id+"/result/"+str(storedResult.result_id)
        #print("Returned result_id is "+str(storedResult.result_id)+", n_nodes="+str(n_nodes)+", n_edges="+str(n_edges)+", hash="+result_hash)
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

    result_hash = str(hash(",".join(nodes)+"_"+"-".join(edges)))
    return result_hash


  #### Get a previously stored response for this query from the database
  def getCachedResponse(self,query):
    session = self.session
    tool_version = "RTX 0.4"
    #### Look for previous responses we could use
    storedResponse = session.query(Response).filter(Response.query_type==query["known_query_type_id"]).filter(Response.tool_version==tool_version).filter(Response.terms==str(query["terms"])).order_by(desc(Response.response_datetime)).first()
    if ( storedResponse is not None ):
      return pickle.loads(storedResponse.response_object)
    return

#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

  #### Create a new RTXFeedback object
  rtxFeedback = RTXFeedback()

  #### Careful, don't destroy an important database!!!
  ###rtxFeedback.createDatabase()
  ###rtxFeedback.prepopulateDatabase()

  #### Connect to the database
  rtxFeedback.connect()
  session = rtxFeedback.session

  #### Query and print some rows from the reference tables
  print("Querying database")
  for rating in session.query(Rating).all():
    print(rating)
    print("rating_id="+str(rating.rating_id)+"  name="+rating.name+"\n")

  for expertise_level in session.query(Expertise_level).all():
    print(expertise_level)
    print("expertise_level_id="+str(expertise_level.expertise_level_id)+"  name="+expertise_level.name+"\n")


if __name__ == "__main__": main()
