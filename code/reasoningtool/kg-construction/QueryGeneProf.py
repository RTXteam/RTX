""" This module defines the class QueryGeneProf.
QueryGeneProf is written to connect with geneprof.org, querying the functional
genomics data including transcription factor, gene symbol.
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
import sys
import os
import re

# configure requests package to use the "QueryCOHD.sqlite" cache
#requests_cache.install_cache('orangeboard')
# specifiy the path of orangeboard database
tmppath = re.compile(".*/RTX/")
dbpath = tmppath.search(os.path.realpath(__file__)).group(0) + 'data/orangeboard'
requests_cache.install_cache(dbpath)

class QueryGeneProf:
    API_BASE_URL = 'http://www.geneprof.org/GeneProf/api'
    TIMEOUT_SEC = 120

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryGeneProf.API_BASE_URL + "/" + handler + "/" + url_suffix
#        print(url_str)
        try:
            res = requests.get(url_str, timeout=QueryGeneProf.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print("Timeout in QueryGeneProf for URL: " + url_str, file=sys.stderr)
            return None
        except BaseException as e:
            print(url_str, file=sys.stderr)
            print('%s received in QueryGeneProf for URL: %s' % (e, url_str), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print("HTTP response status code: " + str(status_code) + " for URL:\n" + url_str, file=sys.stderr)
            res = None
        return res

    @staticmethod
    def gene_symbol_to_geneprof_ids(gene_symbol):
        handler = 'gene.info/gp.id'
        url_suffix = 'human/C_NAME/' + gene_symbol + '.json'
        res = QueryGeneProf.send_query_get(handler, url_suffix)
        ret_set = {}
        if res is not None:
            res_json = res.json()
            if res_json is not None and len(res_json) > 0:
                ret_set = set(res_json['ids'])
        return ret_set

    @staticmethod
    def geneprof_id_to_transcription_factor_gene_symbols(geneprof_id):
        handler = 'gene.info/regulation/binary/by.target'
        url_suffix = 'human/' + str(geneprof_id) + '.json?with-sample-info=true'
        res = QueryGeneProf.send_query_get(handler, url_suffix)
        tf_genes = set()
        if res is not None:
            res_json = res.json()
            if res_json is not None:
                sample_info_dict_list = [expt['sample'] for expt in res_json['values'] if expt['is_target']]
                for sample_info in sample_info_dict_list:
                    gene_symbol = sample_info.get("Gene", None)
                    if gene_symbol is not None:
                        tf_genes.add(gene_symbol)
        return tf_genes

    @staticmethod
    def gene_symbol_to_transcription_factor_gene_symbols(gene_symbol):
        geneprof_ids_set = QueryGeneProf.gene_symbol_to_geneprof_ids(gene_symbol)
        tf_gene_symbols = set()
        for geneprof_id in geneprof_ids_set:
            if geneprof_id is not None:
                tf_gene_symbols |= QueryGeneProf.geneprof_id_to_transcription_factor_gene_symbols(geneprof_id)
        return tf_gene_symbols


if __name__ == '__main__':
    QueryGeneProf.gene_symbol_to_geneprof_ids('xyzzy')
    print(QueryGeneProf.gene_symbol_to_transcription_factor_gene_symbols('HMOX1'))
    print(QueryGeneProf.gene_symbol_to_geneprof_ids('HMOX1'))
#    print(next(iter(hmox1_geneprof_id)))
#    print(QueryGeneProf.gene_symbol_to_transcription_factor_gene_symbols(str(next(iter(hmox1_geneprof_id)))))
