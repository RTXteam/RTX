#!/usr/bin/python3
# Database definition and ResponseCache class

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
import copy
import multiprocessing
from importlib import metadata

import boto3
import timeit
import uuid
import shutil

import sqlalchemy
from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime, Text, PickleType, LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from sqlalchemy import inspect

#sys.path = ['/mnt/data/python/TestValidator'] + sys.path
from reasoner_validator.validator import TRAPIResponseValidator

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../..")
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
from ARAX_attribute_parser import ARAXAttributeParser

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.response import Response as Envelope

trapi_version = '1.5.0'
biolink_version = '4.2.1'

try:
    validator_version = f"{metadata.version('reasoner-validator')}"
except metadata.PackageNotFoundError:
    validator_version = ""

component_cache_dir = os.path.dirname(os.path.abspath(__file__))+"/json_cache"
if os.path.exists(component_cache_dir):
    shutil.rmtree(component_cache_dir)
if not os.path.exists(component_cache_dir):
    os.mkdir(component_cache_dir)


def validate_envelope(process_params):
    validator = process_params['validator']
    envelope = process_params['envelope']
    try:
        validator.check_compliance_of_trapi_response(envelope)
    except:
        eprint(f"ERROR: Validator crashed")
    return(validator)


Base = declarative_base()

#### Define the Response table a class for SQLalchemy
class Response(Base):
    __tablename__ = 'TRAPI_1_0_0_response'
    response_id = Column(Integer, primary_key=True)
    response_datetime = Column(DateTime, nullable=False)
    tool_version = Column(String(50), nullable=False)
    response_code = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    n_results = Column(Integer, nullable=False)


#### Define the ResponseCacheConfigSetting table a class for SQLalchemy
class ResponseCacheConfigSetting(Base):
    __tablename__ = 'ResponseCacheConfigSetting'
    setting_id = Column(Integer, primary_key=True)
    key = Column(String(255), nullable=False)
    value = Column(String(255), nullable=False)
    comment = Column(Text, nullable=False)


