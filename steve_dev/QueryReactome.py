import requests
import sys

class QueryReactome:

    API_BASE_URL = 'https://reactome.org/ContentService'

    @staticmethod
    def send_query_get(handler, url_suffix):  ## :WEIRD: Reactome REST API GET syntax doesn't want a question mark in the URL
        url_str = QueryReactome.API_BASE_URL + "/" + handler + "/" + url_suffix
        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        assert 200 == res.status_code
        return res

    # @staticmethod
    # def uniprot_to_reactome_entity_id(uniprot_id):
    #     handler = 'data/complexes/UniProt'
    #     url_suffix = uniprot_id
    #     res = QueryReactome.send_query_get(handler, url_suffix)
    #     return res.json()

    @staticmethod
    def test():
        print(QueryReactome.uniprot_to_reactome_entity_id("P68871"))
        
if "--test" in set(sys.argv):
    QueryReactome.test()
        
