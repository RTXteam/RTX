__author__ = 'Finn Womack'
__copyright__ = 'Oregon State University'
__credits__ = ['Finn Womack']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

# import requests
import urllib
import math
import sys
import time
import os
from io import StringIO
import re
import pandas
# import CachedMethods
# import requests_cache
import lxml.html as lh
from lxml.html import fromstring

try:
    from cache_control_helper import CacheControlHelper
except ImportError:
    insert_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)) + "/../kg-construction/")
    sys.path.insert(0, insert_dir)
    from cache_control_helper import CacheControlHelper


class QueryUMLS:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'https://uts-ws.nlm.nih.gov/rest'
    Ticket_URL = 'https://utslogin.nlm.nih.gov'
    auth_endpoint = "/cas/v1/api-key"
    api_key = '98b04ff2-e69d-4177-889b-d5fbcf8a9114'

    @staticmethod
    def get_ticket_gen():
        # params = {'username': self.username,'password': self.password}
        params = {'apikey': QueryUMLS.api_key}
        h = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": "python"}
        requests = CacheControlHelper()
        r = requests.post(QueryUMLS.Ticket_URL + QueryUMLS.auth_endpoint, data=params, headers=h)
        response = fromstring(r.text)
        ## extract the entire URL needed from the HTML form (action attribute) returned - looks similar to https://utslogin.nlm.nih.gov/cas/v1/tickets/TGT-36471-aYqNLN2rFIJPXKzxwdTNC5ZT7z3B3cTAKfSc5ndHQcUxeaDOLN-cas
        ## we make a POST call to this URL in the getst method
        tgt = response.xpath('//form/@action')[0]
        return tgt

    @staticmethod
    def get_single_ticket(tgt):
        params = {'service': "http://umlsks.nlm.nih.gov"}
        h = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": "python"}
        requests = CacheControlHelper()
        r = requests.post(tgt, data=params, headers=h)
        st = r.text
        return st

    @staticmethod
    def send_query_get(handler, st):
        url_str = QueryUMLS.API_BASE_URL + '/' + handler + '&ticket=' + st
        requests = CacheControlHelper()
        try:
            res = requests.get(url_str, headers={'accept': 'application/json'}, timeout=QueryUMLS.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print('HTTP timeout in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except requests.exceptions.ConnectionError:
            print('HTTP connection error in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
            res = None
        return res

    @staticmethod
    def get_synonyms_from_string(string, tgt):
        st = QueryUMLS.get_single_ticket(tgt)
        query = '/search/current?string=' + string + '&pageSize=10000'
        r = QueryUMLS.send_query_get(query, st)
        if r is not None:
            return [a['name'] for a in r.json()['result']['results']]
        else:
            return None

    @staticmethod
    def get_cuis_from_string(string, tgt):
        st = QueryUMLS.get_single_ticket(tgt)
        query = '/search/current?string=' + string + '&pageSize=10000'
        r = QueryUMLS.send_query_get(query, st)
        if r is not None:
            ans = [a['ui'] for a in r.json()['result']['results']]
            if ans[0] == 'NONE':
                return None
            return ans
        else:
            return None

    @staticmethod
    def get_cui_from_string_precision(string, tgt):
        cui = None
        st = QueryUMLS.get_single_ticket(tgt)
        query = '/search/current?string=' + string + '&pageSize=10000'
        r = QueryUMLS.send_query_get(query, st)
        if r is not None:
            res_json = r.json()
            if 'result' in res_json.keys():
                if 'results' in res_json['result'].keys():
                    for res_obj in res_json['result']['results']:
                        if 'name' in res_obj.keys() and 'ui' in res_obj.keys():
                            if res_obj['name'].lower() == string.lower():
                                cui = res_obj['ui']
                    if cui is None and len(res_json['result']['results']) > 0:
                        cui = res_json['result']['results'][0]['ui']
        return cui

    @staticmethod
    def get_cuis_from_curie(curie, tgt):
        map_dict = {'HP' : 'HPO',
                    'OMIM':'OMIM',
                    'GO':'GO'
                    }
        cui = None
        st = QueryUMLS.get_single_ticket(tgt)
        if curie.split(':')[0] not in map_dict.keys():
            return None
        else:
            db = map_dict[curie.split(':')[0]]
            if db == 'OMIM':
                curie = curie.split(':')[1]
        query = '/search/2018AA?string=' + curie + '&sabs=' + db + '&searchType=exact&inputType=sourceUi'
        print(query)
        r = QueryUMLS.send_query_get(query, st)
        if r is not None:
            ans = [a['ui'] for a in r.json()['result']['results']]
            if ans[0] == 'NONE':
                return None
            return ans
        else:
            return None
        return cui

if __name__ == '__main__':
    # pass
    tgt = QueryUMLS.get_ticket_gen()
    print(QueryUMLS.get_cuis_from_string('log15', tgt))
    print(QueryUMLS.get_cuis_from_string('pain', tgt))
    print(QueryUMLS.get_cui_from_string_precision('pain', tgt))
    print(QueryUMLS.get_cui_from_string_precision('Influenza-like symptoms', tgt))
