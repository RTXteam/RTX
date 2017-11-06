import requests
import sys

class QueryDisont:

    API_BASE_URL = 'http://www.disease-ontology.org/api'

    @staticmethod
    def send_query_get(handler, url_suffix): 
        url_str = QueryDisont.API_BASE_URL + "/" + handler + "/" + url_suffix
        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        assert res.status_code == 200
        return res
    
    @staticmethod
    def query_disont_to_child_disonts(disont_id):
        res_json = QueryDisont.send_query_get('metadata', 'DOID:' + str(disont_id)).json()
        disease_children_list = res_json["children"]
        return set([int(disease_child_list[1].split(':')[1]) for disease_child_list in disease_children_list])

    @staticmethod
    def test():
        print(QueryDisont.query_disont_to_child_disonts(12365))
        
if "--test" in set(sys.argv):
    QueryDisont.test()
    
