''' This module defines the class QueryProteinEntity. QueryProteinEntity class is designed
to query protein entity from mygene library
'''

__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import mygene


class QueryMyGene:

    @staticmethod
    def get_protein_entity(protein_id):
        mg = mygene.MyGeneInfo()
        result_str = str(mg.query(protein_id, fields='all'))
        #   replace double quotes with single quotes
        result_str = result_str.replace('"', "'")
        if len(result_str) > 100:
            return result_str
        else:
            return "UNKNOWN"

    @staticmethod
    def get_microRNA_entity(protein_id):
        mg = mygene.MyGeneInfo()
        result_str = str(mg.query(protein_id.replace('NCBIGene', 'entrezgene'), fields='all'))
        #   replace double quotes with single quotes
        result_str = result_str.replace('"', "'")
        if len(result_str) > 100:
            return result_str
        else:
            return "UNKNOWN"

if __name__ == '__main__':
    print(QueryMyGene.get_protein_entity("UniProt:P53814"))
    print(QueryMyGene.get_microRNA_entity("NCBIGene:100616298"))