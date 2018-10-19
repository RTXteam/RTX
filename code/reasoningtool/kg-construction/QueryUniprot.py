""" This module defines the class QueryUniprot which connects to APIs at
http://www.uniprot.org/uploadlists/, querying reactome pathways from uniprot id.

*   map_enzyme_commission_id_to_uniprot_ids(ec_id)

    Description:
        map enzyme commission id to UniProt ids

    Args:
        ec_id (str): enzyme commission id, e.g., "ec:1.4.1.17"

    Returns:
        ids (set): a set of the enzyme commission ids, or empty set if no UniProt id can be obtained or the response
                    status code is not 200.

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
import requests_cache
import CachedMethods
import sys
import urllib.parse
import xmltodict


class QueryUniprot:
    API_BASE_URL = "http://www.uniprot.org/uploadlists/"
    TIMEOUT_SEC = 120
    HANDLER_MAP = {
        'map_enzyme_commission_id_to_uniprot_ids': 'uniprot/?query=({id})&format=tab&columns=id',
        'get_protein': 'uniprot/{id}.xml'
    }

    @staticmethod
    @CachedMethods.register
    def uniprot_id_to_reactome_pathways(uniprot_id):
        """returns a ``set`` of reactome IDs of pathways associated with a given string uniprot ID

        :param uniprot_id: a ``str`` uniprot ID, like ``"P68871"``
        :returns: a ``set`` of string Reactome IDs
        """

        payload = { 'from':   'ACC',
                    'to':     'REACTOME_ID',
                    'format': 'tab',
                    'query':  uniprot_id }
        contact = "stephen.ramsey@oregonstate.edu"
        header = {'User-Agent': 'Python %s' % contact}
        try:
            url =QueryUniprot.API_BASE_URL
            res = requests.post(QueryUniprot.API_BASE_URL, data=payload, headers=header)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryUniprot for URL: ' + QueryUniprot.API_BASE_URL, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryUniprot for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(QueryUniprot.API_BASE_URL, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + QueryUniprot.API_BASE_URL, file=sys.stderr)
            return None
#        assert 200 == res.status_code
        res_set = set()
        for line in res.text.splitlines():
            field_str = line.split("\t")[1]
            if field_str != "To":
                res_set.add(field_str)
        return res_set

    @staticmethod
    def __access_api(handler):

        api_base_url = 'http://www.uniprot.org'
        url = api_base_url + '/' + handler
        #print(url)
        contact = "stephen.ramsey@oregonstate.edu"
        header = {'User-Agent': 'Python %s' % contact}
        try:
            res = requests.get(url, timeout=QueryUniprot.TIMEOUT_SEC, headers=header)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryUniprot for URL: ' + url, file=sys.stderr)
            return None
        except requests.exceptions.ChunkedEncodingError:
            print(url, file=sys.stderr)
            print('ChunkedEncodingError for URL: ' + url, file=sys.stderr)
            return None
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryUniprot for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        return res.text

    @staticmethod
    def map_enzyme_commission_id_to_uniprot_ids(ec_id):
        res_set = set()
        if not isinstance(ec_id, str):
            return res_set
        ec_id_encoded = urllib.parse.quote_plus(ec_id)
        handler = QueryUniprot.HANDLER_MAP['map_enzyme_commission_id_to_uniprot_ids'].format(id=ec_id_encoded)
        res = QueryUniprot.__access_api(handler)
        if res is not None:
            res = res[res.find('\n')+1:]
            for line in res.splitlines():
                res_set.add(line)
        return res_set

    @staticmethod
    def __get_entity(entity_type, entity_id):
        if entity_id[:10] == 'UniProtKB:':
            entity_id = entity_id[10:]
        handler = QueryUniprot.HANDLER_MAP[entity_type].format(id=entity_id)
        results = QueryUniprot.__access_api(handler)
        entity = None
        if results is not None:
            obj = xmltodict.parse(results)
            if 'uniprot' in obj.keys():
                if 'entry' in obj['uniprot'].keys():
                    entity = obj['uniprot']['entry']
        return entity

    @staticmethod
    def get_protein_gene_symbol(entity_id):
        ret_symbol = "None"
        if not isinstance(entity_id, str):
            return ret_symbol
        entity_obj = QueryUniprot.__get_entity("get_protein", entity_id)
        if entity_obj is not None:
            if 'gene' in entity_obj.keys():
                if "name" in entity_obj["gene"].keys():
                    gene_name_obj = entity_obj["gene"]["name"]
                    if not type(gene_name_obj) == list:
                        gene_name_obj = [gene_name_obj]
                    for name_dict in gene_name_obj:
                        #                        print(name_dict)
                        if "primary" in name_dict.values() and "#text" in name_dict.keys():
                            ret_symbol = name_dict["#text"]
        return ret_symbol

    @staticmethod
    def __get_name(entity_type, entity_id):
        entity_obj = QueryUniprot.__get_entity(entity_type, entity_id)
        name = "None"
        if entity_obj is not None:
            if 'protein' in entity_obj.keys():
                if 'recommendedName' in entity_obj['protein'].keys():
                    if 'fullName' in entity_obj['protein']['recommendedName'].keys():
                        name = entity_obj['protein']['recommendedName']['fullName']
                        if isinstance(name, dict):
                            name = name['#text']
        return name

    @staticmethod
    def get_protein_name(protein_id):
        if not isinstance(protein_id, str):
            return "None"
        return QueryUniprot.__get_name("get_protein", protein_id)

    @staticmethod
    def get_citeable_accession_for_accession(accession_number):
        res_acc = None
        res_tab = QueryUniprot.__access_api("uniprot/" + accession_number + ".tab")
        if res_tab is None:
            return res_acc
        res_lines = res_tab.splitlines()
        if len(res_lines) > 1:
            res_acc = res_lines[1].split("\t")[0]
        return res_acc

if __name__ == '__main__':
    print(QueryUniprot.get_citeable_accession_for_accession("P35354"))
    print(QueryUniprot.get_citeable_accession_for_accession("A8K802"))
    print(QueryUniprot.get_citeable_accession_for_accession("Q16876"))
    # print(QueryUniprot.uniprot_id_to_reactome_pathways("P68871"))
    # print(QueryUniprot.uniprot_id_to_reactome_pathways("Q16621"))
    # print(QueryUniprot.uniprot_id_to_reactome_pathways("P09601"))
    # print(CachedMethods.cache_info())
    # print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.4.1.17"))  # small results
    # print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.3.1.110")) # empty result
    # print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:1.2.1.22"))  # large results
    # print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("ec:4.4.1.xx"))  # fake id
    # print(QueryUniprot.map_enzyme_commission_id_to_uniprot_ids("R-HSA-1912422"))   # wrong id
    # print(QueryUniprot.get_protein_gene_symbol('UniProtKB:P20848'))
    # print(QueryUniprot.get_protein_gene_symbol("UniProtKB:P01358"))
    # print(QueryUniprot.get_protein_gene_symbol("UniProtKB:Q96P88"))
    # print(QueryUniprot.get_protein_name('UniProtKB:P01358'))
    # print(QueryUniprot.get_protein_name('UniProtKB:P20848'))
    # print(QueryUniprot.get_protein_name('UniProtKB:Q9Y471'))
    # print(QueryUniprot.get_protein_name('UniProtKB:O60397'))
    # print(QueryUniprot.get_protein_name('UniProtKB:Q8IZJ3'))
    # print(QueryUniprot.get_protein_name('UniProtKB:Q7Z2Y8'))
    # print(QueryUniprot.get_protein_name('UniProtKB:Q8IWN7'))
    # print(QueryUniprot.get_protein_name('UniProtKB:Q156A1'))
