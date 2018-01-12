import unittest
from tests.QueryBioLinkTests import QueryBioLinkTestCase
from tests.QueryChEMBLTests import QueryChEMBLTestCase
from tests.QueryDisGeNetTests import QueryDisGeNetTestCase
from tests.QueryDisontTests import QueryDisontTestCase
from tests.QueryGeneProfTests import QueryGeneProfTestCase
from tests.QueryMiRBaseTests import QueryMiRBaseTestCase
from tests.QueryMiRGateTests import QueryMiRGateTestCase
from tests.QueryMyGeneTests import QueryMyGeneTestCase
from tests.QueryNCBIeUtilsTests import QueryNCBIeUtilsTestCase
from tests.QueryOMIMTests import QueryOMIMTestCase
from tests.QueryPC2Tests import QueryPC2TestCase
from tests.QueryPharosTests import QueryPharosTestCase
from tests.QueryReactomeTests import QueryReactomeTestCase
from tests.QuerySciGraphTests import QuerySciGraphTestCase
from tests.QueryUniprotTests import QueryUniprotTestCase


class QueryModuleTestSuite(unittest.TestSuite):
    def suite(self):
        suite = unittest.TestSuite()

        suite.addTest(QueryBioLinkTestCase())
        suite.addTest(QueryChEMBLTestCase())
        suite.addTest(QueryDisGeNetTestCase())
        suite.addTest(QueryDisontTestCase())
        suite.addTest(QueryGeneProfTestCase())

        suite.addTest(QueryMiRBaseTestCase())
        suite.addTest(QueryMiRGateTestCase())
        suite.addTest(QueryMyGeneTestCase())
        suite.addTest(QueryNCBIeUtilsTestCase())
        suite.addTest(QueryOMIMTestCase())

        suite.addTest(QueryPC2TestCase())
        suite.addTest(QueryPharosTestCase())
        suite.addTest(QueryReactomeTestCase())
        suite.addTest(QuerySciGraphTestCase())
        suite.addTest(QueryUniprotTestCase())

        self.run(suite)


if __name__ == '__main__':
    """
    Run this module outside `tests` folder.
    
        John@Workstation ~/Documents/Git-repo/NCATS/code/reasoningtool (master)
        $ python -m unittest tests/QueryModuleTestSuite.py

    """
    unittest.main()
