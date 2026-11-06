"""
Unit tests for storing a response over an existing record in Expand/trapi_query_cacher.py.

These use a temporary database and cache directory, so they need no KP and don't touch the real
cache. Lookups return `last_refresh_http_code or first_query_http_code`, so a refresh code left
over from an earlier response can hide what was just stored.

Usage:
  pytest -v test_trapi_query_cacher.py
"""

import os
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")
from Expand.trapi_query_cacher import NO_CACHED_RESPONSE, Base, KPQuery, KPQueryCacher

KP_CURIE = "infores:retriever"
QUERY_URL = "https://kp.example.org/query"
QUERY: dict = {"message": {"query_graph": {"nodes": {}, "edges": {}}}}
TIMEOUT_CODE = -1


@pytest.fixture(name="cacher")
def fixture_cacher(tmp_path):
    cacher = KPQueryCacher.__new__(KPQueryCacher)
    cacher.db_file_path = str(tmp_path / "cache.sqlite")
    cacher.cache_dir = str(tmp_path / "responses")
    os.makedirs(cacher.cache_dir)
    cacher.engine = create_engine(f"sqlite:///{cacher.db_file_path}")
    cacher.Session = sessionmaker(bind=cacher.engine)
    Base.metadata.create_all(cacher.engine)
    return cacher


def _store(cacher, response, http_code):
    cacher.store_response(kp_curie=KP_CURIE, query_url=QUERY_URL, query_object=QUERY,
                          response_object=response, http_code=http_code, elapsed_time=0.1)


def _mark_refreshed_ok(cacher):
    # What refresh_cache() writes after a successful refresh
    with cacher._get_session() as session:
        record = session.query(KPQuery).one()
        record.last_refresh_http_code = 200
        record.last_attempted_refresh_http_code = 200
        record.last_attempted_refresh_datetime = "2020-01-01 00:00:00"
        record.last_successful_refresh_datetime = "2020-01-01 00:00:00"
        record.last_refresh_elapsed = 1.0
        record.last_refresh_n_results = 1


def _age_record(cacher, hours):
    with cacher._get_session() as session:
        record = session.query(KPQuery).one()
        old_time = datetime.now() - timedelta(hours=hours)
        record.first_request_datetime = old_time.strftime('%Y-%m-%d %H:%M:%S')


def test_timeout_over_refreshed_record_is_not_reported_as_success(cacher):
    _store(cacher, {"message": {"results": [{}]}}, 200)
    _mark_refreshed_ok(cacher)

    _store(cacher, None, TIMEOUT_CODE)  # e.g. bypass_cache=true, and the KP timed out this time

    response, http_code, _, _ = cacher.get_cached_result(QUERY_URL, QUERY)
    assert response is None
    assert http_code == TIMEOUT_CODE


def test_timeout_over_refreshed_record_expires_like_any_other_timeout(cacher):
    _store(cacher, {"message": {"results": [{}]}}, 200)
    _mark_refreshed_ok(cacher)
    _store(cacher, None, TIMEOUT_CODE)

    _age_record(cacher, hours=1)

    response, http_code, _, _ = cacher.get_cached_result(QUERY_URL, QUERY)
    assert response is None
    assert http_code == NO_CACHED_RESPONSE


def test_storing_again_clears_all_refresh_fields(cacher):
    _store(cacher, {"message": {"results": [{}]}}, 200)
    _mark_refreshed_ok(cacher)

    new_response = {"message": {"results": [{}, {}]}}
    _store(cacher, new_response, 200)

    with cacher._get_session() as session:
        record = session.query(KPQuery).one()
        assert record.last_refresh_http_code is None
        assert record.last_attempted_refresh_http_code is None
        assert record.last_attempted_refresh_datetime is None
        assert record.last_successful_refresh_datetime is None
        assert record.last_refresh_elapsed is None
        assert record.last_refresh_n_results is None

    response, http_code, _, _ = cacher.get_cached_result(QUERY_URL, QUERY)
    assert response == new_response
    assert http_code == 200
