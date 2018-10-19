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


class QueryKEGG:
    TIMEOUT_SEC = 120
    API_BASE_URL = ' http://rest.kegg.jp'
    GENOME_API_BASE_URL = ' http://rest.genome.jp'
    HANDLER_MAP = {
        'map_kegg_compound_to_enzyme_commission_ids': 'link/ec/{id}',
        'map_kegg_compound_to_pub_chem_id': 'conv/pubchem/compound:{id}',
        'map_kegg_compound_to_hmdb_id': 'link/hmdb/{id}'
    }

    @staticmethod
    def __access_api(handler, base_url=API_BASE_URL):

        url = base_url + '/' + handler

        try:
            res = requests.get(url, timeout=QueryKEGG.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryKEGG for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryKEGG for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
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
        if res is not None and res != '':
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
        if res is not None and res != '':
            tab_pos = res.find('\t')
            if tab_pos > 0:
                result_id = res[tab_pos+9:len(res)-1]
        return result_id

    @staticmethod
    def map_kegg_compound_to_hmdb_id(kegg_id):
        """ map kegg compond id to HMDB ids

        Args:
            kegg_id (str): The ID of the kegg compound, e.g., "KEGG:C00022"

        Returns:
            id (str): the HMDB ID, or None if no id is retrieved
        """
        if not isinstance(kegg_id, str):
            return None
        kegg_id = kegg_id[5:]
        handler = QueryKEGG.HANDLER_MAP['map_kegg_compound_to_hmdb_id'].format(id=kegg_id)
        res = QueryKEGG.__access_api(handler, QueryKEGG.GENOME_API_BASE_URL)
        if res is not None and res != '':
            tab_pos = res.find('\t')
            res = res[tab_pos + 6:]
            tab_pos = res.find('\t')
            res = res[:tab_pos]
            if len(res) == 9:
                res = res[:4] + "00" + res[4:]
            return res
        else:
            return None

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
    print(QueryKEGG.map_kegg_compound_to_pub_chem_id('KEGG:C00022'))

    print("test map_kegg_compound_to_hmdb_id")
    print(QueryKEGG.map_kegg_compound_to_hmdb_id('KEGG:C00022'))
    print(QueryKEGG.map_kegg_compound_to_hmdb_id('KEGG:C19033'))
    print(QueryKEGG.map_kegg_compound_to_hmdb_id('KEGG:C11686'))
    print(QueryKEGG.map_kegg_compound_to_hmdb_id('GO:2342343'))
    print(QueryKEGG.map_kegg_compound_to_hmdb_id('43'))
    print(QueryKEGG.map_kegg_compound_to_hmdb_id('C11686'))
    print(QueryKEGG.map_kegg_compound_to_hmdb_id(10000))
