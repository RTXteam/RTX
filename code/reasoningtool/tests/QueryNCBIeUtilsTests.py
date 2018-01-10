import unittest
from QueryNCBIeUtils import QueryNCBIeUtils


# TODO complete tests for other functions
class QueryNCBIeUtilsTestCase(unittest.TestCase):
    def test_get_medgen_uid_for_omim_id(self):
        medgen_ids = QueryNCBIeUtils.get_medgen_uid_for_omim_id(219550)
        known_ids = {346587}

        self.assertSetEqual(medgen_ids, known_ids)


if __name__ == '__main__':
    unittest.main()
