import requests
import sys


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

    def disease_mim_to_gene_symbols_and_uniprot_ids(self, mim_id):
        """for a given MIM ID for a genetic disease (as input), returns a dict of of gene symbols and UniProt IDs
        {gene_symbols: [gene_symbol_list], uniprot_ids: [uniprot_ids_list]}

        :param mim_id: an integer MIM number for a disease
        """
        assert type(mim_id) == int
        omim_handler = "entry"
        url_suffix = "mimNumber=" + str(mim_id) + "&include=geneMap,externalLinks&exclude=text"
        r = self.send_query_get(omim_handler, url_suffix)
        result_dict = r.json()
        result_entry = result_dict["omim"]["entryList"][0]["entry"]
        uniprot_ids = result_entry["externalLinks"]["swissProtIDs"].split(",")
        phenotype_map_list = result_entry["phenotypeMapList"]
        gene_symbols = [phenotype_map_list[i]["phenotypeMap"]["geneSymbols"].split(", ")[0] for i in
                        range(0, len(phenotype_map_list))]
        return {'gene_symbols': set(gene_symbols),
                'uniprot_ids': set(uniprot_ids)}

    @staticmethod
    def test():
        qo = QueryOMIM()
        res = qo.disease_mim_to_gene_symbols_and_uniprot_ids(603903)
        print(res)


if "--test" in set(sys.argv):
    QueryOMIM.test()
