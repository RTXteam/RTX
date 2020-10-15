#!/usr/bin/python3

import sys
import os
import time
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, PickleType
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

Base = declarative_base()

class ARAXQuery(Base):
  __tablename__ = 'arax_query'
  query_id = Column(Integer, primary_key=True)
  status = Column(String(50), nullable=False)
  start_datetime = Column(DateTime, nullable=False)
  end_datetime = Column(DateTime, nullable=True)
  elapsed = Column(Float, nullable=True) ## seconds
  pid = Column(Integer, nullable=False)
  instance_name = Column(String(50), nullable=False)
  origin = Column(String(50), nullable=False)
  input_query = Column(PickleType, nullable=False) ## blob object
  message_id = Column(Integer, nullable=True)
  message_code = Column(String(50), nullable=True)
  code_description = Column(String(50), nullable=True)

class ARAXQueryTracker:

  def __init__(self):
    self.session = ""
    self.databaseName = "RTXFeedback"
    self.connect() 

  def __del__(self):
    self.disconnect()

  def create_database(self):
    rtxConfig = RTXConfiguration()
    engine = create_engine("mysql+pymysql://" + rtxConfig.mysql_feedback_username + ":" + rtxConfig.mysql_feedback_password + "@" + rtxConfig.mysql_feedback_host + "/" + self.databaseName)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    self.connect()

  def connect(self):
    rtxConfig = RTXConfiguration()
    engine = create_engine("mysql+pymysql://" + rtxConfig.mysql_feedback_username + ":" + rtxConfig.mysql_feedback_password + "@" + rtxConfig.mysql_feedback_host + "/" + self.databaseName)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    self.session = session
    self.engine = engine

  def disconnect(self):
    session = self.session
    engine = self.engine
    session.close()
    try:
      engine.dispose()
    except:
      pass

  def update_tracker_entry(self, tracker_id, attributes):
    session = self.session
    tracker_entries = session.query(ARAXQuery).filter(ARAXQuery.query_id==tracker_id).all()
    if len(tracker_entries) > 0:
      tracker_entry = tracker_entries[0]
      end_datetime = datetime.now()
      elapsed = end_datetime - tracker_entry.start_datetime
      tracker_entry.end_datetime = end_datetime
      tracker_entry.elapsed = elapsed.seconds
      tracker_entry.status = attributes['status']
      tracker_entry.message_id = attributes['message_id']
      tracker_entry.message_code = attributes['message_code']
      tracker_entry.code_description = attributes['code_description']
    session.commit()

  def create_tracker_entry(self, attributes):
    session = self.session
    tracker_entry = ARAXQuery(status="started",
        start_datetime=datetime.now(),
        pid=os.getpid(),
        instance_name="test",
        origin=attributes['origin'],
        input_query=attributes['input_query'])
    session.add(tracker_entry)
    session.commit()
    tracker_id = tracker_entry.query_id
    return tracker_id

  def get_entries(self):
    return self.session.query(ARAXQuery).all()

def main():
  query_tracker = ARAXQueryTracker()
  attributes = { 'origin': 'local_dev', 'input_query': { 'query_graph': { 'nodes': [], 'edges': [] } } }
  tracker_id = query_tracker.create_tracker_entry(attributes)
  time.sleep(2)
  attributes = { 'status': 'Completed OK', 'message_id': 3187, 'message_code': 'OK', 'code_description': '32 results' }
  query_tracker.update_tracker_entry(tracker_id, attributes)
  entries = query_tracker.get_entries()
  for entry in entries:
    print(entry.__dict__)

if __name__ == "__main__":
    main()
