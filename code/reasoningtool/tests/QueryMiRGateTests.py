import unittest
from QueryMiRGate import QueryMiRGate as QMG


class QueryMiRGateTestCase(unittest.TestCase):
    def test_get_microrna_ids_that_regulate_gene_symbol(self):
        res_ids = QMG.get_microrna_ids_that_regulate_gene_symbol('HMOX1')
        known_ids = {'MIMAT0002174', 'MIMAT0000077', 'MIMAT0021021', 'MIMAT0023252',
                     'MIMAT0016901', 'MIMAT0019723', 'MIMAT0019941', 'MIMAT0018996',
                     'MIMAT0015029', 'MIMAT0019227', 'MIMAT0014989', 'MIMAT0015078',
                     'MIMAT0005920', 'MIMAT0014978', 'MIMAT0024616', 'MIMAT0019012',
                     'MIMAT0022726', 'MIMAT0018965', 'MIMAT0019913', 'MIMAT0014990',
                     'MIMAT0019028', 'MIMAT0019806', 'MIMAT0015238', 'MIMAT0025852',
                     'MIMAT0019844', 'MIMAT0005905', 'MIMAT0023696', 'MIMAT0005871',
                     'MIMAT0019829', 'MIMAT0019041', 'MIMAT0019699', 'MIMAT0004776',
                     'MIMAT0019218'}

        self.assertSetEqual(res_ids, known_ids)

    def test_get_gene_symbols_regulated_by_microrna(self):
        res_ids = QMG.get_gene_symbols_regulated_by_microrna('MIMAT0018979')

        known_ids = {'NISCH', 'MED16', 'FAM53C', 'DGKA', 'GFAP', 'TMEM208', 'COPS7A',
                     'ELSPBP1', 'FKTN', 'RP11-617B3.2', 'ELP5', 'AC025335.1', 'PCBP1-AS1',
                     'TRAF3', 'P4HA2', 'RABL2A', 'HSP90AB1', 'ST13', 'GPX4', 'HMGN2',
                     'RP11-317J19.1', 'DNAJA4', 'TUBA1B', 'COL1A1', 'C22orf25', 'DHX30',
                     'LINC00469', 'PROM2', 'CTD-2062F14.3', 'SSBP1', 'BIRC6', 'RP11-998D10.7',
                     'NPTX2', 'GPR85', 'CDCA5', 'ATF7IP', 'AC010148.1', 'AGAP3', 'BMPER',
                     'MAGED1', 'REG1A', 'DUSP11', 'TCF12', 'SPTBN2', 'SEMA4G', 'DRG2', 'DUS4L',
                     'AC012067.1', 'BMF', 'PPM1M', 'TPM1', 'AC105344.2', 'LPIN1', 'PHKG2',
                     'RP11-84C10.2', 'IFI27', 'AP001442.2', 'CDK14', 'LRIG2', 'EEFSEC', 'C17orf75',
                     'IKBKB', 'MIR655', 'RP11-473I1.10', 'CDH18', 'NSD1', 'ZNF330', 'NCAM1',
                     'TCAIM', 'LINC00665', 'ILF3', 'SCRN1', 'PELI3', 'FAR1', 'EWSR1', 'RP11-116K4.1',
                     'MAOA', 'OR9Q2', 'LDHC', 'MTRR', 'IL36G', 'MUS81', 'MS4A7', 'AC010731.3',
                     'GCNT3', 'RAB26', 'IFT122', 'MORC3', 'RP11-526N18.1', 'SRR', 'EIF3B', 'PTPRA',
                     'CTD-2014E2.6', 'TRGV3', 'TRAFD1', 'BBS1', 'ABCC3', 'POLR2J', 'EGFL8.1', 'DECR1',
                     'IL20RB', 'METTL21D', 'C1QTNF6', 'CTD-2354A18.1', 'HOOK2', 'NAT9', 'EIF4E2',
                     'PABPN1', 'C16orf13', 'LRRC53', 'TRGV7', 'DDX19A', 'CHTOP', 'ZNF707', 'BCAS3',
                     'WDR46', 'RP11-467D18.2', 'ART3'}

        self.assertSetEqual(res_ids, known_ids)


if __name__ == '__main__':
    unittest.main()
