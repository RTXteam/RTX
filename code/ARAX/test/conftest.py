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


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    skip_fast = pytest.mark.skip(reason="--runonlyslow option was used; this test is fast")
    for item in items:
        if "slow" in item.keywords:
            if not config.getoption("--runslow") and not config.getoption("--runonlyslow"):
                item.add_marker(skip_slow)
        elif config.getoption("--runonlyslow"):
            item.add_marker(skip_fast)
