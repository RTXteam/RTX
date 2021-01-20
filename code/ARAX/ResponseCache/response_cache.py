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

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.response import Response



Base = declarative_base()

#### Define the database tables as classes
class Response(Base):
    __tablename__ = 'TRAPI_1_0_0_response'
    response_id = Column(Integer, primary_key=True)
    response_datetime = Column(DateTime, nullable=False)
    tool_version = Column(String(50), nullable=False)
    response_code = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    n_results = Column(Integer, nullable=False)


#### The main ResponseCache class
class ResponseCache:

    #### Constructor
    def __init__(self):
        self.rtxConfig = RTXConfiguration()
        self.databaseName = "ResponseCache"
        self.engine_type = 'sqlite'
        if self.rtxConfig.is_production_server:
            self.engine_type = 'mysql'
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


    ##################################################################################################
    #### Delete and create the ResponseStore database. Careful!
    def create_database(self):
        print("Creating database")

        # If the engine_type is mysql then set up the MySQL database
        if self.engine_type == 'mysql':
            engine = create_engine("mysql+pymysql://" + self.rtxConfig.mysql_feedback_username + ":" +
                self.rtxConfig.mysql_feedback_password + "@" + self.rtxConfig.mysql_feedback_host + "/" + self.databaseName)

        # Else just use SQLite
        else:
            database_path = os.path.dirname(os.path.abspath(__file__)) + '/' + self.databaseName + '.sqlite'
            if os.path.exists(database_path):
                os.remove(database_path)
            engine = create_engine("sqlite:///"+database_path)

        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.connect()


    ##################################################################################################
    #### Create and store a database connection
    def connect(self):

        # If the engine_type is mysql then connect to the MySQL database
        if self.engine_type == 'mysql':
            engine = create_engine("mysql+pymysql://" + self.rtxConfig.mysql_feedback_username + ":" +
                self.rtxConfig.mysql_feedback_password + "@" + self.rtxConfig.mysql_feedback_host + "/" + self.databaseName)

        # Else just use SQLite
        else:
            database_path = os.path.dirname(os.path.abspath(__file__)) + '/' + self.databaseName + '.sqlite'
            engine = create_engine("sqlite:///"+database_path)

        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        self.session = session
        self.engine = engine

        #### If the tables don't exist, then create the database
        if not engine.dialect.has_table(engine, Response.__tablename__):
            print(f"WARNING: {self.engine_type} tables do not exist; creating them")
            Base.metadata.create_all(engine)


    ##################################################################################################
    #### Create and store a database connection
    def disconnect(self):
        session = self.session
        engine = self.engine
        session.close()
        try:
            engine.dispose()
        except:
            pass


    ##################################################################################################
    #### Pre-populate the database with reference data (none now)
    def prepopulate_database(self):
        session = self.session
        return


    ##################################################################################################
    #### Store a new response into the database
    def add_new_response(self,response):

        session = self.session
        envelope = response.envelope
        message = envelope.message

        stored_response = Response(response_datetime=datetime.now(),tool_version=self.rtxConfig.version,
            response_code=envelope.status,message=envelope.description,n_results=len(envelope.message.results))
        session.add(stored_response)
        session.flush()
        session.commit()

        servername = 'localhost'
        if self.rtxConfig.is_production_server:
            servername = 'arax.ncats.io'
        envelope.id = f"https://{servername}/api/arax/v1.0/response/{stored_response.response_id}"

        #### Instead of storing the large response object in the MySQL database as a blob
        #### now store it as a JSON file on the filesystem
        response_dir = os.path.dirname(os.path.abspath(__file__)) + '/../../../data/responses_1_0'
        if not os.path.exists(response_dir):
            try:
                os.mkdir(response_dir)
            except:
                eprint(f"ERROR: Unable to create dir {response_dir}")

        if os.path.exists(response_dir):
            response_filename = f"{stored_response.response_id}.json"
            response_path = f"{response_dir}/{response_filename}"
            try:
                with open(response_path, 'w') as outfile:
                    json.dump(envelope.to_dict(), outfile, sort_keys=True)
            except:
                eprint(f"ERROR: Unable to write response to file {response_path}")

        return stored_response.response_id


    ##################################################################################################
    #### Fetch a cached response
    def get_response(self, response_id):
        session = self.session

        if response_id is None:
            return( { "status": 400, "title": "response_id missing", "detail": "Required attribute response_id is missing from URL", "type": "about:blank" }, 400)

        #### Find the response
        stored_response = session.query(Response).filter(Response.response_id==response_id).first()
        if stored_response is not None:
            response_dir = os.path.dirname(os.path.abspath(__file__)) + '/../../../data/responses_1_0'
            response_filename = f"{stored_response.response_id}.json"
            response_path = f"{response_dir}/{response_filename}"
            try:
                with open(response_path) as infile:
                    return json.load(infile)
            except:
                eprint(f"ERROR: Unable to read response from file '{response_path}'")

        else:
            return( { "status": 404, "title": "Response not found", "detail": "There is no response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)



############################################ Main ############################################################

#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the ResponseCache class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('response_id', type=int, nargs='*', help='Integer number of a response to read and display')
    params = argparser.parse_args()

    #### Create a new ResponseStore object
    response_cache = ResponseCache()

    #### Get the session handle
    session = response_cache.session

    #### Query and print some rows from the reference tables
    if len(params.response_id) == 0:
        print("Listing of all responses")
        for response in session.query(Response).all():
            print(f"response_id={response.response_id}  response_datetime={response.response_datetime}")

    else:
        print(f"Content of response_id {params.response_id[0]}:")
        envelope = response_cache.get_response(params.response_id[0])
        print(json.dumps(ast.literal_eval(repr(envelope)), sort_keys=True, indent=2))


if __name__ == "__main__": main()
