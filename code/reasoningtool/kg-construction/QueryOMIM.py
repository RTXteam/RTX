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

import requests
import CachedMethods


class QueryOMIM:
    API_KEY = '1YCxuN7PRHyrpuZnO7F5gQ'
    API_BASE_URL = 'http://api.omim.org/api'

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
        res = requests.get(url, cookies=self.cookie)
        assert 200 == res.status_code
        return res

    @CachedMethods.register
    def disease_mim_to_gene_symbols_and_uniprot_ids(self, mim_id):
        """for a given MIM ID for a genetic disease (as input), returns a dict of of gene symbols and UniProt IDs
        {gene_symbols: [gene_symbol_list], uniprot_ids: [uniprot_ids_list]}

        :param mim_id: a string OMIMD ID (of the form 'OMIM:605543')
        :returns: a ``dict`` with two keys; ``gene_symbols`` and ``uniprot_ids``; the entry for each of the
        keys is a ``set`` containing the indicated identifiers (or an empty ``set`` if no such identifiers are available)
        """
        assert type(mim_id) == str
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

if __name__ == '__main__':
    qo = QueryOMIM()
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:166710'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:129905'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:603903'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:613074'))
    print(qo.disease_mim_to_gene_symbols_and_uniprot_ids('OMIM:603918'))  # test issue 1
