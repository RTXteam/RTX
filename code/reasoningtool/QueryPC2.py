""" This module defines the class QueryPC2. It is designed to connect to
http://www.pathwaycommons.org/pc2, querying uniprot id and pathway id mutually.
"""

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Zheng Liu', 'Yao Yao']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests

class QueryPC2:
    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://www.pathwaycommons.org/pc2'

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryPC2.API_BASE_URL + "/" + handler + "?" + url_suffix
#        print(url_str)
        try:
            res = requests.get(url_str, timeout=QueryPC2.TIMEOUT_SEC)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryPC2 for URL: ' + url, file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res

    @staticmethod
    def pathway_id_to_uniprot_ids(pathway_reactome_id):
        query_str = "uri=http://identifiers.org/reactome/" + pathway_reactome_id + "&format=TXT"
        res = QueryPC2.send_query_get("get", query_str)
        res_set = set()
        if res is not None:
            start_capturing = False
            res_text = res.text
            for line_str in res_text.splitlines():
                if start_capturing:
                    unification_xref_str = line_str.split("\t")[3]
                    unification_xref_namevals = unification_xref_str.split(";")
                    for unification_xref_nameval in unification_xref_namevals:
                        unification_xref_nameval_fields = unification_xref_nameval.split(":")
                        if unification_xref_nameval_fields[0] == "uniprot knowledgebase":
                            res_set.add(unification_xref_nameval_fields[1])
                            if line_str.split("\t")[0] == "PARTICIPANT":
                                start_capturing = True
        return res_set

    @staticmethod
    def uniprot_id_to_reactome_pathways(uniprot_id):
        res = QueryPC2.send_query_get("search.json", "q=" + uniprot_id + "&type=pathway")
        res_dict = res.json()
        if res is not None:
            search_hits = res_dict["searchHit"]
            pathway_list = [item.split("http://identifiers.org/reactome/")[1] for i in range(0, len(search_hits)) for item
                            in search_hits[i]["pathway"]]
        return set(pathway_list)


if __name__ == '__main__':
    print(QueryPC2.uniprot_id_to_reactome_pathways("P68871"))
    print(QueryPC2.pathway_id_to_uniprot_ids("R-HSA-2168880"))
