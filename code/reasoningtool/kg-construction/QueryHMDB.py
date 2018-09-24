''' This module defines the class QueryHMDB. QueryHMDB class is designed
to communicate with HMDB APIs (xml format) and their corresponding data sources. The
available methods include:

*   get_compound_desc(hmdb_url)

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


class QueryHMDB:
    TIMEOUT_SEC = 120

    @staticmethod
    def __access_api(url):

        url = url + '.xml'

        try:
            res = requests.get(url, timeout=QueryHMDB.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryHMDB for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryHMDB for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.text

    @staticmethod
    def get_compound_desc(hmdb_url):
        """
        Query the description of metabolite from HMDB
        Args:
            hmdb_url (str): the metabolite url of HMDB website
        Returns:
            res_desc (str): the description of metabolite
        """
        res_desc = "None"
        if not isinstance(hmdb_url, str):
            return res_desc
        results = QueryHMDB.__access_api(hmdb_url)
        if results is not None and results[:5] == "<?xml":
            obj = xmltodict.parse(results)
            if 'metabolite' in obj.keys():
                metabolite = obj['metabolite']
                if 'cs_description' in metabolite.keys():
                    res_desc = metabolite['cs_description']
        return res_desc

if __name__ == '__main__':
    # print(QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB0060288'))
    # print(QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB00021820'))
    # print(QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB0012194'))
    # print(QueryHMDB.get_compound_desc(820))
    print(QueryHMDB.get_compound_desc('http://www.hmdb.ca/metabolites/HMDB05049'))
