'''Parse the human phenotype ontology

'''

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Zheng Liu', 'Yao Yao']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import pronto
import json

class ParsePhenont:
    @staticmethod
    def get_name_id_dict(hp_obo_file_name):
        ont = pronto.Ontology(hp_obo_file_name)
        phenont_json = json.loads(ont.json)
        ret_dict = dict()
        for phenont_id in phenont_json.keys():
            name = phenont_json[phenont_id]['name']
            ret_dict[name]=phenont_id
        return ret_dict

if __name__ == '__main__':
    print(ParsePhenont.get_name_id_dict('../../hpo/hp.obo'))
    
