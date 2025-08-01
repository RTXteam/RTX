#!/usr/bin/python3

import sys
import os
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)
import time
import re
import signal
import socket
import json
import psutil

from datetime import datetime, timezone
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, PickleType
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DEBUG = False

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.async_query_status_response import AsyncQueryStatusResponse

Base = declarative_base()

class ARAXQuery(Base):
    __tablename__ = 'arax_query'
    query_id = Column(Integer, primary_key=True)
    status = Column(String(255), nullable=False)
    start_datetime = Column(String(25), nullable=False) ## ISO formatted YYYY-MM-DD HH:mm:ss
    end_datetime = Column(String(25), nullable=True) ## ISO formatted YYYY-MM-DD HH:mm:ss
    elapsed = Column(Float, nullable=True) ## seconds
    pid = Column(Integer, nullable=False)
    domain = Column(String(255), nullable=True)
    hostname = Column(String(255), nullable=True)
    instance_name = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    input_query = Column(PickleType, nullable=False) ## blob object
    message_id = Column(Integer, nullable=True)
    message_code = Column(String(255), nullable=True)
    code_description = Column(String(255), nullable=True)
    remote_address = Column(String(50), nullable=False)
    start_timestamp = Column(Integer, nullable=True)

class ARAXOngoingQuery(Base):
    __tablename__ = 'arax_ongoing_query'
    ongoing_query_id = Column(Integer, primary_key=True)
    query_id = Column(Integer, nullable=False)
    status = Column(String(255), nullable=False)
    start_datetime = Column(String(25), nullable=False) ## ISO formatted YYYY-MM-DD HH:mm:ss
    end_datetime = Column(String(25), nullable=True) ## ISO formatted YYYY-MM-DD HH:mm:ss
    elapsed = Column(Float, nullable=True) ## seconds
    pid = Column(Integer, nullable=False)
    domain = Column(String(255), nullable=True)
    hostname = Column(String(255), nullable=True)
    instance_name = Column(String(255), nullable=False)
    origin = Column(String(255), nullable=False)
    input_query = Column(PickleType, nullable=False) ## blob object
    message_id = Column(Integer, nullable=True)
    message_code = Column(String(255), nullable=True)
    code_description = Column(String(255), nullable=True)
    remote_address = Column(String(50), nullable=False)
    start_timestamp = Column(Integer, nullable=True)

