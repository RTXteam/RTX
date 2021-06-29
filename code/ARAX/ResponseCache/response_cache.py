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
import requests
import requests_cache
from flask import Flask,redirect

from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime, Text, PickleType, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from sqlalchemy import inspect

from reasoner_validator import validate
from jsonschema.exceptions import ValidationError

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.response import Response as Envelope

trapi_version = '1.1.1'


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
        envelope.id = f"https://{servername}/api/arax/v1.1/response/{stored_response.response_id}"

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
                    json.dump(envelope.to_dict(), outfile, sort_keys=True, indent=2)
            except:
                eprint(f"ERROR: Unable to write response to file {response_path}")

        return stored_response.response_id


    ##################################################################################################
    #### Fetch a cached response
    def get_response(self, response_id):
        session = self.session

        if response_id is None:
            return( { "status": 400, "title": "response_id missing", "detail": "Required attribute response_id is missing from URL", "type": "about:blank" }, 400)

        response_id = str(response_id)

        #### Check to see if this is an integer. If so, it is a local response id
        match = re.match(r'\d+\s*$',response_id)
        if match:
            #### Find the response
            stored_response = session.query(Response).filter(Response.response_id==int(response_id)).first()
            if stored_response is not None:
                response_dir = os.path.dirname(os.path.abspath(__file__)) + '/../../../data/responses_1_0'
                response_filename = f"{stored_response.response_id}.json"
                response_path = f"{response_dir}/{response_filename}"
                try:
                    with open(response_path) as infile:
                        envelope = json.load(infile)
                except:
                    eprint(f"ERROR: Unable to read response from file '{response_path}'")
                    return

                #### Temporary hack for schema problem FIXME
                if 'message' in envelope:
                    if 'knowledge_graph' in envelope['message']:
                        if 'nodes' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['nodes'] is not None:
                            for node_key,node in envelope['message']['knowledge_graph']['nodes'].items():
                                if 'attributes' in node and node['attributes'] is not None:
                                    for attribute in node['attributes']:
                                        if 'value_type_id' in attribute and attribute['value_type_id'] is None:
                                            attribute['value_type_id'] = 'PLACEHOLDER:placeholder'
                        if 'edges' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['edges'] is not None:
                            for edge_key,edge in envelope['message']['knowledge_graph']['edges'].items():
                                if 'attributes' in edge and edge['attributes'] is not None:
                                    for attribute in edge['attributes']:
                                        if 'value_type_id' in attribute and attribute['value_type_id'] is None:
                                            attribute['value_type_id'] = 'PLACEHOLDER:placeholder'


                #### Perform a validation on it
                try:
                    validate(envelope,'Response',trapi_version)
                    if 'description' not in envelope or envelope['description'] is None:
                        envelope['description'] = 'reasoner-validator: PASS'

                except ValidationError as error:
                    timestamp = str(datetime.now().isoformat())
                    if 'logs' not in envelope or envelope['logs'] is None:
                        envelope['logs'] = []
                    envelope['logs'].append( { "code": 'InvalidTRAPI', "level": "ERROR", "message": "TRAPI validator reported an error: " + str(error),
                        "timestamp": timestamp } )
                    if 'description' not in envelope or envelope['description'] is None:
                        envelope['description'] = ''
                    envelope['description'] = 'ERROR: TRAPI validator reported an error: ' + str(error) + ' --- ' + envelope['description']
                return envelope

            else:
                return( { "status": 404, "title": "Response not found", "detail": "There is no response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)

        #### Otherwise, see if it is an ARS style response_id
        if len(response_id) > 30:
            ars_hosts = [ 'ars.ci.transltr.io', 'ars-dev.transltr.io', 'ars.transltr.io' ]
            for ars_host in ars_hosts:
                with requests_cache.disabled():
                    response_content = requests.get(f"https://{ars_host}/ars/api/messages/"+response_id, headers={'accept': 'application/json'})
                status_code = response_content.status_code
                if status_code == 200:
                    break

            if status_code != 200:
                return( { "status": 404, "title": "Response not found", "detail": "Cannot fetch from ARS a response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)

            content_size = len(response_content.content)
            if content_size < 1000:
                content_size = '{:.2f} kB'.format(content_size/1000)
            elif content_size < 1000000:
                content_size = '{:.0f} kB'.format(content_size/1000)
            elif content_size < 10000000000:
                content_size = '{:.1f} MB'.format(content_size/1000000)
            else:
                content_size = '{:.0f} MB'.format(content_size/1000000)

            #### Unpack the response content into a dict
            try:
                response_dict = response_content.json()
            except:
                return( { "status": 404, "title": "Error decoding Response", "detail": "Cannot decode ARS response_id="+str(response_id)+" to a Translator Response", "type": "about:blank" }, 404)

            if 'fields' in response_dict and 'actor' in response_dict['fields'] and str(response_dict['fields']['actor']) == '9':
                with requests_cache.disabled():
                    response_content = requests.get(f"https://{ars_host}/ars/api/messages/" + response_id + '?trace=y', headers={'accept': 'application/json'})
                status_code = response_content.status_code

                if status_code != 200:
                    return( { "status": 404, "title": "Response not found", "detail": "Failed attempting to fetch trace=y from ARS with response_id="+str(response_id), "type": "about:blank" }, 404)

                #### Unpack the response content into a dict and dump
                try:
                    response_dict = response_content.json()
                except:
                    return( { "status": 404, "title": "Error decoding Response", "detail": "Cannot decode ARS response_id="+str(response_id)+" to a Translator Response", "type": "about:blank" }, 404)

                return response_dict

            if 'fields' in response_dict and 'data' in response_dict['fields']:
                envelope = response_dict['fields']['data']
                if envelope is None:
                    envelope = {}
                    return envelope

                #### Actor lookup
                actor_lookup = { 
                    '1': 'Aragorn',
                    '2': 'ARAX',
                    '3': 'BTE',
                    '4': 'NCATS',
                    '5': 'Robokop',
                    '6': 'Unsecret',
                    '7': 'Genetics',
                    '8': 'MolePro',
                    '10': 'Explanatory',
                    '11': 'ImProving',
                    '12': 'Cam',
                    '13': 'TextMining'
                }

                #Remove warning code hack
                #if 'logs' in envelope and envelope['logs'] is not None:
                #    for log in envelope['logs']:
                #        if isinstance(log,dict):
                #            if 'code' in log and log['code'] is None:
                #                log['code'] = '-'
                is_trapi = True
                actual_response = ''
                if 'message' in envelope:
                    #eprint("INFO: envelope has a message")
                    #eprint(json.dumps(envelope,indent=2,sort_keys=True))
                    if 'logs' in envelope and isinstance(envelope['logs'],list) and len(envelope['logs']) > 0:
                        #eprint("INFO: envelope has logs")
                        if isinstance(envelope['logs'][0], str):
                           #eprint("INFO: logs[0] is str")
                           is_trapi = False
                           actual_response = envelope['logs'][0]
                           for i in range(len(envelope['logs'])):
                               if isinstance(envelope['logs'][i],str):
                                   envelope['logs'][i] = { 'level': 'INFO', 'message': 'ARS info: ' + envelope['logs'][i] }
                else:
                    #eprint("INFO: envelope has no message")
                    is_trapi = False

                if not is_trapi:
                    envelope['validation_result'] = { 'status': 'NA', 'version': trapi_version, 'size': content_size, 'message': 'Returned response is not TRAPI: ' + actual_response }
                    return envelope


                #### Perform a validation on it
                try:
                    validate(envelope,'Response',trapi_version)
                    envelope['validation_result'] = { 'status': 'PASS', 'version': trapi_version, 'size': content_size, 'message': '' }

                except ValidationError as error:
                    timestamp = str(datetime.now().isoformat())
                    if 'logs' not in envelope or envelope['logs'] is None:
                        envelope['logs'] = []
                    envelope['logs'].append( { "code": 'InvalidTRAPI', "level": "ERROR", "message": "TRAPI validator reported an error: " + str(error),
                        "timestamp": timestamp } )
                    if 'description' not in envelope or envelope['description'] is None:
                        envelope['description'] = ''
                    envelope['validation_result'] = { 'status': 'FAIL', 'version': trapi_version, 'size': content_size, 'message': 'TRAPI validator reported an error: ' + str(error) + ' --- ' + envelope['description'] }

                #### Try to add the reasoner_id
                if 'actor' in response_dict['fields'] and response_dict['fields']['actor'] is not None:
                    actor = str(response_dict['fields']['actor'])
                    if actor in actor_lookup:
                        if 'message' in envelope and 'results' in envelope['message'] and envelope['message']['results'] is not None:
                            for result in envelope['message']['results']:
                                if 'reasoner_id' in result and result['reasoner_id'] is not None:
                                    pass
                                else:
                                    result['reasoner_id'] = actor_lookup[actor]

                if 'message' in envelope and 'knowledge_graph' in envelope['message'] and envelope['message']['knowledge_graph'] is not None:
                    n_nodes = None
                    if 'nodes' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['nodes'] is not None:
                        n_nodes = len(envelope['message']['knowledge_graph']['nodes'])
                    n_edges = None
                    if 'edges' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['edges'] is not None:
                        n_edges = len(envelope['message']['knowledge_graph']['edges'])
                    envelope['validation_result']['n_nodes'] = n_nodes
                    envelope['validation_result']['n_edges'] = n_edges


                return envelope
            return( { "status": 404, "title": "Cannot find Response (in 'fields' and 'data') in ARS response packet", "detail": "Cannot decode ARS response_id="+str(response_id)+" to a Translator Response", "type": "about:blank" }, 404)


        return( { "status": 404, "title": "UnrecognizedResponse_idFormat", "detail": "Unrecognized response_id format", "type": "about:blank" }, 404)


############################################ Main ############################################################

#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the ResponseCache class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    #argparser.add_argument('list', action='store', help='List all local response ids')
    argparser.add_argument('response_id', type=str, nargs='*', help='Id of a response to fetch and display')
    params = argparser.parse_args()

    #### Create a new ResponseStore object
    response_cache = ResponseCache()

    #### Get the session handle
    session = response_cache.session

    #### Query and print some rows from the reference tables
    #if params.list is True:
    if False:
        print("Listing of all responses")
        for response in session.query(Response).all():
            print(f"response_id={response.response_id}  response_datetime={response.response_datetime}")
        return

    if len(params.response_id) > 0:
        print(f"Content of response_id {params.response_id[0]}:")
        envelope = response_cache.get_response(params.response_id[0])

        #print(json.dumps(ast.literal_eval(repr(envelope)), sort_keys=True, indent=2))
        #print(json.dumps(envelope, sort_keys=True, indent=2))
        print(json.dumps(envelope['logs'], sort_keys=True, indent=2))
        #return

    try:
        validate(envelope['message'],'Message',trapi_version)
        print('- Message is valid')
    except ValidationError as error:
        print(f"- Message INVALID: {error}")

    #return

    for component, klass in { 'query_graph': 'QueryGraph', 'knowledge_graph': 'KnowledgeGraph' }.items():
        if component in envelope['message']:
            try:
                validate(envelope['message'][component], klass, trapi_version)
                print(f"  - {component} is valid")
            except ValidationError:
                print(f"  - {component} INVALID")
        else:
            print(f"  - {component} is not present")

    for node_key, node in envelope['message']['knowledge_graph']['nodes'].items():
        print(f"{node_key}")
        for attribute in node['attributes']:
            attribute['value_type_id'] = None
            try:
                validate(attribute, 'Attribute', trapi_version)
                print(f"  - attribute with {attribute['attribute_type_id']} is valid")
            except ValidationError:
                print(f"  - attribute with {attribute['attribute_type_id']} is  INVALID")


    for result in envelope['message']['results']:
        try:
            validate(result,'Result', trapi_version)
            print(f"    - result is valid")
        except ValidationError:
            print(f"    - result INVALID")

        for key,node_binding_list in result['node_bindings'].items():
            for node_binding in node_binding_list:
                try:
                    validate(node_binding, 'NodeBinding', trapi_version)
                    print(f"      - node_binding {key} is valid")
                except ValidationError:
                    print(f"      - node_binding {key} INVALID")

        for key,edge_binding_list in result['edge_bindings'].items():
            for edge_binding in edge_binding_list:
                #print(json.dumps(edge_binding, sort_keys=True, indent=2))
                try:
                    validate(edge_binding,'EdgeBinding', trapi_version)
                    print(f"      - edge_binding {key} is valid")
                except ValidationError:
                    print(f"      - edge_binding {key} INVALID")





if __name__ == "__main__": main()
