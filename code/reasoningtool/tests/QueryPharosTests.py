import unittest
from QueryPharos import QueryPharos


# TODO complete tests for other functions
class QueryPharosTestCase(unittest.TestCase):
    def test_query_drug_id_by_name(self):
        ret = QueryPharos.query_drug_id_by_name('lovastatin')
        self.assertEqual(ret, 254599)


if __name__ == '__main__':
    unittest.main()
