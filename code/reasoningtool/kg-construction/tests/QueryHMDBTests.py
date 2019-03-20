from unittest import TestCase

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryHMDB import QueryHMDB

class QueryHMDBTestCases(TestCase):
    def test_get_compound_desc(self):

        desc = QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB0060288')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, "N8-Acetylspermidine belongs to the class of organic compounds known as carboximidic acids. These are organic acids with the general formula RC(=N)-OH (R=H, organic group). N8-Acetylspermidine exists as a solid, slightly soluble (in water), and an extremely weak acidic (essentially neutral) compound (based on its pKa). N8-Acetylspermidine has been detected in multiple biofluids, such as saliva, urine, and blood. N8-Acetylspermidine exists in all eukaryotes, ranging from yeast to humans. Outside of the human body, N8-acetylspermidine can be found in a number of food items such as sweet bay, gooseberry, hedge mustard, and burbot. This makes N8-acetylspermidine a potential biomarker for the consumption of these food products.")

        #   wrong url
        desc = QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB00602880')
        self.assertEqual(desc, "None")

        desc = QueryHMDB.get_compound_desc(820)
        self.assertEqual(desc, "None")