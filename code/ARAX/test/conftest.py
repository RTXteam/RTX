#!/usr/bin/env python3
import os
import sys
import time

import pytest
pathlist = os.path.realpath(__file__).split(os.path.sep)
sys.path.append(os.path.sep.join([*pathlist[:(pathlist.index("RTX") + 1)], "code", "ARAX", "ARAXQuery"]))
from ARAX_database_manager import ARAXDatabaseManager
sys.path.append(os.path.sep.join([*pathlist[:(pathlist.index("RTX") + 1)], "code", "ARAX", "ARAXQuery", "Expand"]))
from kp_info_cacher import KPInfoCacher


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="include slow tests"
    )
    parser.addoption(
        "--runonlyslow", action="store_true", default=False, help="run only slow tests"
    )
    parser.addoption(
        "--runexternal", action="store_true", default=False, help="include tests that rely on external KPs"
    )
    parser.addoption(
        "--runonlyexternal", action="store_true", default=False, help="run only external tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "external: mark test as relying on an external KP")


def pytest_sessionstart(session):
    """
    Pytest runs these steps at the beginning of the testing session (prior to running any tests)
    """
    # Ensure local databases are up to date
    print(f"Running database manager to check for missing databases..")
    db_manager = ARAXDatabaseManager(allow_downloads=True)
    db_manager.update_databases()

    # Refresh KP info cache if it hasn't been updated in more than an hour
    kp_info_cacher = KPInfoCacher()
    cache_exists = os.path.exists(kp_info_cacher.smart_api_and_meta_map_cache)
    if cache_exists:
        cache_is_stale = time.time() - os.path.getmtime(kp_info_cacher.smart_api_and_meta_map_cache) > 3600
    else:
        cache_is_stale = True
    if cache_exists and not cache_is_stale:
        print(f"KP info cache is up to date.")
    else:
        print(f"Running KP info cacher to update stale/missing cache..")
        kp_info_cacher.refresh_kp_info_caches()


def pytest_collection_modifyitems(config, items):
    # Thanks docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    skip_fast = pytest.mark.skip(reason="--runonlyslow option was used; this test is fast")
    skip_external = pytest.mark.skip(reason="need --runexternal option to run")
    skip_internal = pytest.mark.skip(reason="--runonlyexternal option was used; this test is internal")
    for item in items:
        if "slow" in item.keywords:
            if not config.getoption("--runslow") and not config.getoption("--runonlyslow"):
                item.add_marker(skip_slow)
        elif config.getoption("--runonlyslow"):
            item.add_marker(skip_fast)

        if "external" in item.keywords:
            if not config.getoption("--runexternal") and not config.getoption("--runonlyexternal"):
                item.add_marker(skip_external)
        elif config.getoption("--runonlyexternal"):
            item.add_marker(skip_internal)
