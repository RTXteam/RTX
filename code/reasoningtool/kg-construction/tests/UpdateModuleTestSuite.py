"""
    Before running the test suite, create config.json in the same directory as UpdateModuleTestSuite.py

    config.json
    {
        "url":"bolt://localhost:7687"
        "username":"xxx",
        "password":"xxx"
    }


    Run this module outside `tests` folder.
        $ cd [git repo]/code/reasoningtool/kg-construction/tests
        $ python3 -m unittest UpdateModuleTestSuite.py
"""


import unittest

from UpdateNodesInfoTests import UpdateNodesInfoTestCase
from Neo4jConnectionTests import Neo4jConnectionTestCase
from QueryBioLinkExtendedTests import QueryBioLinkExtendedTestCase
from QueryMyChemTests import QueryMyChemTestCase
from QueryMyGeneExtendedTests import QueryMyGeneExtendedTestCase
from QueryReactomeExtendedTests import QueryReactomeExtendedTestCase


class UpdateModuleTestSuite(unittest.TestSuite):
    def suite(self):
        suite = unittest.TestSuite()

        suite.addTest(UpdateNodesInfoTestCase())
        suite.addTest(Neo4jConnectionTestCase())
        suite.addTest(QueryBioLinkExtendedTestCase())
        suite.addTest(QueryMyChemTestCase())
        suite.addTest(QueryMyGeneExtendedTestCase())
        suite.addTest(QueryReactomeExtendedTestCase())

        return suite


if __name__ == '__main__':
    unittest.main()