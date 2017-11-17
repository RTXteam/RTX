import requests
import lxml.etree


class QueryMiRGate:
    API_BASE_URL = 'http://mirgate.bioinfo.cnio.es/ResT/API/human'
    TIMEOUT_SEC = 60
    
    @staticmethod
    def send_query_get(handler, url_suffix):  
        url_str = QueryMiRGate.API_BASE_URL + "/" + handler + "/" + url_suffix
#        print(url_str)
        try:
            res = requests.get(url_str, headers={'accept': 'application/json'},
                               timeout=QueryMiRGate.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print("Timeout in QueryMiRGate for URL: " + url_str)
            return None
        status_code = res.status_code
        if status_code != 200:
            print("Status code " + status_code + " for url: " + url_str)
            return None
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
    print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0016853')) # for issue #25
    print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0018979'))
    print(QueryMiRGate.get_microrna_ids_that_regulate_gene_symbol('HMOX1'))
    print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0019885'))