#### The main ResponseCache class
class ResponseCache:

    #### Constructor
    def __init__(self):
        self.rtxConfig = RTXConfiguration()
        self.databaseName = "ResponseCache"
        self.engine_type = 'sqlite'
        #if self.rtxConfig.is_production_server or True:              # For testing pretending to be production server
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

        #### If tables do not exist, create them
        database_info = sqlalchemy.inspect(engine)
        if not database_info.has_table(Response.__tablename__):
            eprint(f"WARNING: {self.engine_type} Response table does not exist; creating it")
            Base.metadata.create_all(engine)
        if not database_info.has_table(ResponseCacheConfigSetting.__tablename__):
            eprint(f"WARNING: {self.engine_type} ResponseCacheConfigSetting table does not exist; creating it")
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

        DEBUG = True
        session = self.session
        envelope = response.envelope
        message = envelope.message

        response.debug(f"Writing response record to MySQL")
        try:
            stored_response = Response(response_datetime=datetime.now(),tool_version=self.rtxConfig.version,
                response_code=envelope.status,message=envelope.description,n_results=len(envelope.message.results))
            session.add(stored_response)
            session.flush()
            session.commit()
            response_id = stored_response.response_id
            response_filename = f"/responses/{response_id}.json"
        except:
            response.error(f"Unable to store response record in MySQL", error_code="InternalError")
            response_filename = f"/responses/error.json"
            response_id = 0

        servername = 'localhost'
        if self.rtxConfig.is_production_server:
            servername = 'arax.ncats.io'
        envelope.id = f"https://{servername}/api/arax/v1.4/response/{response_id}"

        #### New system to store the responses in an S3 bucket
        rtx_config = RTXConfiguration()
        KEY_ID = rtx_config.config_secrets['s3']['access']
        ACCESS_KEY = rtx_config.config_secrets['s3']['secret']
        succeeded_to_s3 = False

        #### Get information needed to decide which bucket to write to
        bucket_config = self.get_configs()
        datetime_now = str(datetime.now())
        s3_bucket_migration_datetime = bucket_config.get('S3BucketMigrationDatetime')
        if DEBUG:
            print(f"DEBUG: Datetime now is: {datetime_now}")
            print(f"DEBUG: Cutover date is: {s3_bucket_migration_datetime}")
        buckets = {
            'old': { 'region_name': 'us-west-2', 'bucket_name': 'arax-response-storage' },
            'new': { 'region_name': 'us-east-1', 'bucket_name': 'arax-response-storage-2' }
        }

        if s3_bucket_migration_datetime:  # Only save the response in S3 if we know which bucket to use

            #### Set the bucket info
            if datetime_now > s3_bucket_migration_datetime:
                bucket_tag = 'new'
                if DEBUG:
                    print(f"DEBUG: Since we're after the cutover date, use {bucket_tag} " +
                        f"{buckets[bucket_tag]['region_name']} S3 bucket {buckets[bucket_tag]['bucket_name']}")
            else:
                bucket_tag = 'old'
                if DEBUG:
                    print(f"DEBUG: Since we're before the cutover date, use {bucket_tag} " +
                        f"{buckets[bucket_tag]['region_name']} S3 bucket {buckets[bucket_tag]['bucket_name']}")

            serialized_response = json.dumps(envelope.to_dict(), sort_keys=True, indent=2)

            try:
                region_name = buckets[bucket_tag]['region_name']
                bucket_name = buckets[bucket_tag]['bucket_name']
                eprint(f"INFO: Attempting to write to S3 bucket {region_name}:{bucket_name}:{response_filename}")

                t0 = timeit.default_timer()
                s3 = boto3.resource('s3', region_name=region_name, aws_access_key_id=KEY_ID, aws_secret_access_key=ACCESS_KEY)
                s3.Object(bucket_name, response_filename).put(Body=serialized_response)
                t1 = timeit.default_timer()

                response.info(f"INFO: Successfully wrote {response_filename} to {region_name} S3 bucket {bucket_name} in {t1-t0} seconds")
                succeeded_to_s3 = True

            except:
                response.error(f"Unable to write response {response_filename} to {region_name} S3 bucket {bucket_name}", error_code="InternalError")


            #### if the S3 write failed, store it as a JSON file on the filesystem
            if not succeeded_to_s3:
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
                            json.dump(serialized_response, outfile, sort_keys=True, indent=2)
                    except:
                        eprint(f"ERROR: Unable to write response to file {response_path}")
        else:
            response.warning(f"Not saving response to S3 because I don't know the S3BucketMigrationDatetime")

        return stored_response.response_id


    ##################################################################################################
    #### Fetch a cached response
    def get_response(self, response_id):
        session = self.session

        DEBUG = False

        if response_id is None:
            return( { "status": 400, "title": "response_id missing", "detail": "Required attribute response_id is missing from URL", "type": "about:blank" }, 400)

        response_id = str(response_id)

        #### Check to see if this is an integer. If so, it is a local response id
        match = re.match(r'\d+\s*$',response_id)
        if match:
            #### Find the response
            stored_response = session.query(Response).filter(Response.response_id==int(response_id)).first()
            if stored_response is not None:

                #### See if a very old response is still found locally
                found_response_locally = False
                response_dir = os.path.dirname(os.path.abspath(__file__)) + '/../../../data/responses_1_0'
                response_filename = f"{stored_response.response_id}.json"
                response_path = f"{response_dir}/{response_filename}"
                try:
                    with open(response_path) as infile:
                        envelope = json.load(infile)
                    found_response_locally = True
                    eprint(f"INFO: Wow, found the response locally at '{response_path}'. It must be very old")
                except:
                    pass

                #### If the file wasn't local, try it in S3
                if not found_response_locally:
                    rtx_config = RTXConfiguration()
                    KEY_ID = rtx_config.config_secrets['s3']['access']
                    ACCESS_KEY = rtx_config.config_secrets['s3']['secret']

                    #### Get information needed to decide which bucket to look in
                    bucket_config = self.get_configs()
                    datetime_now = str(datetime.now())
                    if DEBUG:
                        print(f"DEBUG: Datetime now is: {datetime_now}")
                        print(f"DEBUG: Cutover date is: {bucket_config['S3BucketMigrationDatetime']}")
                    buckets = {
                        'old': { 'region_name': 'us-west-2', 'bucket_name': 'arax-response-storage' },
                        'new': { 'region_name': 'us-east-1', 'bucket_name': 'arax-response-storage-2' }
                    }

                    for attempt in  [ 'expected_bucket', 'other_bucket' ]:

                        if attempt == 'expected_bucket':
                            if datetime_now > bucket_config['S3BucketMigrationDatetime']:
                                bucket_tag = 'new'
                                if DEBUG:
                                    print(f"DEBUG: Since we're after the cutover date, use {bucket_tag} " +
                                        f"{buckets[bucket_tag]['region_name']} S3 bucket {buckets[bucket_tag]['bucket_name']}")
                            else:
                                bucket_tag = 'old'
                                if DEBUG:
                                    print(f"DEBUG: Since we're before the cutover date, use {bucket_tag} " +
                                        f"{buckets[bucket_tag]['region_name']} S3 bucket {buckets[bucket_tag]['bucket_name']}")
                        else:
                            print(f"ERROR: Failed in our attempt at using the {bucket_tag} " +
                                    f"{buckets[bucket_tag]['region_name']} S3 bucket {buckets[bucket_tag]['bucket_name']}")
                            if bucket_tag == 'old':
                                bucket_tag = 'new'
                            else:
                                bucket_tag = 'old'
                            print(f"INFO: Instead will try failing over to the {bucket_tag} " +
                                    f"{buckets[bucket_tag]['region_name']} S3 bucket {buckets[bucket_tag]['bucket_name']}")

                        try:
                            region_name = buckets[bucket_tag]['region_name']
                            bucket_name = buckets[bucket_tag]['bucket_name']
                            s3 = boto3.resource('s3', region_name=region_name, aws_access_key_id=KEY_ID, aws_secret_access_key=ACCESS_KEY)

                            response_filename = f"/responses/{response_id}.json"
                            eprint(f"INFO: Attempting to read {region_name}:{bucket_name}:{response_filename} from S3")
                            t0 = timeit.default_timer()

                            content = s3.Object(bucket_name, response_filename).get()["Body"].read()
                            envelope = json.loads(content)
                            t1 = timeit.default_timer()
                            eprint(f"INFO: Successfully read {response_filename} from {region_name} S3 bucket {bucket_name} in {t1-t0} seconds")
                            break

                        except:
                            eprint(f"ERROR: Unable to read {region_name}:{bucket_name}:{response_filename} from S3")
                            if attempt == 'other_bucket':
                                return( { "status": 404, "title": "Response not found", "detail": "There is no response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)


                #### Perform a validation on it
                enable_validation = True
                schema_version = trapi_version
                if enable_validation:
                    #if True:
                    try:

                        #### Perform the validation
                        eprint(f"Validating TRAPI with version {schema_version} and {biolink_version}")
                        validator = TRAPIResponseValidator(trapi_version=schema_version, biolink_version=biolink_version)
                        validator.check_compliance_of_trapi_response(envelope)
                        validation_messages_text = validator.dumps()
                        validation_messages_text = validation_messages_text[:120] + '...truncated'
                        raw_messages: Dict[str, List[Dict[str,str]]] = validator.get_all_messages()
                        messages = raw_messages['Validate TRAPI Response']['Standards Test']
                        #eprint(json.dumps(messages, indent=2, sort_keys=True))

                        envelope['validation_result'] = { 'status': '?', 'version': schema_version, 'message': 'Internal error', 'validation_messages': messages, 'validation_messages_text': validation_messages_text, 'validator_version': validator_version }
                        critical_errors = 0
                        errors = 0
                        if 'critical' in messages and len(messages['critical']) > 0:
                            critical_errors = len(messages['critical'])
                        if 'error' in messages and len(messages['error']) > 0:
                            errors = len(messages['error'])
                        if critical_errors > 0:
                            envelope['validation_result']['status'] = 'FAIL'
                            envelope['validation_result']['message'] = 'There were critical validator errors'
                        elif errors > 0:
                            envelope['validation_result']['status'] = 'ERROR'
                            envelope['validation_result']['message'] = 'There were validator errors'
                        else:
                            envelope['validation_result']['status'] = 'PASS'
                            envelope['validation_result']['message'] = ''

                    #else:
                    except Exception as error:
                        timestamp = str(datetime.now().isoformat())
                        if 'logs' not in envelope or envelope['logs'] is None:
                            envelope['logs'] = []
                        envelope['logs'].append( { "code": 'ValidatorFailed', "level": "ERROR", "message": "TRAPI validator crashed with error: " + str(error),
                            "timestamp": timestamp } )
                        if 'description' not in envelope or envelope['description'] is None:
                            envelope['description'] = ''
                        envelope['validation_result'] = { 'status': 'FAIL', 'version': schema_version, 'message': 'TRAPI validator crashed with error: ' + str(error) + ' --- ' + envelope['description'] }

                else:
                    envelope['validation_result'] = { 'status': 'DISABLED', 'version': schema_version, 'message': 'Validation disabled.', 'validation_messages': { "critical": {}, "error": {}, "warning": {}, "info": { "message": 'Validation has been temporarily disabled due to various problems running it. It may return if the problems can be resolved.' } } }


                #### Count provenance information
                attribute_parser = ARAXAttributeParser(envelope,envelope['message'])
                envelope['validation_result']['provenance_summary'] = attribute_parser.summarize_provenance_info()

                return envelope

            else:
                return( { "status": 404, "title": "Response not found", "detail": "There is no response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)


        #### Otherwise, see if it is a URL
        if response_id.startswith('CQ') or response_id.startswith('$$') or response_id.startswith('http'):
            debug = True
            url = 'xx'

            if response_id.startswith('http'):
                url = response_id.replace('$', '/')

            if response_id.startswith('$$'):
                url = 'https:' + response_id.replace('$', '/')

            if response_id.startswith('CQ'):
                url = f"https://peptideatlas.org/tmp/{response_id}"

            with requests_cache.disabled():
                if debug:
                    eprint(f"Trying {url}...")
                try:
                    response_content = requests.get(url, headers={'accept': 'application/json'})
                except Exception as e:
                    return( { "status": 404, "title": f"Remote URL {url} unavailable", "detail": f"Connection attempts to {url} triggered an exception: {e}", "type": "about:blank" }, 404)
            status_code = response_content.status_code
            if debug:
                eprint(f"--- Fetch of {url} yielded {status_code}")

            if status_code != 200:
                if debug:
                    eprint("Cannot fetch url "+str(url))
                    eprint(str(response_content.content))
                return( { "status": 404, "title": "Response not found", "detail": "Cannot fetch from ARS a response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)

            #if True:
            try:
                envelope = json.loads(response_content.content)
            #else:
            except:
                eprint(f"ERROR: Unable to convert {url} to JSON")
                return( { "status": 404, "title": "Response not found", "detail": "There is no response corresponding to response_id="+str(response_id), "type": "about:blank" }, 404)


            #### Perform a validation on it
            enable_validation = True
            schema_version = trapi_version
            #if 'schema_version' in envelope:
            #    schema_version = envelope['schema_version']
            try:
                if enable_validation:

                    validator = TRAPIResponseValidator(trapi_version=schema_version, biolink_version=biolink_version)
                    validator.check_compliance_of_trapi_response(envelope)
                    raw_messages: Dict[str, List[Dict[str,str]]] = validator.get_all_messages()
                    messages = raw_messages['Validate TRAPI Response']['Standards Test']

                    critical_errors = 0
                    errors = 0
                    if 'critical' in messages and len(messages['critical']) > 0:
                        critical_errors = len(messages['critical'])
                    if 'error' in messages and len(messages['error']) > 0:
                       errors = len(messages['error'])
                    if critical_errors > 0:
                        envelope['validation_result'] = { 'status': 'FAIL', 'version': schema_version, 'message': 'There were critical validator errors', 'validation_messages': messages, 'validation_messages_text': validation_messages_text }
                    elif errors > 0:
                        envelope['validation_result'] = { 'status': 'ERROR', 'version': schema_version, 'message': 'There were validator errors', 'validation_messages': messages, 'validation_messages_text': validation_messages_text }
                    else:
                        envelope['validation_result'] = { 'status': 'PASS', 'version': schema_version, 'message': '', 'validation_messages': messages, 'validation_messages_text': validation_messages_text }

                else:
                    envelope['validation_result'] = { 'status': 'PASS', 'version': schema_version, 'message': 'Validation disabled. too many dependency failures', 'validation_messages': { "errors": [], "warnings": [], "information": [ 'Validation has been temporarily disabled due to problems with dependencies. Will return again soon.' ] } }
            except Exception as error:
                timestamp = str(datetime.now().isoformat())
                if 'logs' not in envelope or envelope['logs'] is None:
                    envelope['logs'] = []
                envelope['logs'].append( { "code": 'ValidatorFailed', "level": "ERROR", "message": "TRAPI validator crashed with error: " + str(error),
                    "timestamp": timestamp } )
                if 'description' not in envelope or envelope['description'] is None:
                    envelope['description'] = ''
                envelope['validation_result'] = { 'status': 'FAIL', 'version': schema_version, 'message': 'TRAPI validator crashed with error: ' + str(error) + ' --- ' + envelope['description'] }

            #### Count provenance information
            attribute_parser = ARAXAttributeParser(envelope,envelope['message'])
            envelope['validation_result']['provenance_summary'] = attribute_parser.summarize_provenance_info()

            return envelope




        #### Otherwise, see if it is an ARS style response_id
        if len(response_id) > 30:
            debug = False

            #### See if this thing is cached already
            filename = f"{component_cache_dir}/{response_id}.json"
            if os.path.exists(filename):
                with open(filename) as infile:
                    envelope = json.load(infile)
                return envelope

            #### If it started with Z, this is a special temporary cache, and if it's not there, all is lost
            if response_id.startswith('Z'):
                return( { "status": 404, "title": f"Cached component not found", "detail": f"The component cache has been cleared since the initial request. Refresh the entire response", "type": "about:blank" }, 404)

            #### If the UUID starts with X, then enable attribute stripping mode and attribute caching, which makes the GUI faster
            attribute_caching = False
            original_response_id = response_id
            if response_id.startswith('X'):
                attribute_caching = True
                response_id = response_id[1:]

            ars_hosts = [ 'ars-prod.transltr.io', 'ars.test.transltr.io', 'ars.ci.transltr.io', 'ars-dev.transltr.io' ]
            for ars_host in ars_hosts:
                with requests_cache.disabled():
                    if debug:
                        eprint(f"Trying {ars_host}...")
                    try:
                        response_content = requests.get(f"https://{ars_host}/ars/api/messages/"+response_id, headers={'accept': 'application/json'}, timeout=15)
                    except Exception as e:
                        return( { "status": 404, "title": f"Remote host {ars_host} unavailable", "detail": f"Connection attempts to {ars_host} triggered an exception: {e}", "type": "about:blank" }, 404)
                status_code = response_content.status_code
                if debug:
                    eprint(f"--- Fetch of {response_id} from {ars_host} yielded {status_code}")
                if status_code == 200:
                    if debug:
                        eprint(f"Got 200 from {ars_host}...")
                    break

            if status_code != 200:
                if debug:
                    eprint("Cannot fetch from ARS a response corresponding to response_id="+str(response_id))
                    eprint(str(response_content.content))
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

            #### Debugging
            if debug:
                temp = copy.deepcopy(response_dict)
                temp['fields']['data'] = '...'
                eprint(json.dumps(temp,indent=2,sort_keys=True))

            is_parent_pk = False
            if 'fields' in response_dict:
                if 'name' in response_dict['fields'] and response_dict['fields']['name'] != '':
                    if response_dict['fields']['name'] == 'ars-default-agent' or response_dict['fields']['name'] == 'ars-workflow-agent':
                        is_parent_pk = True
                    else:
                        is_parent_pk = False
                elif 'actor' in response_dict['fields'] and ( str(response_dict['fields']['actor']) == '9' or str(response_dict['fields']['actor']) == '19' ):
                    is_parent_pk = True
            if is_parent_pk == True:
                with requests_cache.disabled():
                    if debug:
                        eprint(f"INFO: This is a parent UUID. Fetching trace=y for {response_id}")
                    response_content = requests.get(f"https://{ars_host}/ars/api/messages/" + response_id + '?trace=y', headers={'accept': 'application/json'})
                status_code = response_content.status_code

                if status_code != 200:
                    return( { "status": 404, "title": "Response not found", "detail": "Failed attempting to fetch trace=y from ARS with response_id="+str(response_id), "type": "about:blank" }, 404)

                #### Unpack the response content into a dict and dump
                try:
                    response_dict = response_content.json()
                except:
                    return( { "status": 404, "title": "Error decoding Response", "detail": "Cannot decode ARS response_id="+str(response_id)+" to a Translator Response", "type": "about:blank" }, 404)

                response_dict['ars_host'] = ars_host
                response_dict['ui_host'] = ars_host.replace('ars','ui').replace('-prod','')

                return response_dict

            if not is_parent_pk and 'fields' in response_dict and 'data' in response_dict['fields']:
                envelope = response_dict['fields']['data']
                if debug:
                    eprint(f"INFO: This is an ordinary child UUID. Reading and validating it...")
                if envelope is None:
                    envelope = {}
                    return envelope
                actual_response = str(envelope)
                if not isinstance(envelope,dict):
                    envelope = { 'detail': envelope }

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

                #### Actor lookup by name
                actor_name_lookup = {
                    'ara-aragorn': 'Aragorn',
                    'ara-arax': 'ARAX',
                    'ara-bte': 'BTE',
                    'ara-ncats': 'NCATS',
                    'ara-robokop': 'Robokop',
                    'ara-unsecret': 'Unsecret',
                    'kp-genetics': 'Genetics',
                    'kp-molecular': 'MolePro',
                    'ara-explanatory': 'Explanatory',
                    'ara-improving': 'ImProving',
                    'kp-cam': 'Cam',
                    'kp-chp': 'CHP',
                    'kp-icees': 'ICEES',
                    'kp-openpredict': 'OpenPredict',
                    'kp-textmining': 'TextMining'
                }

                #Remove warning code hack
                #if 'logs' in envelope and envelope['logs'] is not None:
                #    for log in envelope['logs']:
                #        if isinstance(log,dict):
                #            if 'code' in log and log['code'] is None:
                #                log['code'] = '-'
                is_trapi = True
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

                           try:
                               #eprint(f"INFO: Actual response: {actual_response}")
                               import html
                               actual_response = html.unescape(actual_response)
                               #eprint(f"INFO: Actual decoded response: {actual_response}")
                               actual_response_dict = json.loads(actual_response)
                               if 'message' in actual_response_dict:
                                   is_trapi = True
                                   envelope = actual_response_dict
                           except:
                               eprint("WARNING: tried to convert the response to JSON and it did not work")
                               eprint(f"It was: {envelope['logs'][0]}")

                else:
                    #eprint("INFO: envelope has no message")
                    is_trapi = False

                if not is_trapi:
                    envelope['validation_result'] = { 'status': 'NA', 'version': trapi_version, 'size': content_size, 'message': 'Returned response is not TRAPI: ' + actual_response }
                    return envelope


                #### Perform a validation on it
                enable_validation = True
                schema_version = trapi_version
                try:
                    if enable_validation:

                        #### Set up the validator
                        validator = TRAPIResponseValidator(trapi_version=schema_version, biolink_version=biolink_version)

                        eprint(f"Validating response with trapi_version={schema_version}, biolink_version={biolink_version}")
                        validator.check_compliance_of_trapi_response(envelope)

                        raw_messages: Dict[str, List[Dict[str,str]]] = validator.get_all_messages()
                        messages = raw_messages['Validate TRAPI Response']['Standards Test']
                        validation_messages_text = validator.dumps()
                        validation_messages_text = validation_messages_text[:120] + '...truncated'

                        envelope['validation_result'] = { 'status': '?', 'version': schema_version, 'size': content_size, 'message': 'Internal error', 'validation_messages': messages, 'validation_messages_text': validation_messages_text, 'validator_version': validator_version }
                        critical_errors = 0
                        errors = 0
                        if 'critical' in messages and len(messages['critical']) > 0:
                            critical_errors = len(messages['critical'])
                        if 'error' in messages and len(messages['error']) > 0:
                            errors = len(messages['error'])
                        if critical_errors > 0:
                            envelope['validation_result']['status'] = 'FAIL'
                            envelope['validation_result']['message'] = 'There were critical validator errors'
                        elif errors > 0:
                            envelope['validation_result']['status'] = 'ERROR'
                            envelope['validation_result']['message'] = 'There were validator errors'
                        else:
                            envelope['validation_result']['status'] = 'PASS'
                            envelope['validation_result']['message'] = ''

                    else:
                        envelope['validation_result'] = { 'status': 'DISABLED', 'version': schema_version, 'message': 'Validation disabled.', 'validation_messages': { "critical": {}, "error": {}, "warning": {}, "info": { "message": 'Validation has been temporarily disabled due to various problems running it. It may return if the problems can be resolved.' } } }

                except Exception as error:
                    timestamp = str(datetime.now().isoformat())
                    if 'logs' not in envelope or envelope['logs'] is None:
                        envelope['logs'] = []
                    envelope['logs'].append( { "code": 'ValidatorFailed', "level": "ERROR", "message": "TRAPI validator crashed with error: " + str(error),
                        "timestamp": timestamp } )
                    if 'description' not in envelope or envelope['description'] is None:
                        envelope['description'] = ''
                    envelope['validation_result'] = { 'status': 'FAIL', 'version': schema_version, 'size': content_size, 'message': 'TRAPI validator crashed with error: ' + str(error) + ' --- ' + envelope['description'] }

                #### Try to add the resource_id
                if 'name' in response_dict['fields'] and response_dict['fields']['name'] is not None:
                    #eprint(json.dumps(response_dict,indent=2,sort_keys=True))
                    actor = str(response_dict['fields']['name'])
                    if actor in actor_name_lookup:
                        #eprint(f"INFO: Attempting to inject {actor_name_lookup[actor]} into results")
                        if 'message' in envelope and 'results' in envelope['message'] and envelope['message']['results'] is not None:
                            for result in envelope['message']['results']:
                                if 'resource_id' in result and result['resource_id'] is not None:
                                    pass
                                else:
                                    result['resource_id'] = actor_name_lookup[actor]

                elif 'actor' in response_dict['fields'] and response_dict['fields']['actor'] is not None:
                    #eprint(json.dumps(response_dict,indent=2,sort_keys=True))
                    actor = str(response_dict['fields']['actor'])
                    if actor in actor_lookup:
                        if 'message' in envelope and 'results' in envelope['message'] and envelope['message']['results'] is not None:
                            for result in envelope['message']['results']:
                                if 'resource_id' in result and result['resource_id'] is not None:
                                    pass
                                else:
                                    result['resource_id'] = actor_lookup[actor]

                if 'message' in envelope and 'knowledge_graph' in envelope['message'] and envelope['message']['knowledge_graph'] is not None:
                    n_nodes = None
                    if 'nodes' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['nodes'] is not None:
                        n_nodes = len(envelope['message']['knowledge_graph']['nodes'])
                    n_edges = None
                    if 'edges' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['edges'] is not None:
                        n_edges = len(envelope['message']['knowledge_graph']['edges'])
                    envelope['validation_result']['n_nodes'] = n_nodes
                    envelope['validation_result']['n_edges'] = n_edges

                    #### Count provenance information
                    attribute_parser = ARAXAttributeParser(envelope,envelope['message'])
                    envelope['validation_result']['provenance_summary'] = attribute_parser.summarize_provenance_info()

                    #### Strip highly verbose information
                    if attribute_caching is True and 'nodes' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['nodes'] is not None:
                        for node_key, node in envelope['message']['knowledge_graph']['nodes'].items():
                            component_uuid = 'Z' + str(uuid.uuid4())
                            filename = f"{component_cache_dir}/{component_uuid}.json"
                            with open(filename, 'w') as outfile:
                                json.dump(node, outfile)
                            node['attributes'] = None
                            node['detail_lookup'] = component_uuid
                    eprint(f"attribute_caching={attribute_caching}")
                    if attribute_caching is True and 'edges' in envelope['message']['knowledge_graph'] and envelope['message']['knowledge_graph']['edges'] is not None:
                        for edge_key, edge in envelope['message']['knowledge_graph']['edges'].items():
                            #eprint(f"edge {edge_key}")
                            if 'attributes' in edge and edge['attributes'] is not None:
                                for attribute in edge['attributes']:
                                    if 'attribute_type_id' in attribute and attribute['attribute_type_id'] is not None and attribute['attribute_type_id'] == 'biolink:support_graphs':
                                        edge['has_these_support_graphs'] = attribute['value']
                                        #eprint(f"has_these_support_graphs={attribute['value']}")
                            component_uuid = 'Z' + str(uuid.uuid4())
                            filename = f"{component_cache_dir}/{component_uuid}.json"
                            with open(filename, 'w') as outfile:
                                json.dump(edge, outfile)
                            edge['detail_lookup'] = component_uuid
                            edge['attributes'] = None
                            edge['sources'] = None

                    content_size = len(json.dumps(envelope,indent=2))
                    if content_size < 1000:
                        content_size = '{:.2f} kB'.format(content_size/1000)
                    elif content_size < 1000000:
                        content_size = '{:.0f} kB'.format(content_size/1000)
                    elif content_size < 10000000000:
                        content_size = '{:.1f} MB'.format(content_size/1000000)
                    else:
                        content_size = '{:.0f} MB'.format(content_size/1000000)
                    envelope['validation_result']['size'] = content_size
                    filename = f"{component_cache_dir}/{original_response_id}.json"
                    with open(filename, 'w') as outfile:
                        json.dump(envelope, outfile)





                return envelope
            return( { "status": 404, "title": "Cannot find Response (in 'fields' and 'data') in ARS response packet", "detail": "Cannot decode ARS response_id="+str(response_id)+" to a Translator Response", "type": "about:blank" }, 404)


        return( { "status": 404, "title": "UnrecognizedResponse_idFormat", "detail": "Unrecognized response_id format", "type": "about:blank" }, 404)


    ##################################################################################################
    #### Store a received callback content
    def store_callback(self, body):

        data_dir = os.path.dirname(os.path.abspath(__file__)) + '/../../../data/callbacks'
        if not os.path.exists(data_dir):
            try:
                os.mkdir(data_dir)
            except:
                eprint(f"ERROR: Unable to create dir {data_dir}")
                return

        if os.path.exists(data_dir):
            counter = 1
            filename = f"{data_dir}/{counter:05}.json"
            while os.path.exists(filename):
                counter += 1
                filename = f"{data_dir}/{counter:05}.json"
                if counter > 5000:
                    eprint(f"ERROR: store_callback counter has reach 5000. Time to clean up or there is a runaway")
                    return

            try:
                with open(filename, 'w') as outfile:
                    json.dump(body, outfile, sort_keys=True, indent=2)
                    eprint(f"INFO: Received a response and wrote it to {filename}")
                    return
            except:
                eprint(f"ERROR: Unable to write response to file {filename}")
                return

        else:
            eprint(f"ERROR: Unable to find dir {data_dir}")




    ##################################################################################################
    #### Fetch the configs stored in the MySQL server
    def get_configs(self):
        session = self.session

        query_result = session.query(ResponseCacheConfigSetting).all()

        configs = {}
        for row in query_result:
            #print(row.__dict__)
            configs[row.key] = row.value

        #### Force value for testing code logic on one instance endpoint only:
        #configs['S3BucketMigrationDatetime'] = '2023-10-11 15:00:00'

        return configs


    ##################################################################################################
    #### Set a ResponseCacheConfigSetting on the MySQL server
    def set_config(self, setting_str):

        if setting_str is None or '=' not in setting_str:
            print(f"ERROR: Config setting string must be in format key=value")
            return
        key, value = setting_str.split('=',1)
        key = key.strip()
        value = value.strip()

        configs = self.get_configs()
        session = self.session

        if key in configs:
            eprint(f"INFO: Updating ResponseCacheConfigSetting record to MySQL")
            query_result = session.query(ResponseCacheConfigSetting).filter(ResponseCacheConfigSetting.key==key).all()
            if len(query_result) > 0:
                entry = query_result[0]
                entry.value = value
                entry.comment = f"ResponseCacheConfigSetting updated {datetime.now()}"
                session.flush()
                session.commit()
            else:
                print(f"ERROR: Internal error E808")
            return

        else:
            eprint(f"INFO: Writing new ResponseCacheConfigSetting record to MySQL")
            try:
                comment = f"ResponseCacheConfigSetting added {datetime.now()}"
                stored_setting = ResponseCacheConfigSetting(key=key, value=value, comment=comment)
                session.add(stored_setting)
                session.flush()
                session.commit()
                setting_id = stored_setting.setting_id
                print(f"INFO: Stored. Resulting setting_id={setting_id}")
            except:
                eprint(f"Unable to store response record in MySQL")
                return

        return setting_id


############################################ Main ############################################################

#### If this class is run from the command line, perform a short little test to see if it is working correctly
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the ResponseCache class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('--show_config', action='count', help='Show all the database config settings')
    argparser.add_argument('--set_config', action='store', help='Specify a key and value to insert or update with format key=value')
    argparser.add_argument('--response_id', action='store', help='Id of a response to display')
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

    if params.response_id is not None and len(params.response_id) > 0:
        print(f"Loading response_id {params.response_id}:")
        envelope = response_cache.get_response(params.response_id)
        #print(json.dumps(ast.literal_eval(repr(envelope)), sort_keys=True, indent=2))
        #print(json.dumps(envelope, sort_keys=True, indent=2))
        return

    if params.set_config is not None:
        print(f"Setting ResponseCacheConfigSetting {params.set_config}")
        response_cache.set_config(params.set_config)
        return

    if params.show_config is not None:
        print("ResponseCache config information in ResponseCacheConfigSetting table:")
        configs = response_cache.get_configs()
        print(json.dumps(configs, indent=2, sort_keys=True))
        return

    print("INFO: No CLI options provided. See --help for options.")

if __name__ == "__main__": main()
