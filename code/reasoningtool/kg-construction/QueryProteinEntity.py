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


class QueryProteinEntity:

    @staticmethod
    def get_protein_entity(protein_id):
        mg = mygene.MyGeneInfo()
        result_str = str(mg.query(protein_id, fields='all'))
        #   replace double quotes with single quotes
        return result_str.replace('"', "'")

if __name__ == '__main__':
    obj = QueryProteinEntity.get_protein_entity("UniProt:P53814")
    print(obj)