class ARAXQueryTracker:

   #### Constructor
    def __init__(self):
        if DEBUG:
            timestamp = str(datetime.now().isoformat())
            eprint(f"{timestamp}: DEBUG: In ARAXQueryTracker init")

        self.rtxConfig = RTXConfiguration()
        self.databaseName = "QueryTracker"
        self.engine_type = 'sqlite'
        self.session = None
        self.engine = None

        if self.rtxConfig.is_production_server or True:
            self.databaseName = "ResponseCache"
            self.engine_type = 'mysql'
        self.connect()

        if DEBUG:
            timestamp = str(datetime.now().isoformat())
            eprint(f"{timestamp}: DEBUG: ARAXQueryTracker initialized")

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
    def create_tables(self):
        eprint("WARNING: Tried to call create_tables, but this is potentially catastrophic. Manual code change required")
        #### Uncomment this if you really want to drop tables, but be super careful!!
        #Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)


    ##################################################################################################
    def create_indexes(self):
        eprint("INFO: Creating indexes on table ARAXQuery")
        start_timestamp_index = sqlalchemy.Index('start_timestamp_idx', ARAXQuery.start_timestamp)
        start_timestamp_index.create(bind=self.engine)


    ##################################################################################################
    #### Create and store a database connection
    def connect(self):
        if DEBUG:
            timestamp = str(datetime.now().isoformat())
            eprint(f"{timestamp}: DEBUG: ARAXQueryTracker initiating DB connection")

        # If the engine_type is mysql then connect to the MySQL database
        if self.engine_type == 'mysql':
            engine = create_engine("mysql+pymysql://" + self.rtxConfig.mysql_feedback_username + ":" +
                self.rtxConfig.mysql_feedback_password + "@" + self.rtxConfig.mysql_feedback_host + "/" + self.databaseName)

        # Else just use SQLite
        else:
            database_path = os.path.dirname(os.path.abspath(__file__)) + '/' + self.databaseName + '.sqlite'
            engine = create_engine("sqlite:///"+database_path)

        #DBSession = sessionmaker(bind=engine)
        #session = DBSession()

        if DEBUG:
            timestamp = str(datetime.now().isoformat())
            eprint(f"{timestamp}: DEBUG: ARAXQueryTracker establishing session")

        session_factory = sessionmaker(bind=engine)
        Session = scoped_session(session_factory)
        session = Session()

        self.session = session
        self.engine = engine

        #### If the tables don't exist, then create the database
        database_info = sqlalchemy.inspect(engine)
        if not database_info.has_table(ARAXQuery.__tablename__) or not database_info.has_table(ARAXOngoingQuery.__tablename__):
            eprint(f"WARNING: {self.engine_type} tables do not exist; creating them")
            Base.metadata.create_all(engine)


    ##################################################################################################
    def disconnect(self):
        if self.session is None:
            return
        try:
            self.session.close()
            self.engine.dispose()
            if DEBUG:
                timestamp = str(datetime.now().isoformat())
                eprint(f"{timestamp}: DEBUG: ARAXQueryTracker disconnecting session")
        except:
            eprint("ERROR: [ARAX_query_tracker.disconnect] Attempt to close and dispose of session failed")


    ##################################################################################################
    #### Delete and create the ResponseStore database. Careful!
    def create_database(self):
        print("Creating database")
        this = dangerous()

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
    def update_tracker_entry(self, tracker_id, attributes):
        if tracker_id is None:
            eprint("ERROR: update_tracker_entry: tracker_id is None")
            return

        session = self.session
        if session is None:
            eprint("ERROR: update_tracker_entry: session is None")
            return

        try:
            tracker_entries = session.query(ARAXQuery).filter(ARAXQuery.query_id==tracker_id).all()
            if len(tracker_entries) > 0:
                tracker_entry = tracker_entries[0]
                end_datetime = datetime.now()
                elapsed = end_datetime - datetime.fromisoformat(tracker_entry.start_datetime)
                tracker_entry.end_datetime = end_datetime.isoformat(' ', 'seconds')
                tracker_entry.elapsed = elapsed.seconds
                tracker_entry.status = attributes['status'][:254]
                tracker_entry.message_id = attributes['message_id']
                tracker_entry.message_code = attributes['message_code'][:254]
                tracker_entry.code_description = attributes['code_description'][:254]
            session.commit()

            if 'status' in attributes and attributes['status'] in [ 'Completed', 'Died', 'Reset' ]:
                try:
                    session.query(ARAXOngoingQuery).filter(ARAXOngoingQuery.query_id==tracker_id).delete()
                    session.commit()
                    eprint(f"INFO: Deleted ARAXOngoingQuery.query_id={tracker_id}")
                except:
                    eprint(f"ERROR: Unable to delete ARAXOngoingQuery.query_id={tracker_id}")
                    session.commit()
        except:
            eprint("ERROR: Unable to update_tracker_entry, probably due to MySQL connection flakiness")


    ##################################################################################################
    #### Alter arbitray values in a tracker entry
    def alter_tracker_entry(self, tracker_id, attributes):
        if tracker_id is None:
            return("ERROR: tracker_id is None")

        session = self.session
        if session is None:
            return("ERROR: session is None")

        return_value = ''

        tracker_entries = session.query(ARAXQuery).filter(ARAXQuery.query_id==tracker_id).all()
        if len(tracker_entries) > 0:
            tracker_entry = tracker_entries[0]
            for key, value in attributes.items():
                setattr(tracker_entry, key, value)
        else:
            return_value += 'ERROR: No tracker_entries  '

        ongoing_tracker_entries = session.query(ARAXOngoingQuery).filter(ARAXOngoingQuery.query_id==tracker_id).all()
        if len(ongoing_tracker_entries) > 0:
            ongoing_tracker_entry = ongoing_tracker_entries[0]
            for key, value in attributes.items():
                setattr(ongoing_tracker_entry, key, value)
        else:
            return_value += 'ERROR: No ongoing_tracker_entries  '

        session.commit()

        if len(return_value) == 0:
            return_value = 'OK'

        return(return_value)


    ##################################################################################################
    def get_instance_info(self):

        location = os.path.dirname(os.path.abspath(__file__))
        instance_name = '??'
        match = re.match(r'/mnt/data/orangeboard/(.+)/RTX/code', location)
        if match:
            instance_name = match.group(1)
        if instance_name == 'production':
            instance_name = 'ARAX'

        try:
            with open(location + '/../../config.domain') as infile:
                for line in infile:
                    domain = line.strip()
        except:
            domain = '??'

        hostname = socket.gethostname()

        info = {
            'instance_name': instance_name,
            'domain': domain,
            'hostname': hostname }
        return info


    ##################################################################################################
    def create_tracker_entry(self, attributes):
        session = self.session
        if session is None:
            return

        if DEBUG:
            timestamp = str(datetime.now().isoformat())
            eprint(f"{timestamp}: DEBUG: In ARAXQueryTracker create_tracker_entry")

        MAX_CONCURRENT_FROM_REMOTE = 10

        instance_info = self.get_instance_info()

        ongoing_queries_by_remote_address = self.check_ongoing_queries()

        start_datetime = datetime.now().isoformat(' ', 'seconds')
        start_timestamp = datetime.now().timestamp()

        remote_address = attributes['remote_address']
        if remote_address in ongoing_queries_by_remote_address and ongoing_queries_by_remote_address[remote_address] > MAX_CONCURRENT_FROM_REMOTE and attributes['submitter'] is not None and attributes['submitter'] != 'infores:arax':
            try:
                tracker_entry = ARAXQuery(
                    status = "Denied",
                    start_datetime = start_datetime,
                    start_timestamp = start_timestamp,
                    pid = os.getpid(),
                    domain = instance_info['domain'],
                    hostname = instance_info['hostname'],
                    instance_name = instance_info['instance_name'],
                    origin = attributes['submitter'],
                    input_query = attributes['input_query'],
                    remote_address = attributes['remote_address'],
                    end_datetime = start_datetime,
                    elapsed = 0,
                    message_id = None,
                    message_code = 'OverLimit',
                    code_description = 'Request has exceeded 4 concurrent query limit. Denied.')
                session.add(tracker_entry)
                session.commit()
                tracker_id = tracker_entry.query_id
            except:
                tracker_id = 1
            return -999

        try:
            if DEBUG:
                timestamp = str(datetime.now().isoformat())
                eprint(f"{timestamp}: DEBUG: In ARAXQueryTracker creating ARAXQuery record")

            tracker_entry = ARAXQuery(
                status="started",
                start_datetime = start_datetime,
                start_timestamp = start_timestamp,
                pid=os.getpid(),
                domain = instance_info['domain'],
                hostname = instance_info['hostname'],
                instance_name = instance_info['instance_name'],
                origin=attributes['submitter'],
                input_query=attributes['input_query'],
                remote_address=attributes['remote_address'])
            session.add(tracker_entry)
            session.commit()
            tracker_id = tracker_entry.query_id
        except:
            tracker_id = 1

        try:
            if DEBUG:
                timestamp = str(datetime.now().isoformat())
                eprint(f"{timestamp}: DEBUG: In ARAXQueryTracker creating ARAXOngoingQuery record")

            ongoing_tracker_entry = ARAXOngoingQuery(
                status="started",
                query_id = tracker_id,
                start_datetime = start_datetime,
                start_timestamp = start_timestamp,
                pid=os.getpid(),
                domain = instance_info['domain'],
                hostname = instance_info['hostname'],
                instance_name = instance_info['instance_name'],
                origin=attributes['submitter'],
                input_query=attributes['input_query'],
                remote_address=attributes['remote_address'])
            session.add(ongoing_tracker_entry)
            session.commit()
            ongoing_tracker_id = tracker_entry.ongoing_query_id
        except:
            ongoing_tracker_id = 1

        return tracker_id


    ##################################################################################################
    def get_entries(self, last_n_hours=24, ongoing_queries=False):
        if self.session is None:
            return

        if ongoing_queries:
            return self.session.query(ARAXOngoingQuery).all()

        else:
            timestamp = datetime.now().timestamp()
            timestamp -= last_n_hours * 60 * 60
            return self.session.query(ARAXQuery).filter(ARAXQuery.start_timestamp > timestamp).all()
            #return self.session.query(ARAXQuery).filter(
            #    text("""TIMESTAMPDIFF(HOUR, STR_TO_DATE(start_datetime, '%Y-%m-%d %T'), NOW()) < :n""")).params(n=last_n_hours).all()


    ##################################################################################################
    def check_ongoing_queries(self):
        '''
        Gets the current list of ongoing queries in the tracking table and assesses if any need
        to be marked as died and computes the final number of active ones.
        '''
        if self.session is None:
            return

        instance_info = self.get_instance_info()

        #### Enclosing in commits seems to reduce the problem of threads being out of sync
        self.session.commit()
        ongoing_queries = self.session.query(ARAXOngoingQuery).filter(
            ARAXOngoingQuery.domain == instance_info['domain'],
            ARAXOngoingQuery.hostname == instance_info['hostname'],
            ARAXOngoingQuery.instance_name == instance_info['instance_name']).all()
        self.session.commit()

        n_ongoing_queries = len(ongoing_queries)
        #eprint(f"INFO: There are currently {n_ongoing_queries} ongoing queries in this instance")

        entries_to_delete = []
        ongoing_queries_by_remote_address = {}

        for ongoing_query in ongoing_queries:
            try:
                pid = ongoing_query.pid
            except:
                eprint("WARNING: ongoing query probably deleted by another thread")
                continue

            if psutil.pid_exists(pid):
                status = 'This PID exists'
                remote_address = ongoing_query.remote_address
                if remote_address not in ongoing_queries_by_remote_address:
                    ongoing_queries_by_remote_address[remote_address] = 0
                ongoing_queries_by_remote_address[remote_address] += 1
            else:
                status = 'This PID no longer exists'
                entries_to_delete.append(ongoing_query.query_id)

        for query_id in entries_to_delete:
            attributes = {
                'status': 'Died',
                'message_id': None,
                'message_code': 'FoundDead',
                'code_description': 'The PID for this query is no longer running. Reason unknown.'
            }
            self.update_tracker_entry(query_id, attributes)

        return ongoing_queries_by_remote_address


    ##################################################################################################
    def clear_ongoing_queries(self):
        '''
        Gets the current list of ongoing queries in the tracking table for this instance
        and clears them all (to be called at initial launch in case there are leftovers)
        '''
        if self.session is None:
            return

        instance_info = self.get_instance_info()

        #### Enclosing in commits seems to reduce the problem of threads being out of sync
        self.session.commit()
        ongoing_queries = self.session.query(ARAXOngoingQuery).filter(
            ARAXOngoingQuery.domain == instance_info['domain'],
            ARAXOngoingQuery.hostname == instance_info['hostname'],
            ARAXOngoingQuery.instance_name == instance_info['instance_name']).all()
        self.session.commit()

        n_ongoing_queries = len(ongoing_queries)

        entries_to_delete = []

        for ongoing_query in ongoing_queries:
            entries_to_delete.append(ongoing_query.query_id)
            eprint(f"  -- query_id {ongoing_query.query_id} found still in table. Clearing.")

        for query_id in entries_to_delete:
            attributes = {
                'status': 'Reset',
                'message_id': None,
                'message_code': 'Reset',
                'code_description': 'This query was found in ongoing query list at application relaunch and reset.'
            }
            self.update_tracker_entry(query_id, attributes)

        return


    ##################################################################################################
    def get_status(self, last_n_hours=24, mode=None, id_=None):
        if self.session is None:
            return
        if last_n_hours is None or last_n_hours == 0:
            last_n_hours = 24

        if id_ is not None:
            return self.get_query_by_id(id_)

        self.check_ongoing_queries()

        ongoing_queries = False
        if mode and mode == 'active':
            ongoing_queries = True

        entries = self.get_entries(last_n_hours=last_n_hours, ongoing_queries=ongoing_queries)
        result = { 'recent_queries': [], 'current_datetime': datetime.now().strftime("%Y-%m-%d %T") }
        if entries is None:
            return result

        for entry in entries:
            elapsed = entry.elapsed
            if elapsed is None or entry.status == 'Running Async':
                now = datetime.now()
                then = datetime.strptime(entry.start_datetime, '%Y-%m-%d %H:%M:%S')
                delta = now - then
                elapsed = int(delta.total_seconds())
                elapsed -= 1
                if elapsed < 0:
                    elapsed = 0
                eprint(f"--- {then} {elapsed}")
            result['recent_queries'].append( {
                'query_id': entry.query_id,
                'pid': entry.pid,
                'start_datetime': entry.start_datetime,
                'domain': entry.domain,
                'hostname': entry.hostname,
                'instance_name': entry.instance_name,
                'state': entry.status,
                'elapsed': elapsed,
                'submitter': entry.origin,
                'response_id': entry.message_id,
                'status': entry.message_code,
                'description': entry.code_description,
                'remote_address': entry.remote_address
            } )

        result['recent_queries'].reverse()
        result['current_datetime'] = datetime.now().strftime("%Y-%m-%d %T")
        return result


    ##################################################################################################
    def terminate_job(self, terminate_pid, authorization):
        if self.session is None:
            return { 'status': 'ERROR', 'description': 'Internal error ETJ500' }
        eprint(f"INFO: Entering terminate_job: pid={terminate_pid}, authorization={authorization}")
        reference_authorization = str(hash( 'Pickles' + str(terminate_pid)))
        if authorization is None or str(authorization) != reference_authorization:
            return { 'status': 'ERROR', 'description': 'Invalid authorization provided' }

        try:
            os.kill(terminate_pid, signal.SIGTERM)
        except:
            eprint(f"ERROR: Attempt to terminate pid={terminate_pid} failed")
            return { 'status': 'ERROR', 'description': f"ERROR: Attempt to terminate pid={terminate_pid} failed" }

        return { 'status': 'OK', 'description': f"Process {terminate_pid} terminated" }


    ##################################################################################################
    def get_query_by_id(self, id_):
        if self.session is None:
            return

        if id_ is None:
            eprint(f"ERROR: query_id = {id}")
            return

        entries = self.session.query(ARAXQuery).filter(ARAXQuery.query_id == id_)
        for entry in entries:
            return entry.input_query

        eprint(f"ERROR: Unable to find query_id {id}")


    ##################################################################################################
    def get_job_status(self, job_id):
        if self.session is None:
            return

        if job_id is None:
            eprint(f"ERROR: [ARAX_query_tracker.get_job_status] job_id is null")
            return

        rows = self.session.query(ARAXQuery).filter(ARAXQuery.query_id == job_id)

        if rows.count() == 0:
            description = f"ERROR: Unable to find a record of job_id {job_id}"
            eprint(description)
            response = AsyncQueryStatusResponse(status='UnknownJobId', description=description, logs=[])
            ## Should return a 404
            return response

        row = rows[0]
        pid = row.pid
        status = row.message_code
        state = row.status
        elapsed = row.elapsed
        response_id = row.message_id

        if state == 'Completed':
            description = f"Job {job_id} ended with state '{state}' in {elapsed} seconds"
            if response_id is None:
                description += " but no response_id is available"
            else:
                description += f" with response_id {response_id}"
        elif state == 'Died':
            description = f"Job {job_id} was found to be dead after {elapsed} seconds. Reason unknown."
        else:
            description = f"Job {job_id} has status '{status}' and state '{state}' with pid {pid}"

        response = AsyncQueryStatusResponse(status=state, description=description, logs=[])
        if response_id is not None:
            response.response_url = f"https://arax.ncats.io/?r={response_id}"

        return response


    ##################################################################################################
    def get_logs(self, mode='tail'):
        if self.session is None:
            return

        instance_name = self.get_instance_name()

        buffer = ''
        log_file = f"/tmp/RTX_OpenAPI_{instance_name}.elog"

        try:
            with open(log_file) as infile:
                for line in infile:
                    buffer += line
                return buffer
        except:
            buffer = f"ERROR: Unable to read log file '{log_file}'"


        eprint(buffer)
        return(buffer + "\n")


    ##################################################################################################
    def clear_unfinished_entries(self):
        if self.session is None:
            self.connect()
        if self.session is None:
            return

        instance_name = self.get_instance_name()

        eprint(f"Clearing unfinished entries for this instances")
        entries = self.session.query(ARAXQuery).filter(ARAXQuery.instance_name == instance_name).filter( (ARAXQuery.elapsed == None) | (ARAXQuery.status == 'Running Async') )
        eprint(f" - found {len(entries)} entries")

        for entry in entries:
            eprint(f" - Clearing {entry.query_id}, {entry.instance_name}, {entry.elapsed}")
            now = datetime.now()
            then = datetime.strptime(entry.start_datetime, '%Y-%m-%d %H:%M:%S')
            delta = now - then
            elapsed = int(delta.total_seconds())
            entry.status = 'Reset'
            entry.message_code = 'Reset'
            entry.code_description = 'Query was terminated by a process restart'
            entry.elapsed = elapsed
        self.session.commit()
        eprint(f" - Clearing finished")


    ##################################################################################################
    def get_instance_name(self):
        location = os.path.abspath(__file__)
        instance_name = 'null'
        match = re.match(r'/mnt/data/orangeboard/(.+)/RTX/code', location)
        if match:
            instance_name = match.group(1)
        return instance_name


