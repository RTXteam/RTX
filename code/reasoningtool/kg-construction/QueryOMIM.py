""" This module defines the class QueryOMIM.
It is written to connect to http://api.omim.org/api, which converts omim id to
gene symbol and uniprot id.
"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import sys
import requests
# import CachedMethods
import requests_cache

class QueryOMIM:
    API_KEY = '1YCxuN7PRHyrpuZnO7F5gQ'
    API_BASE_URL = 'https://api.omim.org/api'
    TIMEOUT_SEC = 120
 
    def __init__(self):
        url = QueryOMIM.API_BASE_URL + "/apiKey"
        session_data = {'apiKey': QueryOMIM.API_KEY,
                        'format': 'json'}
        r = requests.post(url, data=session_data)
        assert 200 == r.status_code
        self.cookie = r.cookies

    def send_query_get(self, omim_handler, url_suffix):
        url = "{api_base_url}/{omim_handler}?{url_suffix}&format=json".format(api_base_url=QueryOMIM.API_BASE_URL,
                                                                              omim_handler=omim_handler,
                                                                              url_suffix=url_suffix)
#        print(url)
        try:
            res = requests.get(url, cookies=self.cookie)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print("Timeout in QueryOMIM for URL: " + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryOMIM for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print("Status code " + str(status_code) + " for URL: " + url, file=sys.stderr)
            return None
        return res

    # @CachedMethods.register
    def disease_mim_to_gene_symbols_and_uniprot_ids(self, mim_id):
        """for a given MIM ID for a genetic disease (as input), returns a dict of of gene symbols and UniProt IDs
        {gene_symbols: [gene_symbol_list], uniprot_ids: [uniprot_ids_list]}

        :param mim_id: a string OMIMD ID (of the form 'OMIM:605543')
        :returns: a ``dict`` with two keys; ``gene_symbols`` and ``uniprot_ids``; the entry for each of the
        keys is a ``set`` containing the indicated identifiers (or an empty ``set`` if no such identifiers are available)
        """
        # assert type(mim_id) == str
        if not isinstance(mim_id, str):
            return {'gene_symbols': set(), 'uniprot_ids': set()}
        mim_num_str = mim_id.replace('OMIM:','')
        omim_handler = "entry"
        url_suffix = "mimNumber=" + mim_num_str + "&include=geneMap,externalLinks&exclude=text"
        r = self.send_query_get(omim_handler, url_suffix)
        result_dict = r.json()
#        print(result_dict)
        result_entry = result_dict["omim"]["entryList"][0]["entry"]
        external_links = result_entry.get('externalLinks', None)
        uniprot_ids = []
        gene_symbols = []
        if external_links is not None:
            uniprot_ids_str = external_links.get("swissProtIDs", None)
            if uniprot_ids_str is not None:
                uniprot_ids = uniprot_ids_str.split(",")
            else:
                phenotype_map_list = result_entry.get("phenotypeMapList", None)
                if phenotype_map_list is not None:
                    gene_symbols = [phenotype_map_list[i]["phenotypeMap"]["geneSymbols"].split(", ")[0] for i in
                                    range(0, len(phenotype_map_list))]
        return {'gene_symbols': set(gene_symbols),
                'uniprot_ids': set(uniprot_ids)}
    
    def disease_mim_to_description(self, mim_id):
        # assert type(mim_id) == str
        if not isinstance(mim_id, str):
            return "None"
        mim_num_str = mim_id.replace('OMIM:', '')
        omim_handler = "entry"
        url_suffix = "mimNumber=" + mim_num_str + "&include=text:description"
        r = self.send_query_get(omim_handler, url_suffix)
        if r is None:
            return "None"
        result_dict = r.json()
        # print(result_dict)
        result_entry = result_dict["omim"]["entryList"][0]["entry"]
        res_description = "None"
        text_section_list = result_entry.get('textSectionList', None)
        if text_section_list is not None and len(text_section_list) > 0:
            res_description_dict = text_section_list[0].get("textSection", None)
            if res_description_dict is not None:
                text_section_content = res_description_dict.get("textSectionContent", None)
                if text_section_content is not None:
                    res_description = text_section_content
        return res_description

if __name__ == '__main__':

    qo = QueryOMIM()
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:145270'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:601351'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:248260'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:608670'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:184400'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:100200'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:111360'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:250300'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:142700'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:312500'))
    # print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:166710'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:129905'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:603903'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:613074'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:603918'))  # test issue 1
    print(qo.disease_mim_to_description('OMIM:100100'))
    print(qo.disease_mim_to_description('OMIM:614747'))  # no textSectionContent field
    print(qo.disease_mim_to_description('OMIM:61447'))  # wrong ID
    print(qo.disease_mim_to_description(614747))
