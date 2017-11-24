""" This module is the definition of class QueryDisont. It is written to connect
 with disease-ontology to query disease ontology and mesh id of given disont_id.
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
import sys

class QueryDisont:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://www.disease-ontology.org/api'

    @staticmethod
    def send_query_get(handler, url_suffix):
        url = QueryDisont.API_BASE_URL + "/" + handler + "/" + url_suffix
#        print(url_str)
        try:
            res = requests.get(url, headers={'accept': 'application/json'}, timeout=QueryDisont.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryDisont for URL: ' + url, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None            
        return res

    @staticmethod
    def query_disont_to_child_disonts(disont_id):
        """for a disease ontology ID (including prefix "DOID:", with zero padding), return child DOIDs

        :param disont_id: string, like ``'DOID:14069'``
        :returns: ``set`` with keys as DOIDs
        """
        res = QueryDisont.send_query_get('metadata', disont_id)
        ret_set = set()
        if res is not None:
            res_json = res.json()
#        print(res_json)
            disease_children_list = res_json.get("children", None)
            if disease_children_list is not None:
                ret_set |= set([int(disease_child_list[1].split(':')[1]) for disease_child_list in disease_children_list])
        return ret_set
    
    @staticmethod
    def query_disont_to_label(disont_id):
        res = QueryDisont.send_query_get('metadata', disont_id)
        ret_label = ''
        if res is not None:
            res_json = res.json()
            ret_label = res_json.get('name', '')
        return ret_label

    @staticmethod
    def query_disont_to_child_disonts_desc(disont_id):
        """for a disease ontology ID (including prefix "DOID:", with zero padding), return child DOIDs

        :param disont_id: string, like ``'DOID:14069'``
        :returns: ``dict`` with keys as DOIDs and values as human-readable disease names
        """

        res = QueryDisont.send_query_get('metadata', disont_id)
        ret_dict = dict()
        if res is not None:
            res_json = res.json()
#        print(res_json)
            disease_children_list = res_json.get("children", None)
            if disease_children_list is not None:
                ret_dict = dict([[disease_child_list[1], disease_child_list[0]] for disease_child_list in disease_children_list])
        return ret_dict

    @staticmethod
    def query_disont_to_mesh_id(disont_id):
        """convert a disease ontology ID (including prefix "DOID:", with zero padding) to MeSH ID

        :param disont_id: string, like ``'DOID:14069'``
        """
        res = QueryDisont.send_query_get('metadata', disont_id)
        ret_set = set()
        if res is not None:
            res_json = res.json()
            xref_strs = res_json.get("xrefs", None)
            if xref_strs is not None:
                ret_set |= set([xref_str.split('MESH:')[1] for xref_str in xref_strs if 'MESH:' in xref_str])
        return ret_set

if __name__ == '__main__':
    print(QueryDisont.query_disont_to_label("DOID:0050741"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:9352"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:1837"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:10182"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:11712"))
    print(QueryDisont.query_disont_to_child_disonts_desc("DOID:9352"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:14069"))
    print(QueryDisont.query_disont_to_child_disonts_desc("DOID:12365"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:0050741"))
