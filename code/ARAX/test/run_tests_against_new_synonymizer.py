"""
Runs test_ARAX_synonymizer.py against node_synonymizer_new.py
by patching the import before pytest loads the test module.

Usage: python run_tests_against_new_synonymizer.py
"""
import sys
import os

# Add the NodeSynonymizer directory to path
synonymizer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "NodeSynonymizer")
sys.path.insert(0, synonymizer_dir)

# Import the NEW synonymizer and register it under the OLD module name
# so that `from node_synonymizer import NodeSynonymizer` in the test file
# picks up node_synonymizer_new.NodeSynonymizer instead.
import node_synonymizer_new
sys.modules["node_synonymizer"] = node_synonymizer_new

import pytest
sys.exit(pytest.main(["-v", "--tb=short", os.path.join(os.path.dirname(__file__), "test_ARAX_synonymizer.py")]))
