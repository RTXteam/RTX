import requests
import lxml.etree

class QueryMiRGate:
    API_BASE_URL = 'http://mirgate.bioinfo.cnio.es/ResT/API/human'
    
    @staticmethod
    def send_query_get(handler, url_suffix):  
        url_str = QueryMiRGate.API_BASE_URL + "/" + handler + "/" + url_suffix
        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        assert status_code == 200
        return res

    @staticmethod
    def get_microrna_ids_that_regulate_gene_symbol(gene_symbol):
        res = QueryMiRGate.send_query_get('gene_predictions', gene_symbol)
        root = lxml.etree.fromstring(res.content)
        res_ids = set(root.xpath('/miRGate/search/results/result/@mature_miRNA'))
        res_ids.discard('')
        return res_ids

    @staticmethod
    def get_gene_symbols_regulated_by_microrna(microrna_id):
        '''returns the gene symbols that a given microrna (MIMAT ID) regulates
        
        '''
        assert 'MIMAT' in microrna_id
        res = QueryMiRGate.send_query_get('miRNA_predictions', microrna_id)
        root = lxml.etree.fromstring(res.content)
        res_ids = set(root.xpath('/miRGate/search/results/result/@HGNC'))
        return res_ids
    
    def test():
#        print(QueryMiRBase.convert_mirbase_id_to_mature_mir_ids('MI0000098'))
        print(QueryMiRGate.get_microrna_ids_that_regulate_gene_symbol('HMOX1'))
#        print(QueryMiRGate.get_gene_symbols_regulated_by_microrna('MIMAT0019885'))
        
if __name__ == '__main__':
    QueryMiRGate.test()
     
