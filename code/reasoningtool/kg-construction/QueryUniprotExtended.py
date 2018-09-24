
''' This module defines the class QueryUniprotExtended. QueryUniprotExtended class is designed
to communicate with Uniprot APIs and their corresponding data sources. The
available methods include:

*   get_protein_name(protein_id)

    Description:
        search for protein name

    Args:
        protein_id (str): The ID of the protein entity, e.g., "UniProt:P01358"

    Returns:
        name (str): the name of the protein entity, or 'None' if no protein object can be obtained.
'''


__author__ = 'Deqing Qu'
__copyright__ = 'Oregon State University'
__credits__ = ['Deqing Qu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import requests_cache
import sys
import xmltodict


class QueryUniprotExtended:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://www.uniprot.org/uniprot'
    HANDLER_MAP = {
        'get_protein': '{id}.xml'
    }

    @staticmethod
    def __access_api(handler):

        url = QueryUniprotExtended.API_BASE_URL + '/' + handler
        print(url)
        try:
            res = requests.get(url, timeout=QueryUniprotExtended.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryUniprot for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryUniprot for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None

        return res.text

    @staticmethod
    def __get_entity(entity_type, entity_id):
        if entity_id[:10] == 'UniProtKB:':
            entity_id = entity_id[10:]
        handler = QueryUniprotExtended.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryUniprotExtended.__access_api(handler)
        entity = None
        if results is not None:
            obj = xmltodict.parse(results)
            if 'uniprot' in obj.keys():
                if 'entry' in obj['uniprot'].keys():
                    entity = obj['uniprot']['entry']
        return entity

    @staticmethod
    def get_protein_gene_symbol(entity_id):
        ret_symbol = ""
        entity_obj = QueryUniprotExtended.__get_entity("get_protein", entity_id)
        if entity_obj is not None:
            if 'gene' in entity_obj.keys():
                if "name" in entity_obj["gene"].keys():
                    gene_name_obj = entity_obj["gene"]["name"]
                    if not type(gene_name_obj) == list:
                        gene_name_obj = [ gene_name_obj ]
                    for name_dict in gene_name_obj:
                        #                        print(name_dict)
                        if "primary" in name_dict.values() and "#text" in name_dict.keys():
                            ret_symbol = name_dict["#text"]
        return ret_symbol
        
    @staticmethod
    def __get_name(entity_type, entity_id):
        entity_obj = QueryUniprotExtended.__get_entity(entity_type, entity_id)
        name = "None"
        if entity_obj is not None:
            if 'protein' in entity_obj.keys():
                if 'recommendedName' in entity_obj['protein'].keys():
                    if 'fullName' in entity_obj['protein']['recommendedName'].keys():
                        name = entity_obj['protein']['recommendedName']['fullName']
                        if isinstance(name, dict):
                            name = name['#text']
        return name

    @staticmethod
    def get_protein_name(protein_id):
        return QueryUniprotExtended.__get_name("get_protein", protein_id)

if __name__ == '__main__':
    print(QueryUniprotExtended.get_protein_gene_symbol('UniProtKB:P20848'))
    print(QueryUniprotExtended.get_protein_gene_symbol("UniProtKB:P01358"))
    print(QueryUniprotExtended.get_protein_gene_symbol("UniProtKB:Q96P88"))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:P01358'))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:P20848'))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:Q9Y471'))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:O60397'))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:Q8IZJ3'))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:Q7Z2Y8'))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:Q8IWN7'))
    print(QueryUniprotExtended.get_protein_name('UniProtKB:Q156A1'))
