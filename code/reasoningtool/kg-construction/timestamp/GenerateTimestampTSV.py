""" This module defines the class GenerateTimestampTSV.
It is written to generate a timestamp TSV.
"""

__author__ = ""
__copyright__ = ""
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

from QueryChEMBLTimestamp import QueryChEMBLTimestamp
from QueryDisGeNETTimestamp import QueryDisGeNETTimestamp
from QueryDrugBankTimestamp import QueryDrugBankTimestamp
from QueryKEGGTimestamp import QueryKEGGTimestamp
from QueryOMIMTimestamp import QueryOMIMTimestamp
from QueryDGIdbTimestamp import QueryDGIdbTimestamp
from QueryDisontTimestamp import QueryDisontTimestamp
from QueryEBIOLSTimestamp import QueryEBIOLSTimestamp
from QueryHMDBTimestamp import QueryHMDBTimestamp
from QueryMiRBaseTimestamp import QueryMiRBaseTimestamp
from QueryMyChemTimestamp import QueryMyChemTimestamp
from QueryMyGeneTimestamp import QueryMyGeneTimestamp
from QueryNCBITimestamp import QueryNCBITimestamp
from QueryReactomeTimestamp import QueryReactomeTimestamp


class GenerateTimestampTSV:
    FILE_NAME = 'timestamp.tsv'

    @staticmethod
    def __process_all_databases():
        content = ''
        #   ChEMBL
        content += 'ChEMBL\t' + QueryChEMBLTimestamp.get_timestamp() + '\n'
        #   DisGeNET
        content += 'DisGeNET\t' + QueryDisGeNETTimestamp.get_timestamp() + '\n'\
        #   Disont
        content += 'Disont\t' + QueryDisontTimestamp.get_timestamp() + '\n'
        #   DrugBank
        content += 'DrugBank\t' + QueryDrugBankTimestamp.get_timestamp() + '\n'
        #   DGIdb
        content += 'DGIdb\t' + QueryDGIdbTimestamp.get_timestamp() + '\n'
        #   EBIOLS
        content += 'EBIOLS\t' + QueryEBIOLSTimestamp.get_timestamp() + '\n'
        #   HMDB
        content += 'HMDB\t' + QueryHMDBTimestamp.get_timestamp() + '\n'
        #   KEGG
        content += 'KEGG\t' + QueryKEGGTimestamp.get_timestamp() + '\n'
        #   MiRBase
        content += 'MiRBase\t' + QueryMiRBaseTimestamp.get_timestamp() + '\n'
        #   MyChem
        content += 'MyChem\t' + QueryMyChemTimestamp.get_timestamp() + '\n'
        #   MyGene
        content += 'MyGene\t' + QueryMyGeneTimestamp.get_timestamp() + '\n'
        #   NCBI
        content += 'NCBI\t' + QueryNCBITimestamp.get_timestamp() + '\n'
        #   OMIM
        content += 'OMIM\t' + QueryOMIMTimestamp.get_timestamp() + '\n'
        #   Reactome
        content += 'Reactome\t' + QueryReactomeTimestamp.get_timestamp() + '\n'


        try:
            wf = open(GenerateTimestampTSV.FILE_NAME, 'w+')
            wf.write(content)
            wf.close()
        except OSError as err:
            print("writing file, OS error: {0}".format(err))

    @staticmethod
    def generate_timestamp_tsv():
        GenerateTimestampTSV.__process_all_databases()


if __name__ == '__main__':
    GenerateTimestampTSV.generate_timestamp_tsv()