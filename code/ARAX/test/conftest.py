#!/usr/bin/env python3
import pytest
# Thanks https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option


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


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "external: mark test as relying on an external KP")


def pytest_collection_modifyitems(config, items):
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    skip_fast = pytest.mark.skip(reason="--runonlyslow option was used; this test is fast")
    skip_external = pytest.mark.skip(reason="need --runexternal option to run")
    for item in items:
        if "slow" in item.keywords:
            if not config.getoption("--runslow") and not config.getoption("--runonlyslow"):
                item.add_marker(skip_slow)
        elif config.getoption("--runonlyslow"):
            item.add_marker(skip_fast)

        if "external" in item.keywords:
            if not config.getoption("--runexternal"):
                item.add_marker(skip_external)
