''' This module defines the class QueryProteinEntity. QueryProteinEntity class is designed
to query protein entity from mygene library. The
available methods include:

    get_protein_entity : query protein properties by ID
    get_microRNA_entity : query micro properties by ID

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
# import requests_cache
import json
import sys

from cache_control_helper import CacheControlHelper

class QueryMyGeneExtended:

    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://mygene.info/v3'
    HANDLER_MAP = {
        'query': 'query',
        'gene': 'gene'
    }

    @staticmethod
    def __access_api(handler, url_suffix, params=None, return_raw=False):

        requests = CacheControlHelper()
        if url_suffix:
            url = QueryMyGeneExtended.API_BASE_URL + '/' + handler + '?' + url_suffix
        else:
            url = QueryMyGeneExtended.API_BASE_URL + '/' + handler
        headers = {'user-agent': "mygene.py/%s python-requests/%s" % ("1.0.0", "1.0.0"), 'Accept': 'application/json'}
        try:
            res = requests.get(url, params=params, timeout=QueryMyGeneExtended.TIMEOUT_SEC, headers=headers)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryMyGeneExtended for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryMyGeneExtended for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        if return_raw:
            return res.text
        else:
            return res.json()

    @staticmethod
    def get_protein_entity(protein_id):
        # mg = mygene.MyGeneInfo()
        # results = str(mg.query(protein_id.replace('UniProtKB', 'UniProt'), fields='all', return_raw='True', verbose=False))

        handler = QueryMyGeneExtended.HANDLER_MAP['query']
        # url_suffix = "q=" + protein_id.replace('UniProtKB', 'UniProt') + "&fields=all"
        params = {'q': protein_id.replace('UniProtKB', 'UniProt'), 'fields': 'all'}
        results = str(QueryMyGeneExtended.__access_api(handler, None, params=params, return_raw=True))

        result_str = 'None'
        if len(results) > 100:
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def get_microRNA_entity(microrna_id):
        # mg = mygene.MyGeneInfo()
        # results = str(mg.query(microrna_id.replace('NCBIGene', 'entrezgene'), fields='all', return_raw='True', verbose=False))

        handler = QueryMyGeneExtended.HANDLER_MAP['query']
        # url_suffix = "q=" + microrna_id.replace('NCBIGene', 'entrezgene') + "&fields=all"
        params = {'q': microrna_id.replace('NCBIGene', 'entrezgene'), 'fields': 'all'}
        results = str(QueryMyGeneExtended.__access_api(handler, None, params=params, return_raw=True))

        result_str = 'None'
        if len(results) > 100:
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def get_protein_desc(protein_id):
        result_str = QueryMyGeneExtended.get_protein_entity(protein_id)
        desc = "None"
        if result_str != "None":
            result_dict = json.loads(result_str)
            if "hits" in result_dict.keys():
                if len(result_dict["hits"]) > 0:
                    if "summary" in result_dict["hits"][0].keys():
                        desc = result_dict["hits"][0]["summary"]
        return desc

    @staticmethod
    def get_microRNA_desc(protein_id):
        result_str = QueryMyGeneExtended.get_microRNA_entity(protein_id)
        desc = "None"
        if result_str != "None":
            result_dict = json.loads(result_str)
            if "hits" in result_dict.keys():
                if len(result_dict["hits"]) > 0:
                    if "summary" in result_dict["hits"][0].keys():
                        desc = result_dict["hits"][0]["summary"]
        return desc

if __name__ == '__main__':

    def save_to_test_file(filename, key, value):
        f = open(filename, 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('tests/query_test_data.json', 'UniProtKB:O60884', QueryMyGeneExtended.get_protein_entity("UniProtKB:O60884"))
    save_to_test_file('tests/query_test_data.json', 'NCBIGene:100847086', QueryMyGeneExtended.get_microRNA_entity("NCBIGene: 100847086"))
    save_to_test_file('tests/query_desc_test_data.json', 'UniProtKB:O60884', QueryMyGeneExtended.get_protein_desc("UniProtKB:O60884"))
    save_to_test_file('tests/query_desc_test_data.json', 'UniProtKB:O608840', QueryMyGeneExtended.get_protein_desc("UniProtKB:O608840"))
    save_to_test_file('tests/query_desc_test_data.json', 'NCBIGene:100847086', QueryMyGeneExtended.get_microRNA_desc("NCBIGene:100847086"))
    save_to_test_file('tests/query_desc_test_data.json', 'NCBIGene:1008470860', QueryMyGeneExtended.get_microRNA_desc("NCBIGene:1008470860"))
    # print(QueryMyGeneExtended.get_protein_desc("UniProtKB:O60884"))
    # print(QueryMyGeneExtended.get_microRNA_desc("NCBIGene:100847086"))
    print(QueryMyGeneExtended.get_protein_desc("P05451"))
