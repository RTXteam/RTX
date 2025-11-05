#!/usr/bin/env python3

"""
KPQueryCacher: A Python class to cache KP TRAPI queries using
SQLAlchemy, SQLite, and a compressed file store.
"""

import sys
import os
import gzip
import pickle
import json
import hashlib
import time
import shutil
from datetime import datetime
from contextlib import contextmanager
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

# External dependencies
import aiohttp
import asyncio
import requests
from sqlalchemy import create_engine, Column, Integer, String, Float, PickleType
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm.session import Session

# Constants
REFRESH_TIME_LIMIT_SECONDS = 60.0
AGE_BEFORE_REFRESH_HOURS = 0.3
NO_CACHED_RESPONSE = -2
CONNECTION_ERROR = -1


# --- SQLAlchemy Model Definition ---

# Define the declarative base
Base = declarative_base()

class KPQuery(Base):
    """
    SQLAlchemy model for a cached Knowledge Provider (KP) query.
    
    This table stores metadata about a query, the query object itself,
    and statistics about its retrieval and refreshing.
    """
    __tablename__ = 'kp_query'
    
    kp_query_id = Column(Integer, primary_key=True)
    status = Column(String(255), nullable=False, index=True)
    kp_curie = Column(String(255), nullable=False, index=True)
    query_url = Column(String(255), nullable=False)
    query_hash = Column(String(255), nullable=False, unique=True, index=True)
    query_object = Column(PickleType, nullable=False)
    first_request_datetime = Column(String(25), nullable=False)
    last_request_datetime = Column(String(25), nullable=False)
    first_query_elapsed = Column(Float, nullable=False)
    first_query_http_code = Column(Integer, nullable=False)
    first_query_n_results = Column(Integer, nullable=True)
    n_requests = Column(Integer, nullable=False, default=1)
    
    # Refresh statistics
    last_attempted_refresh_datetime = Column(String(25), nullable=True)
    last_successful_refresh_datetime = Column(String(25), nullable=True)
    n_successful_refreshes = Column(Integer, nullable=True, default=0)
    n_failed_refreshes = Column(Integer, nullable=True, default=0)
    last_refresh_elapsed = Column(Float, nullable=True)
    last_refresh_http_code = Column(Integer, nullable=True)
    last_refresh_n_results = Column(Integer, nullable=True)
    n_refresh_same_results = Column(Integer, nullable=True, default=0)
    n_refresh_different_results = Column(Integer, nullable=True, default=0)

    def __repr__(self):
        return f"<KPQuery(hash='{self.query_hash}', url='{self.query_url}', status='{self.status}')>"
    
    def to_dict(self):
        """Serializes the object to a dictionary, redacting the pickled object."""
        d = {}
        for column in self.__table__.columns:
            col_name = column.name
            if col_name == 'query_object':
                d[col_name] = "<Pickled Object (Use hash to retrieve)>"
            else:
                d[col_name] = getattr(self, col_name)
        return d



# --- KPQueryCacher Class ---

