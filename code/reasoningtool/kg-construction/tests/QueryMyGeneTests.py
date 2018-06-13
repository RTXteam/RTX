import unittest
import json

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from QueryMyGene import QueryMyGene


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


class QueryMyGeneTestCase(unittest.TestCase):

    def test_get_protein_entity(self):
        mg = QueryMyGene()
        extended_info_json = mg.get_protein_entity("UniProtKB:O60884")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        if extended_info_json != "None":
            self.assertEqual(len(json.loads(extended_info_json)),
                             len(json.loads(get_from_test_file('query_test_data.json', 'UniProtKB:O60884'))))

        #   invalid parameter
        extended_info_json = mg.get_protein_entity(100847086)
        self.assertEqual(extended_info_json, "None")

    def test_get_microRNA_entity(self):
        mg = QueryMyGene()
        extended_info_json = mg.get_microRNA_entity("NCBIGene: 100847086")
        self.maxDiff = None
        self.assertIsNotNone(extended_info_json)
        if extended_info_json != "None":
            self.assertEqual(len(json.loads(extended_info_json)),
                             len(json.loads(get_from_test_file('query_test_data.json', 'NCBIGene:100847086'))))

        #   invalid parameter
        extended_info_json = mg.get_microRNA_entity(100847086)
        self.assertEqual(extended_info_json, "None")

    def test_get_protein_desc(self):
        mg = QueryMyGene()
        desc = mg.get_protein_desc("UniProtKB:O60884")
        self.assertIsNotNone(desc)
        self.assertEqual(desc, "The protein encoded by this gene belongs to the evolutionarily conserved DNAJ/HSP40 "
                               "family of proteins, which regulate molecular chaperone activity by stimulating ATPase "
                               "activity. DNAJ proteins may have up to 3 distinct domains: a conserved 70-amino acid J "
                               "domain, usually at the N terminus; a glycine/phenylalanine (G/F)-rich region; and a "
                               "cysteine-rich domain containing 4 motifs resembling a zinc finger domain. The product "
                               "of this gene works as a cochaperone of Hsp70s in protein folding and mitochondrial "
                               "protein import in vitro. [provided by RefSeq, Jul 2008].")

        desc = mg.get_protein_desc("UniProtKB:O608840")
        self.assertEqual(desc, 'None')

        #   invalid parameter
        desc = mg.get_protein_desc(608840)
        self.assertEqual(desc, 'None')

    def test_get_microRNA_desc(self):
        mg = QueryMyGene()
        desc = mg.get_microRNA_desc("NCBIGene: 100847086")
        self.assertIsNotNone(desc)
        self.assertEqual(desc, get_from_test_file('query_desc_test_data.json', 'NCBIGene:100847086'))
        self.assertEqual(desc, "microRNAs (miRNAs) are short (20-24 nt) non-coding RNAs that are involved in "
                               "post-transcriptional regulation of gene expression in multicellular organisms by "
                               "affecting both the stability and translation of mRNAs. miRNAs are transcribed by RNA "
                               "polymerase II as part of capped and polyadenylated primary transcripts (pri-miRNAs) "
                               "that can be either protein-coding or non-coding. The primary transcript is cleaved by "
                               "the Drosha ribonuclease III enzyme to produce an approximately 70-nt stem-loop "
                               "precursor miRNA (pre-miRNA), which is further cleaved by the cytoplasmic Dicer "
                               "ribonuclease to generate the mature miRNA and antisense miRNA star (miRNA*) products. "
                               "The mature miRNA is incorporated into a RNA-induced silencing complex (RISC), which "
                               "recognizes target mRNAs through imperfect base pairing with the miRNA and most commonly"
                               " results in translational inhibition or destabilization of the target mRNA. The RefSeq"
                               " represents the predicted microRNA stem-loop. [provided by RefSeq, Sep 2009].")

        desc = mg.get_microRNA_desc("NCBIGene: 1008470860")
        self.assertEqual(desc, 'None')

        #   invalid parameter
        desc = mg.get_microRNA_desc(1008470860)
        self.assertEqual(desc, 'None')

    def test_get_protein_name(self):
        mg = QueryMyGene()
        name = mg.get_protein_name("UniProtKB:O60884")
        self.assertIsNotNone(name)
        self.assertEqual(name, "DnaJ heat shock protein family (Hsp40) member A2")

        name = mg.get_protein_name("UniProtKB:P05231")
        self.assertIsNotNone(name)
        self.assertEqual(name, "interleukin 6")

        name = mg.get_protein_name("UniProtKB:O608840")
        self.assertEqual(name, 'None')

        #   invalid parameter
        name = mg.get_protein_name(608840)
        self.assertEqual(name, 'None')

if __name__ == '__main__':
    unittest.main()