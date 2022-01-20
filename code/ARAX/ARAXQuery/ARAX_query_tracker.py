#!/usr/bin/python3

import sys
import os
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)
import time
import re
import signal
import socket

from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, PickleType
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")
from RTXConfiguration import RTXConfiguration

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

class ARAXQueryTracker:

   #### Constructor
    def __init__(self):
        self.rtxConfig = RTXConfiguration()
        self.databaseName = "QueryTracker"
        self.engine_type = 'sqlite'
        self.session = None
        self.engine = None

        if self.rtxConfig.is_production_server:
            self.databaseName = "ResponseCache"
            self.engine_type = 'mysql'
        self.connect()

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
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)


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
        database_info = sqlalchemy.inspect(engine)
        if not database_info.has_table(ARAXQuery.__tablename__):
            eprint(f"WARNING: {self.engine_type} tables do not exist; creating them")
            Base.metadata.create_all(engine)


    ##################################################################################################
    def disconnect(self):
        session = self.session
        engine = self.engine
        session.close()
        try:
            engine.dispose()
        except:
            pass


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
            return
            database_path = os.path.dirname(os.path.abspath(__file__)) + '/' + self.databaseName + '.sqlite'
            engine = create_engine("sqlite:///"+database_path)

        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        self.session = session
        self.engine = engine

        #### If the tables don't exist, then create the database
        database_info = sqlalchemy.inspect(engine)
        if not database_info.has_table(ARAXQuery.__tablename__):
            eprint(f"WARNING: {self.engine_type} tables do not exist; creating them")
            Base.metadata.create_all(engine)


    ##################################################################################################
    #### Create and store a database connection
    def disconnect(self):
        session = self.session
        engine = self.engine
        if session is None:
            return
        try:
            session.close()
            engine.dispose()
        except:
            pass


    ##################################################################################################
    def update_tracker_entry(self, tracker_id, attributes):
        if tracker_id is None:
            return

        session = self.session
        if session is None:
            return

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


    ##################################################################################################
    def alter_tracker_entry(self, tracker_id, attributes):
        if tracker_id is None:
            return

        session = self.session
        if session is None:
            return

        tracker_entries = session.query(ARAXQuery).filter(ARAXQuery.query_id==tracker_id).all()
        if len(tracker_entries) > 0:
            tracker_entry = tracker_entries[0]
            for key, value in attributes.items():
                setattr(tracker_entry, key, value)
        session.commit()


    ##################################################################################################
    def create_tracker_entry(self, attributes):
        session = self.session
        if session is None:
            return

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

        try:
            tracker_entry = ARAXQuery(status="started",
                start_datetime=datetime.now().isoformat(' ', 'seconds'),
                pid=os.getpid(),
                domain = domain,
                hostname = hostname,
                instance_name = instance_name,
                origin=attributes['submitter'],
                input_query=attributes['input_query'],
                remote_address=attributes['remote_address'])
            session.add(tracker_entry)
            session.commit()
            tracker_id = tracker_entry.query_id
        except:
            tracker_id = 1
        return tracker_id

    ##################################################################################################
    def get_entries(self, last_n_hours=24, incomplete_only=False):
        if self.session is None:
            return

        if incomplete_only:
            return self.session.query(ARAXQuery).filter(
                text("""status NOT LIKE '%Completed%' 
                        AND TIMESTAMPDIFF(HOUR, STR_TO_DATE(start_datetime, '%Y-%m-%d %T'), NOW()) < :n""")).params(n=last_n_hours).all()
        else:
            if self.engine_type == "mysql":
                return self.session.query(ARAXQuery).filter(
                    text("""TIMESTAMPDIFF(HOUR, STR_TO_DATE(start_datetime, '%Y-%m-%d %T'), NOW()) < :n""")).params(n=last_n_hours).all()
            else:
                return self.session.query(ARAXQuery).filter(
                text("""JULIANDAY(start_datetime) - JULIANDAY(datetime('now','localtime')) < :n""")).params(n=last_n_hours/24).all()


    ##################################################################################################
    def get_status(self, last_n_hours=24, incomplete_only=False, id_=None):
        if self.session is None:
            return
        if last_n_hours is None or last_n_hours == 0:
            last_n_hours = 24

        if id_ is not None:
            return self.get_query_by_id(id_)

        entries = self.get_entries(last_n_hours=last_n_hours, incomplete_only=incomplete_only)
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


    ####### ###########################################################################################
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


    ####### ###########################################################################################
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

        entries = self.session.query(ARAXQuery).filter(ARAXQuery.instance_name == instance_name).filter( (ARAXQuery.elapsed == None) | (ARAXQuery.status == 'Running Async') )

        for entry in entries:
            eprint(f" - {entry.query_id}, {entry.instance_name}, {entry.elapsed}")
            now = datetime.now()
            then = datetime.strptime(entry.start_datetime, '%Y-%m-%d %H:%M:%S')
            delta = now - then
            elapsed = int(delta.total_seconds())
            entry.status = 'Reset'
            entry.message_code = 'Reset'
            entry.code_description = 'Query was terminated by a process restart'
            entry.elapsed = elapsed
        self.session.commit()


    ##################################################################################################
    def get_instance_name(self):
        location = os.path.abspath(__file__)
        instance_name = 'null'
        match = re.match(r'/mnt/data/orangeboard/(.+)/RTX/code', location)
        if match:
            instance_name = match.group(1)
        return instance_name


def main():

    query_tracker = ARAXQueryTracker()

    query_tracker.clear_unfinished_entries()
    return

    #query_tracker.create_database()

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
