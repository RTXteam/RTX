import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryReactome import QueryReactome as QR

def get_from_test_file(filename, key):
    f = open(filename, 'r')
    test_data = f.read()
    try:
        test_data_dict = json.loads(test_data)
        f.close()
        return test_data_dict[key]
    except ValueError:
        f.close()
        return None


class QueryReactomeTestCase(unittest.TestCase):
    def test_get_pathway_entity(self):
        extended_info_json = QR.get_pathway_entity('REACT:R-HSA-70326')
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        if extended_info_json != "None":
            self.assertEqual(json.loads(extended_info_json), json.loads(get_from_test_file('query_test_data.json', 'REACT:R-HSA-70326')))

        extended_info_json = QR.get_pathway_entity('REACT:R-HSA-703260')
        self.assertEqual(extended_info_json, "None")

        extended_info_json = QR.get_pathway_entity(70326)
        self.assertEqual(extended_info_json, "None")

    def test_get_pathway_desc(self):
        desc = QR.get_pathway_desc('REACT:R-HSA-70326')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, "Glucose is the major form in which dietary sugars are made available to cells of the "
                               "human body. Its breakdown is a major source of energy for all cells, and is essential "
                               "for the brain and red blood cells. Glucose utilization begins with its uptake by cells "
                               "and conversion to glucose 6-phosphate, which cannot traverse the cell membrane. Fates "
                               "open to cytosolic glucose 6-phosphate include glycolysis to yield pyruvate, glycogen "
                               "synthesis, and the pentose phosphate pathway. In some tissues, notably the liver and "
                               "kidney, glucose 6-phosphate can be synthesized from pyruvate by the pathway of "
                               "gluconeogenesis.")

        desc = QR.get_pathway_desc('REACT:R-HSA-703260')
        self.assertEqual(desc, 'None')

        desc = QR.get_pathway_desc(70326)
        self.assertEqual(desc, 'None')

if __name__ == '__main__':
    unittest.main()