import requests
import functools
import CachedMethods


class QueryGeneProf:
    API_BASE_URL = 'http://www.geneprof.org/GeneProf/api'

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryGeneProf.API_BASE_URL + "/" + handler + "/" + url_suffix
        print(url_str)
        res = requests.get(url_str)
        assert 200 == res.status_code
        return res

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def gene_symbol_to_geneprof_ids(gene_symbol):
        handler = 'gene.info/gp.id'
        url_suffix = 'human/C_NAME/' + gene_symbol + '.json'
        res = QueryGeneProf.send_query_get(handler, url_suffix).json()
        if len(res) > 0:
            ret_set = set(res['ids'])
        else:
            ret_set = {}
        return ret_set

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def geneprof_id_to_transcription_factor_gene_symbols(geneprof_id):
        handler = 'gene.info/regulation/binary/by.target'
        url_suffix = 'human/' + str(geneprof_id) + '.json?with-sample-info=true'
        res = QueryGeneProf.send_query_get(handler, url_suffix).json()
        sample_info_dict_list = [expt['sample'] for expt in res['values'] if expt['is_target']]
        tf_genes = set()
        for sample_info in sample_info_dict_list:
            gene_symbol = sample_info.get("Gene", None)
            if gene_symbol is not None:
                tf_genes.add(gene_symbol)
        return tf_genes

    @staticmethod
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def gene_symbol_to_transcription_factor_gene_symbols(gene_symbol):
        geneprof_ids_set = QueryGeneProf.gene_symbol_to_geneprof_ids(gene_symbol)
        tf_gene_symbols = set()
        for geneprof_id in geneprof_ids_set:
            if geneprof_id is not None:
                tf_gene_symbols |= QueryGeneProf.geneprof_id_to_transcription_factor_gene_symbols(geneprof_id)
        return tf_gene_symbols
    
    @staticmethod
    def test():
        QueryGeneProf.gene_symbol_to_geneprof_ids('xyzzy')
        hmox1_geneprof_id = QueryGeneProf.gene_symbol_to_geneprof_ids('HMOX1')
        print(next(iter(hmox1_geneprof_id)))
        print(QueryGeneProf.gene_symbol_to_transcription_factor_gene_symbols(str(next(iter(hmox1_geneprof_id)))))
        print(QueryGeneProf.gene_symbol_to_transcription_factor_gene_symbols('HMOX1'))
        
if __name__ == '__main__':
    QueryGeneProf.test()
