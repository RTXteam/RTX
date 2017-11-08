import requests
import sys

class QueryDisont:

    API_BASE_URL = 'http://www.disease-ontology.org/api'

    @staticmethod
    def send_query_get(handler, url_suffix): 
        url_str = QueryDisont.API_BASE_URL + "/" + handler + "/" + url_suffix
#        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        assert res.status_code == 200
        return res
    
    @staticmethod
    def query_disont_to_child_disonts(disont_id):
        """for a disease ontology ID (including prefix "DOID:", with zero padding), return child DOIDs

        :param disont_id: string, like ``'DOID:14069'``
        :returns: ``set`` with keys as DOIDs
        """
        res_json = QueryDisont.send_query_get('metadata', disont_id).json()
#        print(res_json)
        disease_children_list = res_json.get("children", None)
        if disease_children_list is not None:
            return set([int(disease_child_list[1].split(':')[1]) for disease_child_list in disease_children_list])
        else:
            return set()

    @staticmethod
    def query_disont_to_child_disonts_desc(disont_id):
        """for a disease ontology ID (including prefix "DOID:", with zero padding), return child DOIDs

        :param disont_id: string, like ``'DOID:14069'``
        :returns: ``dict`` with keys as DOIDs and values as human-readable disease names
        """
   
        res_json = QueryDisont.send_query_get('metadata', disont_id).json()
#        print(res_json)
        disease_children_list = res_json.get("children", None)
        if disease_children_list is not None:
            return dict([[disease_child_list[1], disease_child_list[0]] for disease_child_list in disease_children_list])
        else:
            return dict()
         
    @staticmethod
    def query_disont_to_mesh_id(disont_id):
        """convert a disease ontology ID (including prefix "DOID:", with zero padding) to MeSH ID

        :param disont_id: string, like ``'DOID:14069'``
        """
        res_json = QueryDisont.send_query_get('metadata', disont_id).json()
        xref_strs = res_json["xrefs"]
        mesh_ids = set([xref_str.split('MESH:')[1] for xref_str in xref_strs if 'MESH:' in xref_str])
        return mesh_ids
        
    @staticmethod
    def test():
        print(QueryDisont.query_disont_to_mesh_id("DOID:14069"))
        print(QueryDisont.query_disont_to_child_disonts_desc("DOID:12365"))
        print(QueryDisont.query_disont_to_mesh_id("DOID:0050741"))
        
if __name__ == '__main__':
    QueryDisont.test()
    
