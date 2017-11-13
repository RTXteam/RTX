import requests
import lxml.html

class QueryMiRBase:
    API_BASE_URL = 'http://www.mirbase.org/cgi-bin'

    @staticmethod
    def send_query_get(handler, url_suffix): 
        url_str = QueryMiRBase.API_BASE_URL + "/" + handler + "?" + url_suffix
        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        status_code = res.status_code
        assert status_code == 200
        return res


    
    @staticmethod
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
    def convert_mirbase_id_to_mature_mir_ids(mirbase_id):
        assert mirbase_id != ''
        res = QueryMiRBase.send_query_get('mirna_entry.pl', 'acc=' + mirbase_id)
        ret_ids = set()
        res_tree = lxml.html.fromstring(res.content)
        ## Try to find a suitable REST API somewhere, to replace this brittle HTML page scraping:
        for mature_sequence_element in res_tree.xpath("/html/body/table[*]/tr/td/h2[contains(text(),'Mature sequence')]"):
            ret_ids.add(mature_sequence_element.text.split('Mature sequence ')[1].replace('\n',''))
        return(ret_ids)

    def test():
#        print(QueryMiRBase.convert_mirbase_id_to_mature_mir_ids('MI0000098'))
        print(QueryMiRBase.convert_mirbase_id_to_mature_mir_ids('MIMAT0027666'))
        print(QueryMiRBase.convert_mirbase_id_to_mir_gene_symbol('MIMAT0027666'))
        print(QueryMiRBase.convert_mirbase_id_to_mir_gene_symbol('MIMAT0027666X'))
if __name__ == '__main__':
    QueryMiRBase.test()
     