##################################################################################################
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='ARAX Query Tracker System')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('--show_ongoing', action='count', help='Show all ongoing queries')
    argparser.add_argument('--show_recent', action='count', help='Show queries initiated in the last hour')
    argparser.add_argument('--reset_job', action='count', help='Reset the specified job_id(s)')
    argparser.add_argument('--job_ids', type=str, help='Job IDs to show (comma separated list)')
    argparser.add_argument('--prune_jobs', action='count', help='Simply prune very stale jobs from the active query table')
    argparser.add_argument('--create_indexes', action='count', help='Create needed indexes on the tables')
    params = argparser.parse_args()

    timestamp = str(datetime.now().isoformat())

    #### Set verbose
    verbose = params.verbose
    if verbose is None: verbose = 1

    query_tracker = ARAXQueryTracker()

    if params.create_indexes:
        query_tracker.create_indexes()
        return

    #### If pruning, then also set the --show_ongoing and --reset_job flags
    if params.prune_jobs:
        params.show_ongoing = True
        params.reset_job = True
    prune_job_ids = []

    #### Check ongoing queries
    entries = None
    if params.show_ongoing:
        timestamp = str(datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: Getting ongoing queries from database")

        entries = query_tracker.get_entries(ongoing_queries=True)

        timestamp = str(datetime.now().isoformat())
        eprint(f"{timestamp}: Currently ongoing queries:")
        if len(entries) == 0:
            eprint(" - No ongoing queries")
            entries = []

    if params.show_recent:
        timestamp = str(datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: Getting recent queries from database")

        entries = query_tracker.get_entries(last_n_hours=1)

        timestamp = str(datetime.now().isoformat())
        eprint(f"{timestamp}: Queries from the last hour:")
        if len(entries) == 0:
            eprint(" - No recent queries")
            entries = []

    if entries is not None:
        for entry in entries:
            #print(entry.__dict__)
            now = datetime.now(timezone.utc)
            now = now.replace(tzinfo=None)
            elapsed = now - datetime.fromisoformat(entry.start_datetime)
            elapsed = elapsed.seconds + elapsed.days * 24 * 60 * 60
            print(f"{entry.query_id}\t{entry.start_datetime}\t{elapsed}\t{entry.instance_name}\t{entry.hostname}\t{entry.status}\t{entry.origin}\t{entry.pid}\t{entry.message_id}\t{entry.message_code}\t{entry.code_description}")
            if params.prune_jobs and elapsed > 10000: 
                prune_job_ids.append(entry.query_id)

    #### Extract job_ids
    job_ids = []
    if params.job_ids:
        job_ids = params.job_ids.split(',')
    job_ids.extend(prune_job_ids)

    #### If the request is to reset jobs, do it
    if ( params.reset_job is not None or params.prune_jobs is not None ) and len(job_ids) > 0:
        for job_id in job_ids:
            attributes = {
                'status': 'Reset',
                'message_id': None,
                'message_code': 'Reset',
                'code_description': 'Query job_id entry was manually reset by admin'
            }
            try:
                query_tracker.update_tracker_entry(job_id, attributes)
                eprint(f"Reset job_id {job_id}")
            except:
                eprint(f"ERROR: Unable to reset job_id {job_id}")
        return

    if params.reset_job is not None or params.prune_jobs is not None or params.show_ongoing is not None:
        return

    if len(job_ids) > 0:
        for job_id in job_ids:
            eprint(f"INFO: Getting status for job {job_id}")
            response = query_tracker.get_job_status(job_id)
            print(response)
        return

    print("Insufficient parameters to know what to do. use --help")
    return

    if False:
        attributes = { 'origin': 'local_dev', 'input_query': { 'query_graph': { 'nodes': [], 'edges': [] } }, 'remote_address': 'test_address' }
        tracker_id = query_tracker.create_tracker_entry(attributes)

        time.sleep(1)
        attributes = { 'status': 'Completed OK', 'message_id': 3187, 'message_code': 'OK', 'code_description': '32 results' }
        query_tracker.update_tracker_entry(tracker_id, attributes)

    entries = query_tracker.get_entries(last_n_hours=24)
    for entry in entries:
        #print(entry.__dict__)
        print(f"{entry.query_id}\t{entry.pid}\t{entry.start_datetime}\t{entry.instance_name}\t{entry.status}\t{entry.elapsed}\t{entry.origin}\t{entry.message_id}\t{entry.message_code}\t{entry.code_description}")


if __name__ == "__main__":
    main()

