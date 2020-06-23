from unittest import TestCase
import unittest
import json
from QueryCOHD import QueryCOHD

class NewQueryCOHDTestCases(TestCase):
    def test_get_source_to_target_input(self):
        # initialise QueryCOHD object
        queryCOHD = QueryCOHD()

        # invalid parameter type
        result = queryCOHD.get_source_to_target('312327', 313217)
        self.assertEqual(result, [])

        # invalid parameter type
        result = queryCOHD.get_source_to_target(312327, '313217')
        self.assertEqual(result, [])

    def test_get_source_to_target_has_result(self):
        # initialise QueryCOHD object
        queryCOHD = QueryCOHD()

        # check if correct result is returned
        result = queryCOHD.get_source_to_target(312327, 313217)
        self.assertIsNotNone(result)

    def test_get_source_to_target_result(self):
        # initialise QueryCOHD object
        queryCOHD = QueryCOHD()
        # load test data
        with open("./tests/NewQueryCOHDTestsData.json") as file:
            test_data = json.load(file)

        # check if correct result is returned
        result = queryCOHD.get_source_to_target(312327, 313217)
        self.assertEqual(result, test_data)

if __name__ == '__main__':
    unittest.main()