class KPQueryCacher:
    """
    Manages caching of web queries to a SQLite database and compressed files.
    """

    def __init__(self):
        """
        Initializes the cacher.
        """
        self.db_file_path = os.path.dirname(os.path.abspath(__file__))+"/trapi_query_cacher_database.sqlite"
        self.cache_dir = os.path.dirname(os.path.abspath(__file__))+"/trapi_query_cacher_responses"
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Set up SQLAlchemy engine and session
        self.engine = create_engine(f'sqlite:///{self.db_file_path}')
        self.Session = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        print(f"Cacher initialized. database: '{self.db_file_path}'\n                    cachedir: '{self.cache_dir}'")



    def initialize_cache(self):
        """
        Wipes and re-initializes the database and cache directory.
        All records and all cached files will be deleted.
        """
        print("Initializing cache: Wiping DB and cache directory...")
        with self._get_session() as session:
            # Clear the table
            session.query(KPQuery).delete()
        
        # Drop and recreate tables to reset any auto-increments
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
            
        # Clear the cache directory
        for f_name in os.listdir(self.cache_dir):
            f_path = os.path.join(self.cache_dir, f_name)
            try:
                if os.path.isfile(f_path) or os.path.islink(f_path):
                    os.unlink(f_path)
            except Exception as e:
                print(f"Failed to delete {f_path}. Reason: {e}")
        print("Cache initialization complete.")



    @contextmanager
    def _get_session(self) -> Session:
        """
        Provides a transactional scope around a series of operations.
        Commits on success, rolls back on error.
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            print("Session rolled back due to error.")
            raise
        finally:
            session.close()



    def _hash_query(self, query_object: dict) -> str:
        """
        Creates a stable SHA-256 hash of a query object.
        
        :param query_object: The dictionary to hash.
        :return: A hex digest string.
        """
        query_json = json.dumps(query_object, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(query_json.encode('utf-8')).hexdigest()



    def _get_cache_filepath(self, query_hash: str) -> str:
        """
        Gets the standardized file path for a given query hash.
        
        :param query_hash: The hash of the query.
        :return: The full file path for the compressed response.
        """
        return os.path.join(self.cache_dir, f"{query_hash}.pkl.gz")



    def _read_cache_file(self, filepath: str) -> any:
        """Reads and de-pickles a compressed cache file."""
        with gzip.open(filepath, 'rb') as f:
            return pickle.load(f)



    def _write_cache_file(self, filepath: str, data: any):
        """Pickles and writes data to a compressed cache file."""
        eprint(f"Writing caching file {filepath}")
        with gzip.open(filepath, 'wb') as f:
            pickle.dump(data, f)
        eprint(f"Done writing caching file {filepath}")



    def _get_n_results(self, response_object: any) -> int:
        """
        Heuristically determines the number of results from a response object.
        
        :param response_object: The JSON response from the web service.
        :return: An integer count of results, or None.
        """
        try:
            if isinstance(response_object, dict):
                if 'results' in response_object and isinstance(response_object['results'], list):
                    return len(response_object['results'])
                if 'message' in response_object and isinstance(response_object['message'], dict):
                    msg = response_object['message']
                    if 'results' in msg and isinstance(msg['results'], list):
                        return len(msg['results'])
            elif isinstance(response_object, list):
                return len(response_object)
        except Exception:
            # Fail silently and return None if structure is unexpected
            pass
        return None



    async def get_result(self, query_url: str, query_object: dict, kp_curie: str, timeout=30, async_session=None) -> tuple:
        """
        Looks for a cached result based on the query object.
        If found, updates access stats and returns the decompressed response.
        if not found, then perform the remote query and store the result in the cache

        :param query_object: The query object to hash and look up.
        :return: A tuple of (response_data, http_status_code, elapsed_time, error_message)
            http_status_code -1 means the cached result is a timeout
            http_status_code -2 means there is not cached result available
        """

        #### Try to get the response from the cache
        #eprint(f"*** Checking cache for query with {kp_curie} to {query_url}")
        response_data, http_code, elapsed_time, error = self.get_cached_result(query_url, query_object)
        if http_code != NO_CACHED_RESPONSE: 
            #eprint("*** Found cached result")
            return response_data, http_code, elapsed_time, 'from cache'

        #### Else send it to the service
        #eprint(f"*** Fetch data directly from KP {query_url} using payload {query_object}, timeout={timeout}")
        response_data, http_code, elapsed_time, error = await self.async_post_query_to_web_service(query_url, query_object, timeout=timeout, async_session=async_session)
        n_results = self._get_n_results(response_data)
        #eprint(f"*** Fetched a response with http_code={http_code}, n_results={n_results} from the cache in {elapsed_time:.3f} seconds with error={error}")

        #### And store that result in the cache
        #eprint("*** Store the response in the cache")
        self.store_response(
            kp_curie=kp_curie,
            query_url=query_url,
            query_object=query_object,
            response_object=response_data,
            http_code=http_code,
            elapsed_time=elapsed_time,
            status="OK"
        )

        return response_data, http_code, elapsed_time, error



    def get_cached_result(self, query_url: str, query_object: dict) -> tuple:
        """
        Looks for a cached result based on the query object.
        If found, updates access stats and returns the decompressed response.

        :param query_object: The query object to hash and look up.
        :return: A tuple of (response_data, http_status_code, elapsed_time, error_message)
            http_status_code -1 means the cached result is a timeout
            http_status_code -2 means there is not cached result available
        """

        start_time = time.time()
        query_hash = self._hash_query(query_url + str(query_object))
        
        with self._get_session() as session:
            record = session.query(KPQuery).filter_by(query_url=query_url, query_hash=query_hash).first()
            
            if not record:
                return None, NO_CACHED_RESPONSE, time.time() - start_time, None
                
            # Found a record, update stats
            record.n_requests += 1
            record.last_request_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            session.commit()

            # Now try to read the file
            filepath = self._get_cache_filepath(query_hash)
            try:
                response_data = self._read_cache_file(filepath)
                return response_data, record.last_refresh_http_code or record.first_query_http_code, time.time() - start_time, None

            except FileNotFoundError as e:
                # Cache inconsistency: DB record exists, but file is missing.
                # Delete the bad record and return None.
                print(f"Cache inconsistency detected. Deleting record for hash: {query_hash}")
                session.delete(record)
                return None, NO_CACHED_RESPONSE, time.time() - start_time, e

            except Exception as e:
                # Other read error
                print(f"Error reading cache file {filepath}: {e}")
                return None, NO_CACHED_RESPONSE, time.time() - start_time, e



    def post_query_to_web_service(self, query_url: str, query_object: dict, timeout: int = 30, async_session=None) -> tuple:
        """
        Posts the query to the remote KP.

        :param query_object: The query (request body) to send.
        :param query_url: The URL of the web service.
        :param timeout: Request timeout in seconds.
        :return: A tuple of (response_data, http_status_code, elapsed_time, error_message)
        """
        start_time = time.time()
        try:
            response = requests.post(query_url, json=query_object, timeout=timeout, headers={'accept': 'application/json'})
            elapsed = time.time() - start_time
            # Raise an exception for bad status codes (4xx, 5xx)
            response.raise_for_status() 
            return response.json(), response.status_code, elapsed, None
            
        except requests.exceptions.HTTPError as e:
            # Got a 4xx or 5xx response
            elapsed = time.time() - start_time
            return None, e.response.status_code, elapsed, str(e)

        except requests.exceptions.RequestException as e:
            # Connection error, timeout, DNS error, etc.
            elapsed = time.time() - start_time
            return None, CONNECTION_ERROR, elapsed, str(e) # -1 for non-HTTP errors



    async def async_post_query_to_web_service(self, query_url: str, query_object: dict, timeout: int = 30, async_session=None) -> tuple:
        """
        Posts the query to the remote KP.

        :param query_object: The query (request body) to send.
        :param query_url: The URL of the web service.
        :param timeout: Request timeout in seconds.
        :return: A tuple of (response_data, http_status_code, elapsed_time, error_message)
        """
        start_time = time.time()
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            try:
                async with session.post(query_url, json=query_object, timeout=timeout, headers={'accept': 'application/json'}) as response:
                    elapsed = time.time() - start_time
                    # Raise an exception for bad status codes (4xx, 5xx)
                    response.raise_for_status() 
                    json_response = await response.json()
                    return json_response, response.status, elapsed, None

            except requests.exceptions.HTTPError as e:
                # Got a 4xx or 5xx response
                elapsed = time.time() - start_time
                return None, e.response.status_code, elapsed, str(e)

            except requests.exceptions.RequestException as e:
                # Connection error, timeout, DNS error, etc.
                elapsed = time.time() - start_time
                return None, CONNECTION_ERROR, elapsed, str(e) # -1 for non-HTTP errors



    def store_response(self, 
                       kp_curie: str, 
                       query_url: str, 
                       query_object: dict, 
                       response_object: any, 
                       http_code: int, 
                       elapsed_time: float,
                       status: str = "OK"):
        """
        Stores a new web service response in the DB and file cache.

        :param kp_curie: CURIE of the Knowledge Provider.
        :param query_url: The URL that was queried.
        :param query_object: The query object that was sent.
        :param response_object: The response object that was received.
        :param http_code: The HTTP status code from the query.
        :param elapsed_time: The time the query took.
        :param status: The initial status string (e.g., "OK" or "FAILED").
        """
        query_hash = self._hash_query(query_url + str(query_object))
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        n_results = self._get_n_results(response_object)
        
        # 1. Write the compressed response file
        filepath = self._get_cache_filepath(query_hash)
        try:
            self._write_cache_file(filepath, response_object)
        except Exception as e:
            eprint(f"Failed to write cache file {filepath}: {e}")
            return # Don't create a DB record if file write fails

        # 2. Create the new database record
        new_record = KPQuery(
            status=status,
            kp_curie=kp_curie,
            query_url=query_url,
            query_hash=query_hash,
            query_object=query_object,
            first_request_datetime=now_str,
            last_request_datetime=now_str,
            first_query_elapsed=elapsed_time,
            first_query_http_code=http_code,
            first_query_n_results=n_results,
            n_requests=1,
            n_successful_refreshes=0,
            n_failed_refreshes=0,
            n_refresh_same_results=0,
            n_refresh_different_results=0
        )
        
        # 3. Add to session and commit
        with self._get_session() as session:
            session.add(new_record)



    def refresh_cache(self):
        """
        Iterates through all cached queries and re-queries the web service
        to refresh the data. Updates refresh statistics for each record.
        """

        #timestamp = str(datetime.now().isoformat())
        #eprint(f"{timestamp}: INFO: KPQueryCacher.refresh_cache: Starting KP response cache refresh process")
        start_time = time.time()

        session = self.Session()
        records = session.query(KPQuery).all()
        cached_queries = [record.to_dict() for record in records]

        cached_queries_to_refresh = []
        cache_stats = { 'min_query_age': 9999999, 'max_query_age': 0.0 }
        for cached_query in cached_queries:

            #### Skip non http entries
            if not cached_query['query_url'].startswith('http'):
                continue

            time_now = datetime.now()
            time_at_last_refresh_str = cached_query['last_successful_refresh_datetime'] or cached_query['last_attempted_refresh_datetime'] or cached_query['first_request_datetime']
            time_at_last_refresh = datetime.strptime(time_at_last_refresh_str, "%Y-%m-%d %H:%M:%S")
            time_difference = time_now - time_at_last_refresh
            seconds_difference = time_difference.total_seconds()
            hours_difference = seconds_difference / 3600

            if hours_difference < cache_stats['min_query_age']:
                cache_stats['min_query_age'] = hours_difference
            if hours_difference > cache_stats['max_query_age']:
                cache_stats['max_query_age'] = hours_difference

            #eprint(f"      kp_query_id={cached_query['kp_query_id']}  Stale by {hours_difference:.3f} hours")
            if hours_difference > AGE_BEFORE_REFRESH_HOURS:
                cached_queries_to_refresh.append(cached_query)

        timestamp = str(datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: KPQueryCacher.refresh_cache: Assessed {len(cached_queries)} cached queries: min_query_age={cache_stats['min_query_age']:.3f} hr, max_query_age={cache_stats['max_query_age']:.3f} hr")
        eprint(f"{timestamp}: INFO: KPQueryCacher.refresh_cache: {len(cached_queries_to_refresh)} cache records stale enough to refresh")

        iquery = 0
        for cached_query in cached_queries_to_refresh:

            record = session.query(KPQuery).filter_by(kp_query_id=cached_query['kp_query_id']).first()
            if not record:
                print(f"Skipping kp_query_id {cached_query[kp_query_id]}, record not found (deleted?).")
                continue
                
            eprint(f"{timestamp}: INFO: KPQueryCacher.refresh_cache: Refreshing query {record.kp_query_id} ({iquery+1} of {len(cached_queries_to_refresh)}) to {record.query_url}")

            # 1. Log the attempt
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            record.last_attempted_refresh_datetime = now_str
            
            # 2. Post the query
            response_data, status_code, elapsed, error = self.post_query_to_web_service(
                record.query_url,
                record.query_object, 
                timeout=30
            )
            
            # 3. Update stats based on outcome
            record.last_refresh_elapsed = elapsed
            record.last_refresh_http_code = status_code
            
            if error:
                # Refresh failed
                status_code_message = status_code
                if status_code_message == -1:
                    status_code_message = '30s Timeout'
                record.status = f"REFRESH_FAILED: {status_code_message}"
                record.n_failed_refreshes = (record.n_failed_refreshes or 0) + 1
                timestamp = str(datetime.now().isoformat())
                eprint(f"{timestamp}: INFO: KPQueryCacher.refresh_cache: Attempt to refresh query to {record.query_url} failed with code {status_code} after {time.time() - start_time} seconds")

            else:
                # Refresh succeeded
                record.status = "OK"
                record.n_successful_refreshes = (record.n_successful_refreshes or 0) + 1
                record.last_successful_refresh_datetime = now_str
                record.last_refresh_n_results = self._get_n_results(response_data)
                
                # 4. Compare results
                filepath = self._get_cache_filepath(record.query_hash)
                if True: #try:
                    old_response_data = self._read_cache_file(filepath)
                    if isinstance(old_response_data, tuple):
                        old_response_n_results = old_response_data[0]['message']['results']
                    else:
                        old_response_n_results = old_response_data['message']['results']
                    if old_response_n_results == response_data['message']['results']:
                        #eprint(f"The 'result' portion of the new response is the same as the old")
                        record.n_refresh_same_results = (record.n_refresh_same_results or 0) + 1
                    else:
                        #eprint(f"The 'result' portion of the new response is the different than the old. Storing new response")
                        record.n_refresh_different_results = (record.n_refresh_different_results or 0) + 1
                        # Overwrite file with new data
                        self._write_cache_file(filepath, response_data)
                #except FileNotFoundError:
                #    # File was missing, so this counts as "different"
                #    record.n_refresh_different_results = (record.n_refresh_different_results or 0) + 1
                #    self._write_cache_file(filepath, response_data)
                #except Exception as e:
                else:
                    print(f"Error comparing/writing cache file {filepath}: {e}")

            # Commit changes for this single record
            session.commit()
            iquery += 1

            #### Compute how long we've been working on refreshing, and if more than the limit, yield control again for now
            working_time = time.time() - start_time
            if working_time > REFRESH_TIME_LIMIT_SECONDS:
                timestamp = str(datetime.now().isoformat())
                eprint(f"{timestamp}: INFO: KPQueryCacher.refresh_cache: Working time {working_time:.1f} seconds. This is greater than {REFRESH_TIME_LIMIT_SECONDS} seconds, pausing refresh process")
                break

        #except Exception as e:
        #    print(f"An error occurred during refresh loop: {e}")
        #    session.rollback()
        #finally:
        session.close()

        #timestamp = str(datetime.now().isoformat())
        #eprint(f"{timestamp}: INFO: KPQueryCacher.refresh_cache: Refresh process complete for now")



    def get_cached_input_query(self, kp_query_id: int) -> str:
        """
        Fetches the input query for a given kp_query_id

        :return: A dict-list representation of the KP query payload.
        """
        session = self.Session()
        record = session.query(KPQuery).filter_by(kp_query_id=kp_query_id).first()
        if not record:
            print(f"kp_query_id {kp_query_id} not found")
            return

        return record.query_object



    def delete_input_query(self, kp_query_id: int) -> str:
        """
        Deletes given kp_query_id

        :return: nothing.
        """
        session = self.Session()
        record = session.query(KPQuery).filter_by(kp_query_id=kp_query_id).first()
        if record:
            eprint(f"INFO: Deleting record for kp_query_id={kp_query_id}")
            session.delete(record)
            session.commit()
            eprint(f"INFO: Done")
            return
        
        eprint(f"ERROR: Unable to find record for kp_query_id={kp_query_id}")

        return



    def list_cached_queries(self) -> str:
        """
        Generates a JSON-encoded list of all query records in the cache.
        The 'query_object' field is redacted to avoid serializing large data.

        :return: A JSON string representing the list of cached query records.
        """
        with self._get_session() as session:
            records = session.query(KPQuery).all()
            cached_queries = [record.to_dict() for record in records]

        columns_to_round = { 'query_age_hr': 3, 'first_query_elapsed': 2, 'last_refresh_elapsed': 2 }

        cache_stats = { 'n_cached_queries': len(cached_queries),
                        'age_before_refresh_hr': AGE_BEFORE_REFRESH_HOURS,
                        'min_query_age_hr': 9999999,
                        'max_query_age_hr': 0.0,
                        'http_status_codes': {} }
        time_now = datetime.now()
        for cached_query in cached_queries:

            time_at_last_refresh_str = cached_query['last_successful_refresh_datetime'] or cached_query['last_attempted_refresh_datetime'] or cached_query['first_request_datetime']
            time_at_last_refresh = datetime.strptime(time_at_last_refresh_str, "%Y-%m-%d %H:%M:%S")
            time_difference = time_now - time_at_last_refresh
            seconds_difference = time_difference.total_seconds()
            hours_difference = seconds_difference / 3600
            cached_query['query_age_hr'] = hours_difference

            for column,digits in columns_to_round.items():
                if cached_query[column] is not None:
                    cached_query[column] = round(cached_query[column], digits)

            if hours_difference < cache_stats['min_query_age_hr']:
                cache_stats['min_query_age_hr'] = hours_difference
            if hours_difference > cache_stats['max_query_age_hr']:
                cache_stats['max_query_age_hr'] = hours_difference

            http_status_code = cached_query['last_refresh_http_code'] or cached_query['first_query_http_code']
            if http_status_code not in cache_stats['http_status_codes']:
                cache_stats['http_status_codes'][http_status_code] = 0
            cache_stats['http_status_codes'][http_status_code] += 1

        column_data = [
            { "key": "kp_query_id", "title": "id", "title_hover": "Integer identifier of the cached KP query" },
            { "key": "status", "title": "status", "title_hover": "Status of the cached KP query" },
            { "key": "query_age_hr", "title": "age hr", "title_hover": "Age of the cache entry in hours", "red_if_greater_than_stat": "age_before_refresh_hr" },
            { "key": "kp_curie", "title": "KP curie", "title_hover": "CURIE of the target KP", "cell_hover_key": "query_url" },
            { "key": "first_request_datetime", "title": "first datetime", "title_hover": "Datetime of the first attempt at this query" },
            { "key": "last_request_datetime", "title": "last datetime", "title_hover": "Datetime of the most recent request of this query" },
            { "key": "first_query_elapsed", "title": "first elapsed", "title_hover": "Elapsed of the first query attempt in seconds", "red_if_greater_than_value": 5 },
            { "key": "first_query_http_code", "title": "first code", "title_hover": "HTTP code of the first query attempt (-1 is a timeout)", "red_if_not_equal_to_value": 200 },
            { "key": "first_query_n_results", "title": "first n results", "title_hover": "Number of TRAPI results in first query attempt" },
            { "key": "n_requests", "title": "n requests", "title_hover": "Number of total ARAX requests for this query" },
            { "key": "last_attempted_refresh_datetime", "title": "last attempted datetime", "title_hover": "Datetime of the last attempt to refresh this query" },
            { "key": "last_successful_refresh_datetime", "title": "last success datetime", "title_hover": "Datetime of the last successful attempt to refresh this query" },
            { "key": "n_successful_refreshes", "title": "n success", "title_hover": "Number of successful refreshes" },
            { "key": "n_failed_refreshes", "title": "n failed", "title_hover": "Number of failed refreshes", "red_if_greater_than_value": 0 },
            { "key": "last_refresh_elapsed", "title": "last elapsed", "title_hover": "Elapsed time of the last refresh attempt in seconds", "red_if_greater_than_value": 5 },
            { "key": "last_refresh_http_code", "title": "last code", "title_hover": "HTTP code of the last refresh attempt (-1 is a timeout)", "red_if_not_equal_to_value": 200 },
            { "key": "last_refresh_n_results", "title": "last n results", "title_hover": "Number of TRAPI results in the most recent successful refresh attempt" },
            { "key": "n_refresh_same_results", "title": "n same", "title_hover": "Number of refreshes that yielded the same results as the most recent successful refresh" },
            { "key": "n_refresh_different_results", "title": "n diff", "title_hover": "Number of refreshes that yielded different results as the most recent successful refresh", "red_if_greater_than_value": 0 },
        ]

        cache_stats['total_cache_size_MiB'] = sum(os.path.getsize(f"{self.cache_dir}/{file}") for file in os.listdir(self.cache_dir)) / 1024 / 1024

        response = { 'cache_stats': cache_stats, 'column_data': column_data, 'cache_data': cached_queries }
        return response



############################################ Main ############################################################
#### If this class is run from the command line, allow some basic testing of the class functionality
def main():

    #### Parse command line options
    import argparse
    argparser = argparse.ArgumentParser(description='CLI testing of the KPQueryCacher class')
    argparser.add_argument('--verbose', action='count', help='If set, print more information about ongoing processing' )
    argparser.add_argument('--initialize_cache', action='count', help='Invoke this parameter to (re)initialize the cache')
    argparser.add_argument('--query_number', action='store', help='Specify a number 0-9 to perform a test query with MONDO:000514n')
    argparser.add_argument('--summarize', action='count', help='Summarize the queries in the cache')
    argparser.add_argument('--list', action='count', help='List all queries in the cache')
    argparser.add_argument('--show_input_query', action='store', help='Print the input query for a given kp_query_id')
    argparser.add_argument('--delete_query', action='store', help='Delete the given kp_query_id')
    argparser.add_argument('--refresh', action='count', help='Refresh all queries in the cache')
    params = argparser.parse_args()

    verbose = False
    if params.verbose:
        verbose = True

    eprint(f"Create a cacher instance")
    cacher = KPQueryCacher()

    if params.initialize_cache:
        eprint(f"(Re)initializing the query cache")
        cacher.initialize_cache()
        eprint(f"Complete")
        return

    if params.show_input_query:
        result = cacher.get_cached_input_query(params.show_input_query)
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)
        return

    if params.delete_query:
        result = cacher.delete_input_query(params.delete_query)
        return

    if params.query_number:
        test_curie = "MONDO:000514" + params.query_number
        trapi_query = {
            "message": {
                "query_graph": {
                    "nodes": {"n0": {"ids": [test_curie]}, "n1": {"categories": ["biolink:ChemicalEntity"]}},
                    "edges": {"e01": {"subject": "n1", "object": "n0", "predicates": ["biolink:treats"]}}
                }
            }
        }

        query_destination = 0
        if query_destination == 0:
            kp_url = 'https://kg2cploverdb.ci.transltr.io/query'
            kp_curie = 'infores:rtx-kg2'
        elif query_destination == 1:
            kp_url = 'https://collaboratory-api.ci.transltr.io/query'
            kp_curie = 'infores:knowledge-collaboratory'
        elif query_destination == 2:
            kp_url = 'https://api.collaboratory.semanticscience.org/query'
            kp_curie = 'infores:knowledge-collaboratory'
        else:
            kp_url = 'https://gateway.systemsbiology.net/query'
            kp_curie = 'timeout_test'


        eprint(f"Checking cache for query with {test_curie} to {kp_url}")
        response_data, http_code, elapsed_time, error = cacher.get_cached_result(kp_url, trapi_query)
        if http_code != NO_CACHED_RESPONSE: 
            n_results = cacher._get_n_results(response_data)
            print(f"Fetched a response with http_code={http_code}, n_results={n_results} from the cache in {elapsed_time:.3f} seconds")
            return response_data, http_code, elapsed_time, error

        eprint(f"No cache entry found")

        eprint(f"Fetch data directly from KP {kp_url}")
        response_data, http_code, elapsed_time, error = cacher.post_query_to_web_service(kp_url, trapi_query, timeout=10)
        n_results = cacher._get_n_results(response_data)
        print(f"Fetched a response with http_code={http_code}, n_results={n_results} from the cache in {elapsed_time:.3f} seconds")

        eprint("Store the response in the cache")
        cacher.store_response(
            kp_curie=kp_curie,
            query_url=kp_url,
            query_object=trapi_query,
            response_object=response_data,
            http_code=http_code,
            elapsed_time=elapsed_time,
            status="OK"
        )
        print("Response stored.")
        return

    if params.summarize:
        eprint("Summarize queries in the cache")
        response = cacher.list_cached_queries()
        eprint(json.dumps(response['cache_stats'], indent=2, sort_keys=True))
        for entry in response['cache_data']:
            print(f"{entry['kp_query_id']}\t{entry['kp_curie']:50s}\t{entry['first_request_datetime']}\t{entry['first_query_n_results']}\t{entry['n_requests']}\t{entry['last_refresh_n_results']}")
        return


    if params.list:
        eprint("List all queries in the cache")
        response = cacher.list_cached_queries()
        eprint(json.dumps(response['cache_stats'], indent=2, sort_keys=True))
        eprint(json.dumps(response['cache_data'], indent=2, sort_keys=False))
        return


    if params.refresh:
        eprint("Refresh all queries in the cache")
        cacher.refresh_cache()
        return


if __name__ == "__main__": main()
