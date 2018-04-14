""" This module defines the class QueryMiRGate.
QueryMiRGate is written to connect with mirgate.bioinfo.cnio.es/ResT/API/human,
querying the information concerning regulation of microRNA.
"""

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Yao Yao', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'


import requests
import lxml.etree
import sys

class QueryMiRGate:
    API_BASE_URL = 'http://mirgate.bioinfo.cnio.es/ResT/API/human'
    TIMEOUT_SEC = 120

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryMiRGate.API_BASE_URL + "/" + handler + "/" + url_suffix
#        print(url_str)
        try:
            res = requests.get(url_str, headers={'accept': 'application/json'},
                               timeout=QueryMiRGate.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url_str, file=sys.stderr)
            print("Timeout in QueryMiRGate for URL: " + url_str, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url_str, file=sys.stderr)
            print("Status code " + str(status_code) + " for url: " + url_str, file=sys.stderr)
            return None
        if len(res.content) == 0:
            print(url_str, file=sys.stderr)
            print("Empty response from URL!", file=sys.stderr)
            res = None
        return res

    @staticmethod
    def get_microrna_ids_that_regulate_gene_symbol(gene_symbol):
        res = QueryMiRGate.send_query_get('gene_predictions', gene_symbol)
        if res is None:
            return set()
        root = lxml.etree.fromstring(res.content)
        res_elements = set(root.xpath('/miRGate/search/results/result[@mature_miRNA and ./agreement_value[text() > 2]]'))
        res_ids = set([res_element.xpath('@mature_miRNA')[0] for res_element in res_elements])
#        res_ids = set(root.xpath('/miRGate/search/results/result/@mature_miRNA'))
        res_ids.discard('')
        return res_ids

    @staticmethod
    def get_gene_symbols_regulated_by_microrna(microrna_id):
        '''returns the gene symbols that a given microrna (MIMAT ID) regulates

        '''
        assert 'MIMAT' in microrna_id
        res = QueryMiRGate.send_query_get('miRNA_predictions', microrna_id)
        if res is None:
            return set()
        root = lxml.etree.fromstring(res.content)
#        res_ids = set(root.xpath('/miRGate/search/results/result/@HGNC'))
        res_elements = root.xpath('/miRGate/search/results/result[@HGNC and ./agreement_value[text() > 2]]')
        res_ids = set([res_element.xpath('@HGNC')[0] for res_element in res_elements])
        res_ids.discard('')
        return res_ids

if __name__ == '__main__':
    print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0022742')) # for issue #30
    print(QueryMiRGate.get_microrna_ids_that_regulate_gene_symbol('HMOX1'))
    print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0016853')) # for issue #25
    print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0018979'))
    print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0019885'))
