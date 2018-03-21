__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests
import urllib.parse
import sys
import time

class QueryEBIOLS:
    TIMEOUT_SEC = 120
    API_BASE_URL = "https://www.ebi.ac.uk/ols/api/ontologies"

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryEBIOLS.API_BASE_URL + '/' + handler + "/" + url_suffix
#        print(url_str)
        try:
            res = requests.get(url_str, headers={'Accept': 'application/json'}, timeout=QueryEBIOLS.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print('HTTP timeout in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        except requests.exceptions.ConnectionError:
            print('HTTP connection error in QueryNCBIeUtils.py; URL: ' + url_str, file=sys.stderr)
            time.sleep(1)  ## take a timeout because NCBI rate-limits connections
            return None
        status_code = res.status_code
        if status_code != 200:
            print('HTTP response status code: ' + str(status_code) + ' for URL:\n' + url_str, file=sys.stderr)
            res = None
        return res

    def get_mesh_id_for_uberon_id(self, uberon_curie_id):
        uberon_iri = "http://purl.obolibrary.org/obo/" + uberon_curie_id.replace(":","_")
        uberon_iri_double_encoded = urllib.parse.quote_plus(urllib.parse.quote_plus(uberon_iri))
        res = QueryEBIOLS.send_query_get("uberon/terms/", uberon_iri_double_encoded)
        ret_list = list()
        if res is not None:
            res_json = res.json()
            res_annotation = res_json.get("annotation", None)
            if res_annotation is not None:
                db_x_refs = res_annotation.get("database_cross_reference", None)
                if db_x_refs is not None:
                    ret_list = [mesh_id for mesh_id in db_x_refs if "MESH:D" in mesh_id]
        return set(ret_list)
                                         
if __name__ == "__main__":
#    print(QueryEBIOLS.send_query_get("uberon/terms/" + urllib.parse.quote_plus(urllib.parse.quote_plus("http://purl.obolibrary.org/obo/UBERON_0002107")), ""))
    print(QueryEBIOLS.get_mesh_id_for_uberon_id("UBERON:0002107"))
    
    
