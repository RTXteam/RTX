''' This module defines the class QueryKEGG. QueryKEGG class is designed
to communicate with KEGG APIs and their corresponding data sources. The
available methods include:

*   map_kegg_compound_to_enzyme_commission_ids(kegg_id)
*   map_kegg_compound_to_pub_chem_id(kegg_id)

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

# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')


class QueryKEGG:
    TIMEOUT_SEC = 120
    API_BASE_URL = ' http://rest.kegg.jp'
    HANDLER_MAP = {
        'map_kegg_compound_to_enzyme_commission_ids': 'link/ec/{id}',
        'map_kegg_compound_to_pub_chem_id': 'conv/pubchem/compound:{id}'
    }

    @staticmethod
    def __access_api(handler):

        url = QueryKEGG.API_BASE_URL + '/' + handler

        try:
            res = requests.get(url, timeout=QueryKEGG.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryKEGG for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryKEGG for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.text

    @staticmethod
    def map_kegg_compound_to_enzyme_commission_ids(kegg_id):
        """ map kegg compond id to enzyme commission ids

        Args:
            kegg_id (str): The ID of the kegg compound, e.g., "KEGG:C00022"

        Returns:
            ids (set): a set of the enzyme commission ids, or empty set if no enzyme commission id can be obtained or the
                        response status code is not 200.
        """
        res_set = set()
        if not isinstance(kegg_id, str):
            return res_set
        kegg_id = kegg_id[5:]
        handler = QueryKEGG.HANDLER_MAP['map_kegg_compound_to_enzyme_commission_ids'].format(id=kegg_id)
        res = QueryKEGG.__access_api(handler)
        if res is not None:
            tab_pos = res.find('\t')
            while tab_pos != -1:
                return_pos = res.find('\n')
                ec_id = res[tab_pos+1:return_pos]
                res_set.add(ec_id)
                res = res[return_pos+1:]
                tab_pos = res.find('\t')
        return res_set

    @staticmethod
    def map_kegg_compound_to_pub_chem_id(kegg_id):
        """ map kegg compound id to PubChem id

        Args:
            kegg_id (str): The ID of the kegg compound, e.g., "KEGG:C00022"

        Returns:
            id (str): the PubChem ID, or None if no id is retrieved
        """
        result_id = None
        if not isinstance(kegg_id, str):
            return result_id
        kegg_id = kegg_id[5:]
        handler = QueryKEGG.HANDLER_MAP['map_kegg_compound_to_pub_chem_id'].format(id=kegg_id)
        res = QueryKEGG.__access_api(handler)
        if res is not None:
            tab_pos = res.find('\t')
            if tab_pos > 0:
                result_id = res[tab_pos+9:len(res)-1]
        return result_id


if __name__ == '__main__':
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00190'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00022'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00100'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('KEGG:C00200'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids('GO:2342343'))
    print(QueryKEGG.map_kegg_compound_to_enzyme_commission_ids(1000))

    print(QueryKEGG.map_kegg_compound_to_pub_chem_id('KEGG:C00190'))
    print(QueryKEGG.map_kegg_compound_to_pub_chem_id('KEGG:C00022'))
    print(QueryKEGG.map_kegg_compound_to_pub_chem_id('KEGG:C00100'))
    print(QueryKEGG.map_kegg_compound_to_pub_chem_id('KEGG:C00200'))
    print(QueryKEGG.map_kegg_compound_to_pub_chem_id('GO:2342343'))
    print(QueryKEGG.map_kegg_compound_to_pub_chem_id(1000))
