import unittest
from QueryGeneProf import QueryGeneProf as QGP


class QueryGeneProfTestCase(unittest.TestCase):
    def test_gene_symbol_to_geneprof_ids(self):
        ret_set = QGP.gene_symbol_to_geneprof_ids('HMOX1')
        known_set = {16269}
        self.assertSetEqual(ret_set, known_set)

    def test_geneprof_id_to_transcription_factor_gene_symbols(self):
        ret_set = QGP.geneprof_id_to_transcription_factor_gene_symbols(16269)
        known_set = {'IRF1', 'ELK4', 'WRNIP1', 'FLI1', 'E2F4', 'KDM4A', 'GATA6',
                     'SPI1', 'GATA1', 'CDX2', 'ETV1', 'WHSC1', 'SOX2', 'CTCF',
                     'CUX1', 'ZNF143', 'HDAC1', 'MAFF', 'SREBF1', 'BACH1', 'MAZ',
                     'TRIM28', 'USF2', 'KDM5B', 'BRCA1', 'SMARCC1', 'CCNT2', 'TBP',
                     'ZMIZ1', 'CHD1', 'UBTF', 'SAP30', 'STAT3', 'RBBP5', 'BRD7',
                     'POU5F1', 'MYC', 'MAX', 'KLF4', 'RAD21', 'PPARG', 'HSF1',
                     'ZC3H11A', 'HCFC1', 'SMARCB1', 'JUN', 'SMARCA4', 'RCOR1',
                     'TAL1', 'TFAP2A', 'CHD7', 'CEBPB', 'BHLHE40', 'JUND', 'BCL6',
                     'E2F1', 'MAFK', 'STAT1', 'ZNF384', 'CREBBP', 'ZNF263', 'SMARCC2',
                     'E2F6', 'MXI1', 'POU2F1', 'KDM1A', 'HMGN3', 'POLR3A', 'SETDB1',
                     'PHF8', 'TBL1XR1', 'GTF2F1', 'RFX5', 'ESRRA', 'HNF4A', 'FOXA1',
                     'NFE2', 'HDAC2', 'EOMES', 'EP300', 'FOS'}

        self.assertSetEqual(ret_set, known_set)

    def test_gene_symbol_to_transcription_factor_gene_symbols(self):
        ret_set = QGP.gene_symbol_to_transcription_factor_gene_symbols('IRF1')
        known_set = {'POU5F1', 'CREBBP', 'SMARCC1', 'BRD7', 'SIRT6', 'SPI1',
                     'SUZ12', 'CDX2', 'ELK1', 'EP300', 'GATA2', 'E2F6', 'ESRRA',
                     'RBBP5', 'JUN', 'TFAP2A', 'TAF2', 'HCFC1', 'MAZ', 'CUX1', 'MAX',
                     'HNF4A', 'EOMES', 'ETS1', 'KDM4A', 'TBL1XR1', 'ZNF143', 'ZC3H11A',
                     'BRCA1', 'ETV1', 'GATA3', 'CTNNB1', 'POLR3A', 'PHF8', 'FOS', 'USF2',
                     'RUNX1', 'RFX5', 'WRNIP1', 'ZNF263', 'UBTF', 'CEBPB', 'SMARCA4', 'GATA1',
                     'CHD7', 'TAL1', 'BHLHE40', 'E2F4', 'FOXA1', 'SMC3', 'MAFF', 'DDX5', 'BACH1',
                     'EZH2', 'CTCF', 'CHD1', 'MYC', 'KDM5B', 'HDAC2', 'ZNF384', 'RAD21', 'WHSC1',
                     'PRDM14', 'NFATC1', 'IRF1', 'KDM1A', 'HDAC6', 'SAP30', 'CCNT2', 'KLF4',
                     'SMARCB1', 'TRIM28', 'HMGN3', 'GTF2F1', 'STAT3', 'JUND', 'MXI1', 'CHD2',
                     'TBP', 'E2F1', 'SREBF1', 'HDAC1', 'SETDB1', 'ZMIZ1', 'STAT1', 'RCOR1'}

        self.assertSetEqual(ret_set, known_set)


if __name__ == '__main__':
    unittest.main()
