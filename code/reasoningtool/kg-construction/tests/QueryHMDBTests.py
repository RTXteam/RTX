from unittest import TestCase

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryHMDB import QueryHMDB

class QueryHMDBTestCases(TestCase):
    def test_get_compound_desc(self):

        desc = QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB0060288')
        self.assertIsNotNone(desc)
        self.assertEqual(desc, "N8-acetylspermidine, also known as n(8)-acetylspermidine dihydrochloride or N-[4-[(3-aminopropyl)amino]butyl]-acetamide, is a member of the class of compounds known as carboximidic acids. Carboximidic acids are organic acids with the general formula RC(=N)-OH (R=H, organic group). N8-acetylspermidine is slightly soluble (in water) and an extremely weak acidic compound (based on its pKa). N8-acetylspermidine can be found in a number of food items such as star anise, garland chrysanthemum, pomes, and hyssop, which makes n8-acetylspermidine a potential biomarker for the consumption of these food products. N8-acetylspermidine can be found primarily in blood, saliva, and urine. N8-acetylspermidine exists in all living species, ranging from bacteria to humans. Moreover, n8-acetylspermidine is found to be associated with perillyl alcohol administration for cancer treatment and thyroid cancer . N8-Acetylspermidine is a polyamine. The polyamines, found in virtually all living organisms, are a ubiquitous group of compounds that appear to play a vital role in many cellular processes involving nucleic acids including cell growth and differentiation. The polyamines, found in virtually all living organisms, are a ubiquitous group of compounds that appear to play a vital role in many cellular processes involving nucleic acids including cell growth and differentiation. Acetylation on the terminal nitrogen adjacent to the 4-carbon chain produces N8-acetylspermidine. This reaction is catalyzed by spermidine N8-acetyltransferase and does not result in the conversion of spermidine to putrescine but, instead, the product undergoes deacetylation. This acetyltransferase appears to be associated with chromatin in the cell nucleus and has been reported to be the same as (or related to) the enzyme(s) responsible for histone acetylation. N8-Acetylspermidine does not accumulate in tissues but rather appears to be rapidly deacetylated back to spermidine by a relatively specific cytosolic deacetylase, N8-acetylspermidine deacetylase. The function of this N8-acetylation/deacetylation pathway in cellular processes is not understood clearly, but several observations have suggested a role in cell growth and differentiation (PMID: 12093478)..")

        #   wrong url
        desc = QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB00602880')
        self.assertEqual(desc, "None")

        desc = QueryHMDB.get_compound_desc(820)
        self.assertEqual(desc, "None")