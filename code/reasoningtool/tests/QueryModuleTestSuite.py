import unittest
from tests.QueryBioLinkTests import QueryBioLinkTestCase
from tests.QueryChEMBLTests import QueryChEMBLTestCase
from tests.QueryDisGeNetTests import QueryDisGeNetTestCase
from tests.QueryDisontTests import QueryDisontTestCase
from tests.QueryGeneProfTests import QueryGeneProfTestCase
from tests.QueryMiRBaseTests import QueryMiRBaseTestCase



class QueryModuleTestSuite(unittest.TestSuite):
    def suite(self):
        suite = unittest.TestSuite()

        suite.addTest(QueryBioLinkTestCase())
        suite.addTest(QueryChEMBLTestCase())
        suite.addTest(QueryDisGeNetTestCase())
        suite.addTest(QueryDisontTestCase())
        suite.addTest(QueryGeneProfTestCase())
        suite.addTest(QueryMiRBaseTestCase())

        self.run(suite)


if __name__ == '__main__':
    unittest.main()
