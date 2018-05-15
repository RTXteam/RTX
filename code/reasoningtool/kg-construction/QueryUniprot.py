""" This module defines the class QueryUniprot which connects to APIs at
http://www.uniprot.org/uploadlists/, querying reactome pathways from uniprot id.

*   map_enzyme_commission_id_to_uniprot_ids(ec_id)

    Description:
        map enzyme commission id to UniProt ids

    Args:
        ec_id (str): enzyme commission id, e.g., "ec:1.4.1.17"

    Returns:
        ids (set): a set of the enzyme commission ids, or empty set if no UniProt id can be obtained or the response
                    status code is not 200.

"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import requests
import requests_cache
import CachedMethods
import sys
import urllib.parse

# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')


class QueryUniprot:
    API_BASE_URL = "http://www.uniprot.org/uploadlists/"
    TIMEOUT_SEC = 120
    HANDLER_MAP = {
        'map_enzyme_commission_id_to_uniprot_ids': 'uniprot/?query=({id})&format=tab&columns=id'
    }

    @staticmethod
    @CachedMethods.register
    def uniprot_id_to_reactome_pathways(uniprot_id):
        """returns a ``set`` of reactome IDs of pathways associated with a given string uniprot ID

        :param uniprot_id: a ``str`` uniprot ID, like ``"P68871"``
        :returns: a ``set`` of string Reactome IDs
        """

        payload = { 'from':   'ACC',
                    'to':     'REACTOME_ID',
                    'format': 'tab',
                    'query':  uniprot_id }
        contact = "stephen.ramsey@oregonstate.edu"
        header = {'User-Agent': 'Python %s' % contact}
        try:
            res = requests.post(QueryUniprot.API_BASE_URL, data=payload, headers=header)
        except requests.exceptions.Timeout:
            print(QueryUniprot.API_BASE_URL, file=sys.stderr)
            print('Timeout in QueryUniprot for URL: ' + QueryUniprot.API_BASE_URL, file=sys.stderr)
            return None
        except requests.exceptions.ChunkedEncodingError:
            print(QueryUniprot.API_BASE_URL, file=sys.stderr)
            print('ChunkedEncodingError for URL: ' + QueryUniprot.API_BASE_URL, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(QueryUniprot.API_BASE_URL, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + QueryUniprot.API_BASE_URL, file=sys.stderr)
            return None
#        assert 200 == res.status_code
        res_set = set()
        for line in res.text.splitlines():
            field_str = line.split("\t")[1]
            if field_str != "To":
                res_set.add(field_str)
        return res_set

    @staticmethod
    def __access_api(handler):

        api_base_url = 'http://www.uniprot.org'
        url = api_base_url + '/' + handler
        #print(url)
        contact = "stephen.ramsey@oregonstate.edu"
        header = {'User-Agent': 'Python %s' % contact}
        try:
            res = requests.get(url, timeout=QueryUniprot.TIMEOUT_SEC, headers=header)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryUniprot for URL: ' + url, file=sys.stderr)
            return None
        except requests.exceptions.ChunkedEncodingError:
            print(url, file=sys.stderr)
            print('ChunkedEncodingError for URL: ' + QueryUniprot.API_BASE_URL, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.text

    @staticmethod
    def map_enzyme_commission_id_to_uniprot_ids(ec_id):
        res_set = set()
        if not isinstance(ec_id, str):
            return res_set
        ec_id_encoded = urllib.parse.quote_plus(ec_id)
        handler = QueryUniprot.HANDLER_MAP['map_enzyme_commission_id_to_uniprot_ids'].format(id=ec_id_encoded)
        res = QueryUniprot.__access_api(handler)
        if res is not None:
            res = res[res.find('\n')+1:]
            for line in res.splitlines():
                res_set.add(line)
        return res_set


if __name__ == '__main__':
    print(QueryUniprot.uniprot_id_to_reactome_pathways("P68871"))
    print(QueryUniprot.uniprot_id_to_reactome_pathways("Q16621"))
    print(QueryUniprot.uniprot_id_to_reactome_pathways("P09601"))
    print(CachedMethods.cache_info())

    print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.4.1.17"))  # small results
    print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.3.1.110")) # empty result
    print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.2.1.22"))  # large results
    print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:4.4.1.xx"))  # fake id
    print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("R-HSA-1912422"))   # wrong id
