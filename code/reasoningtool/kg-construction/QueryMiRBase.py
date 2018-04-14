""" This module is the definition of class QueryMiRBase. It is designed to connect
to a microRNA databse named miRBase. It can query miRBase for gene symbol, miRNA
ids etc.
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
import lxml.html
import functools
import CachedMethods


class QueryMiRBase:
    API_BASE_URL = 'http://www.mirbase.org/cgi-bin'

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryMiRBase.API_BASE_URL + "/" + handler + "?" + url_suffix
#        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        assert status_code == 200
        return res

    @staticmethod
    @CachedMethods.register
    def convert_mirbase_id_to_mir_gene_symbol(mirbase_id):
        assert mirbase_id != ''
        res = QueryMiRBase.send_query_get('mirna_entry.pl', 'acc=' + mirbase_id)
        ret_ids = set()
        res_tree = lxml.html.fromstring(res.content)
        res_list = res_tree.xpath("//a[contains(text(), 'HGNC:')]")
        res_symbol = None
        if len(res_list) > 0:
            res_symbol = res_list[0].text.replace('HGNC:','')
        return res_symbol

    @staticmethod
    @CachedMethods.register
    def convert_mirbase_id_to_mature_mir_ids(mirbase_id):
        assert mirbase_id != ''
        res = QueryMiRBase.send_query_get('mirna_entry.pl', 'acc=' + mirbase_id)
        ret_ids = set()
        res_tree = lxml.html.fromstring(res.content)
        ## Try to find a suitable REST API somewhere, to replace this brittle HTML page scraping:
        hrefs = [x.get('href').split('=')[1] for x in res_tree.xpath("/html//table/tr/td/a[contains(@href, 'MIMAT')]")]

        return(set(hrefs))

if __name__ == '__main__':
    print(QueryMiRBase.convert_mirbase_id_to_mature_mir_ids('MI0014240'))
    print(QueryMiRBase.convert_mirbase_id_to_mature_mir_ids('MI0000098'))
    print(QueryMiRBase.convert_mirbase_id_to_mature_mir_ids('MIMAT0027666'))
    print(QueryMiRBase.convert_mirbase_id_to_mir_gene_symbol('MIMAT0027666'))
    # print(QueryMiRBase.convert_mirbase_id_to_mir_gene_symbol('MIMAT0027666X'))
