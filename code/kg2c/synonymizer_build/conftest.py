import pytest


def pytest_addoption(parser):
    parser.addoption("--synonymizername",
                     action="store",
                     required=True,
                     help="Specifies the name of the synonymizer file that should be "
                          "tested (e.g., node_synonymizer_v1.0_KG2.10.0.sqlite). This file must "
                          "be present in the RTX/code/ARAX/NodeSynonymizer directory locally.")


def pytest_configure(config):
    pytest.synonymizer_name = config.getoption("--synonymizername")
