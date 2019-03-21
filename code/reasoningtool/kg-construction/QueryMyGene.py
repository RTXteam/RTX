""" This module defines the class QueryMyGene.
QueryMyGene is written to query gene annotation information via python package
mygene. It can convert among gene symbol, uniprot id, entrez gene id, mirbase id.
"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

# import mygene
import sys
# import requests
import json
# import requests_cache

from cache_control_helper import CacheControlHelper


class QueryMyGene:
    def __init__(self, debug=False):
        # self.mygene_obj = mygene.MyGeneInfo()
        self.debug = debug

    ONT_NAME_TO_SIMPLE_NODE_TYPE = {'BP': 'biological_process',
                                    'MF': 'molecular_function',
                                    'CC': 'cellular_component'}

    TIMEOUT_SEC = 120
    API_BASE_URL = 'http://mygene.info/v3'
    HANDLER_MAP = {
        'query': 'query',
        'gene': 'gene'
    }

    @staticmethod
    def __access_api(handler, url_suffix, params=None, return_raw=False):

        requests = CacheControlHelper()
        if url_suffix:
            url = QueryMyGene.API_BASE_URL + '/' + handler + '?' + url_suffix
        else:
            url = QueryMyGene.API_BASE_URL + '/' + handler
        headers = {'user-agent': "mygene.py/%s python-requests/%s" % ("1.0.0", "1.0.0"), 'Accept': 'application/json'}
        try:
            res = requests.get(url, params=params, timeout=QueryMyGene.TIMEOUT_SEC, headers=headers)
        except requests.exceptions.Timeout:
            print(url, file=sys.stderr)
            print('Timeout in QueryMyGene for URL: ' + url, file=sys.stderr)
            return None
        except KeyboardInterrupt:
            sys.exit(0)
        except BaseException as e:
            print(url, file=sys.stderr)
            print('%s received in QueryMyGene for URL: %s' % (e, url), file=sys.stderr)
            return None
        status_code = res.status_code
        if status_code != 200:
            print(url, file=sys.stderr)
            print('Status code ' + str(status_code) + ' for url: ' + url, file=sys.stderr)
            return None
        if return_raw:
            return res.text
        else:
            return res.json()

    @staticmethod
    def unnest(lst, skip_type):
        """
        To unnest a list like `["foo", ["bar", "baz"]]` to `["foo", "bar", "baz"]`.
        Elements of `skip_type` will be leaf as is.
        """
        def generate_elements(lst, skip_type):
            for e in lst:
                if isinstance(e, skip_type):
                    yield e
                else:
                    yield from e

        return list(generate_elements(lst, skip_type))

    def convert_gene_symbol_to_uniprot_id(self, gene_symbol):
        # try:
        #     res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
        #                                 fields='uniprot', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print('HTTP error for querying gene symbol to uniprot in mygene: ' + gene_symbol, file=sys.stderr)
        #     res = None

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=symbol:" + gene_symbol + "&species=human&fields=uniprot"
        res = QueryMyGene.__access_api(handler, url_suffix)

        uniprot_ids_set = set()
        if res is not None and len(res) > 0:
            uniprot_ids_list = []
            for hit in res['hits']:
                uniprot_hit = hit.get("uniprot", None)
                if uniprot_hit is not None:
                    uniprot_id = uniprot_hit.get("Swiss-Prot", None)
                    if uniprot_id is not None:
                        uniprot_ids_list.append(uniprot_id)
                else:
                    if self.debug:
                        print("Could not find Uniprot ID for gene symbol: " + gene_symbol)
            uniprot_ids_list = QueryMyGene.unnest(uniprot_ids_list, str)
            uniprot_ids_set = set(uniprot_ids_list)
        return uniprot_ids_set

    def convert_uniprot_id_to_gene_symbol(self, uniprot_id):
        # try:
        #     res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human',
        #                                 fields='symbol', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print('HTTP error for querying uniprot to gene symbol mygene: ' + uniprot_id, file=sys.stderr)
        #     res = None

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=uniprot:" + uniprot_id + "&species=human&fields=symbol"
        res = QueryMyGene.__access_api(handler, url_suffix)

        gene_symbol = set()
        if res is not None and len(res) > 0:
            res_hits = res.get('hits', None)
            if res_hits is not None:
                gene_symbol = set([hit['symbol'] for hit in res_hits])
            else:
                print("QueryMyGene.convert_uniprot_id_to_gene_symbol: no \'hits\' result data for uniprot_id: " + uniprot_id, file=sys.stderr)
            gene_symbol = set([hit["symbol"] for hit in res_hits])
        return gene_symbol

    def convert_uniprot_id_to_entrez_gene_ID(self, uniprot_id):
        # requests = CacheControlHelper()
        # try:
        #     res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human',
        #                                 fields='entrezgene', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print('HTTP error for querying uniprot-to-entrezgene in mygene: ' + uniprot_id, file=sys.stderr)
        #     res = None

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=uniprot:" + uniprot_id + "&species=human&fields=entrezgene"
        res = QueryMyGene.__access_api(handler, url_suffix)

        entrez_ids = set()
        if res is not None and len(res) > 0:
            res_hits = res.get('hits', None)
            if res_hits is not None:
                for hit in res_hits:
                    entrez_id = hit.get('entrezgene', None)
                    if entrez_id is not None:
                        entrez_ids.add(entrez_id)
#                entrez_ids = set([hit["entrezgene"] for hit in res_hits])
            else:
                print("QueryMyGene.convert_uniprot_id_to_entrez_gene_ID: no \'hits\' result data for uniprot_id: " + uniprot_id, file=sys.stderr)
        return entrez_ids

    def convert_hgnc_gene_id_to_uniprot_id(self, hgnc_id):
        uniprot_ids = set()

        # requests = CacheControlHelper()
        # try:
        #     res = self.mygene_obj.query(hgnc_id, species='human',
        #                                 fields='uniprot', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print("HTTP error in mygene_obj.query for query string: " + hgnc_id, file=sys.stderr)
        #     return uniprot_ids

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=" + hgnc_id + "&species=human&fields=uniprot"
        res = QueryMyGene.__access_api(handler, url_suffix)

        if res is not None and len(res) > 0:
            for hit in res['hits']:
                uniprot_id_dict = hit.get('uniprot', None)
                if uniprot_id_dict is not None:
                    uniprot_id = uniprot_id_dict.get('Swiss-Prot', None)
                    if uniprot_id is not None:
                        if type(uniprot_id) == str:
                            uniprot_ids.add(uniprot_id)
                        else:
                            uniprot_ids.union(uniprot_id)
        return uniprot_ids
    
    def convert_gene_symbol_to_entrez_gene_ID(self, gene_symbol):
        entrez_ids = set()

        # requests = CacheControlHelper()
        # try:
        #     res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
        #                                 fields='entrezgene', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print("HTTP error in mygene_obj.query for query string: " + gene_symbol, file=sys.stderr)
        #     return entrez_ids

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=symbol:" + gene_symbol + "&species=human&fields=entrezgene"
        res = QueryMyGene.__access_api(handler, url_suffix)

        if res is not None and len(res) > 0:
            entrez_ids = set()
            for hit in res['hits']:
                entrez_id = hit.get('entrezgene', None)
                if entrez_id is not None:
                    entrez_ids.add(entrez_id)
        return entrez_ids

    def convert_entrez_gene_id_to_uniprot_id(self, entrez_gene_id):
        assert type(entrez_gene_id) == int
        uniprot_id = set()

        # requests = CacheControlHelper()
        # try:
        #     res = self.mygene_obj.query('entrezgene:' + str(entrez_gene_id), species='human', fields='uniprot', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print("HTTP error in mygene_obj.query for query string: " + entrez_gene_id, file=sys.stderr)
        #     return uniprot_id

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=entrezgene:" + str(entrez_gene_id) + "&species=human&fields=uniprot"
        res = QueryMyGene.__access_api(handler, url_suffix)

        if res is not None and len(res) > 0:
            res_hits = res.get("hits", None)
            if res_hits is not None and type(res_hits) == list:
                for hit in res_hits:
                    res_uniprot_id_dict = hit.get("uniprot", None)
                    if res_uniprot_id_dict is not None:
                        res_uniprot_id = res_uniprot_id_dict.get("Swiss-Prot", None)
                        if res_uniprot_id is not None:
                            if type(res_uniprot_id) == str:
                                uniprot_id.add(res_uniprot_id)
                            else:
                                if type(res_uniprot_id) == list:
                                    for uniprot_id_item in res_uniprot_id:
                                        uniprot_id.add(uniprot_id_item)
        return uniprot_id
    
    def convert_entrez_gene_ID_to_mirbase_ID(self, entrez_gene_id):
        assert type(entrez_gene_id) == int
        mirbase_id = set()

        # requests = CacheControlHelper()
        # try:
        #     res = self.mygene_obj.query('entrezgene:' + str(entrez_gene_id), species='human', fields='miRBase', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print("HTTP error in mygene_obj.query for query string: " + entrez_gene_id, file=sys.stderr)
        #     return mirbase_id

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=entrezgene:" + str(entrez_gene_id) + "&species=human&fields=miRBase"
        res = QueryMyGene.__access_api(handler, url_suffix)

        if res is not None and len(res) > 0:
            res_hits = res.get("hits", None)
            if res_hits is not None and type(res_hits) == list:
                for hit in res_hits:
                    res_mirbase_id = hit.get("miRBase", None)
                    if res_mirbase_id is not None:
                        mirbase_id.add(res_mirbase_id)
                    else:
                        print("QueryMyGene.convert_entrez_gene_ID_to_mirbase_ID result missing miRBase field where it was expected; Entrez Gene ID: " +
                              str(entrez_gene_id), file=sys.stderr)
        return mirbase_id

    def get_gene_ontology_ids_bp_for_uniprot_id(self, uniprot_id):
        assert type(uniprot_id) == str
        res = dict()

        # requests = CacheControlHelper()
        # try:
        #     q_res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human', fields='go', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print("HTTP error in mygene_obj.query for query string: " + uniprot_id, file=sys.stderr)
        #     return res

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=uniprot:" + uniprot_id + "&species=human&fields=go"
        q_res = QueryMyGene.__access_api(handler, url_suffix)

        if q_res is None:
            return res

        q_res_hits = q_res.get('hits', None)
        if q_res_hits is not None:
            if type(q_res_hits) == list and len(q_res_hits) > 0:
                for q_res_hit in q_res_hits:
                    if type(q_res_hit) == dict:
                        q_res_go = q_res_hit.get('go', None)
                        if q_res_go is not None:
                            q_res_bp = q_res_go.get('BP', None)
                            if q_res_bp is not None:
                                if type(q_res_bp) == list and len(q_res_bp) > 0:
                                    res_add = {item["id"]: item["term"] for item in q_res_bp}
                                    res.update(res_add)
        return res
    
    def get_gene_ontology_ids_for_uniprot_id(self, uniprot_id):
        assert type(uniprot_id) == str
        res = dict()

        # requests = CacheControlHelper()
        # try:
        #     q_res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human', fields='go', verbose=False)
        # except requests.exceptions.HTTPError:
        #     print("HTTP error in mygene_obj.query for query string: " + uniprot_id, file=sys.stderr)
        #     return res

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=uniprot:" + uniprot_id + "&species=human&fields=go"
        q_res = QueryMyGene.__access_api(handler, url_suffix)

        if q_res is None:
            return res

        q_res_hits = q_res.get('hits', None)
        if q_res_hits is not None:
            if type(q_res_hits) == list and len(q_res_hits) > 0:
                for q_res_hit in q_res_hits:
                    if type(q_res_hit) == dict:
                        q_res_go = q_res_hit.get('go', None)
                        if q_res_go is not None:
                            for ont_name, ont_dict_list in q_res_go.items():
                                ont_name_simple_node_type = self.ONT_NAME_TO_SIMPLE_NODE_TYPE[ont_name]
                                for ont_dict in ont_dict_list:
                                    if type(ont_dict) == dict:
                                        term = ont_dict.get('term', None)
                                        id = ont_dict.get('id', None)
                                        res.update({id: {'term': term,
                                                         'ont': ont_name_simple_node_type}})
        return res

    def get_gene_ontology_ids_bp_for_entrez_gene_id(self, entrez_gene_id):
        res = dict()
        assert type(entrez_gene_id) == int
        # q_res = self.mygene_obj.query('entrezgene:' + str(entrez_gene_id), species='human', fields='go', verbose=False)

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=entrezgene:" + str(entrez_gene_id) + "&species=human&fields=go"
        q_res = QueryMyGene.__access_api(handler, url_suffix)

        if q_res is None:
            return res

        q_res_hits = q_res.get('hits', None)
        if q_res_hits is not None:
            if type(q_res_hits) == list and len(q_res_hits) > 0:
                for q_res_hit in q_res_hits:
                    if type(q_res_hit) == dict:
                        q_res_go = q_res_hit.get('go', None)
                        if q_res_go is not None:
                            q_res_bp = q_res_go.get('BP', None)
                            if q_res_bp is not None:
                                if type(q_res_bp) == list and len(q_res_bp) > 0:
                                    res_add = {item["id"]: item["term"] for item in q_res_bp}
                                    res.update(res_add)
        return res

    def uniprot_id_is_human(self, uniprot_id_str):
        # res_json = self.mygene_obj.query("uniprot:" + uniprot_id_str, species="human", verbose=False)

        handler = QueryMyGene.HANDLER_MAP['query']
        url_suffix = "q=uniprot:" + uniprot_id_str + "&species=human"
        res_json = QueryMyGene.__access_api(handler, url_suffix)

        if res_json is None:
            return False

        hits = res_json.get("hits", None)
        return hits is not None and len(hits) > 0

    def get_cui(self, gene_id):
        if gene_id.startswith('NCBIGene'):
            gene_id = int(gene_id.split(':')[1])
            # res = self.mygene_obj.getgene(gene_id, fields='umls', verbose=False)

            handler = QueryMyGene.HANDLER_MAP['gene'] + '/' + str(gene_id)
            url_suffix = 'fields=umls'
            res = QueryMyGene.__access_api(handler, url_suffix)

            if res is not None:
                cui_res = res.get('umls', None)
            else:
                cui_res = None
            cuis = None
            if cui_res is not None:
                cuis = [cui_res['cui']]
            return cuis
        elif gene_id.startswith('UniProt'):
            uni_id = 'uniprot:' + gene_id.split(':')[1]
            # res = self.mygene_obj.query(uni_id, fields='umls', verbose=False)

            handler = QueryMyGene.HANDLER_MAP['query']
            url_suffix = "q=" + uni_id + "&fields=umls"
            res = QueryMyGene.__access_api(handler, url_suffix)

            if res is not None:
                cuis = []
                if 'hits' in res.keys():
                    for hit in res['hits']:
                        if 'umls' in hit.keys():
                            cuis.append(hit['umls']['cui'])
                if len(cuis) > 0:
                    return cuis
                else:
                    return None
        return None

    @staticmethod
    def get_protein_entity(protein_id):
        # mg = mygene.MyGeneInfo()
        # results = str(mg.query(protein_id.replace('UniProtKB', 'UniProt'), fields='all', return_raw='True', verbose=False))

        handler = QueryMyGene.HANDLER_MAP['query']
        # url_suffix = "q=" + protein_id.replace('UniProtKB', 'UniProt') + "&fields=all"
        params = {'q': protein_id.replace('UniProtKB', 'UniProt'), 'fields': 'all'}
        results = str(QueryMyGene.__access_api(handler, None, params=params, return_raw=True))

        result_str = 'None'
        if len(results) > 100:
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    @staticmethod
    def get_microRNA_entity(microrna_id):
        # mg = mygene.MyGeneInfo()
        # results = str(mg.query(microrna_id.replace('NCBIGene', 'entrezgene'), fields='all', return_raw='True', verbose=False))

        handler = QueryMyGene.HANDLER_MAP['query']
        # url_suffix = "q=" + microrna_id.replace('NCBIGene', 'entrezgene') + "&fields=all"
        params = {'q': microrna_id.replace('NCBIGene', 'entrezgene'), 'fields': 'all'}
        results = str(QueryMyGene.__access_api(handler, None, params=params, return_raw=True))

        result_str = 'None'
        if len(results) > 100:
            json_dict = json.loads(results)
            result_str = json.dumps(json_dict)
        return result_str

    def get_protein_desc(self, protein_id):
        if not isinstance(protein_id, str):
            return "None"
        result_str = self.get_protein_entity(protein_id)
        desc = "None"
        if result_str != "None":
            result_dict = json.loads(result_str)
            if "hits" in result_dict.keys():
                if len(result_dict["hits"]) > 0:
                    if "summary" in result_dict["hits"][0].keys():
                        desc = result_dict["hits"][0]["summary"]
        return desc

    def get_microRNA_desc(self, microrna_id):
        if not isinstance(microrna_id, str):
            return "None"
        result_str = self.get_microRNA_entity(microrna_id)
        desc = "None"
        if result_str != "None":
            result_dict = json.loads(result_str)
            if "hits" in result_dict.keys():
                if len(result_dict["hits"]) > 0:
                    if "summary" in result_dict["hits"][0].keys():
                        desc = result_dict["hits"][0]["summary"]
        return desc


    def get_protein_name(self, protein_id):
        if not isinstance(protein_id, str):
            return "None"
        result_str = self.get_protein_entity(protein_id)
        name = "None"
        if result_str != "None":
            result_dict = json.loads(result_str)
            if "hits" in result_dict.keys():
                if len(result_dict["hits"]) > 0:
                    if "name" in result_dict["hits"][0].keys():
                        name = result_dict["hits"][0]["name"]
        return name

if __name__ == '__main__':
    mg = QueryMyGene()
    print(mg.convert_gene_symbol_to_uniprot_id('A2M'))
    print(mg.convert_gene_symbol_to_uniprot_id('A1BG'))
    print(mg.convert_gene_symbol_to_uniprot_id("HMOX1"))
    print(mg.convert_gene_symbol_to_uniprot_id('RAD54B'))
    print(mg.convert_gene_symbol_to_uniprot_id('NS2'))
    print(mg.convert_uniprot_id_to_gene_symbol("P09601"))
    print(mg.convert_uniprot_id_to_gene_symbol('Q05925'))
    print(mg.convert_uniprot_id_to_gene_symbol('Q8NBZ7'))
    print(mg.convert_uniprot_id_to_entrez_gene_ID("P09601"))
    print(mg.convert_uniprot_id_to_entrez_gene_ID("XYZZY"))
    print(mg.convert_hgnc_gene_id_to_uniprot_id('HGNC:4944'))
    print(mg.convert_hgnc_gene_id_to_uniprot_id('HGNC:49440'))
    print(mg.convert_gene_symbol_to_entrez_gene_ID('MIR96'))
    print(mg.convert_entrez_gene_id_to_uniprot_id(9837))
    print(mg.convert_entrez_gene_ID_to_mirbase_ID(407053))
    print(mg.get_gene_ontology_ids_for_uniprot_id('Q05925'))
    print(mg.get_gene_ontology_ids_bp_for_entrez_gene_id(406991))
    print(mg.uniprot_id_is_human("P02794"))
    print(mg.uniprot_id_is_human("P10592"))
    print(mg.get_cui("NCBIGene:100847086"))
    print(mg.get_cui("UniProtKB:O60884"))


    def save_to_test_file(filename, key, value):
        f = open(filename, 'r+')
        try:
            json_data = json.load(f)
        except ValueError:
            json_data = {}
        f.seek(0)
        f.truncate()
        json_data[key] = value
        json.dump(json_data, f)
        f.close()

    save_to_test_file('tests/query_test_data.json', 'UniProtKB:O60884', mg.get_protein_entity("UniProtKB:O60884"))
    save_to_test_file('tests/query_test_data.json', 'NCBIGene:100847086', mg.get_microRNA_entity("NCBIGene:100847086"))
    print(mg.get_protein_desc("UniProtKB:O60884"))
    print(mg.get_protein_desc("UniProtKB:O608840"))
    print(mg.get_microRNA_desc("NCBIGene:100847086"))
    print(mg.get_microRNA_desc("NCBIGene:1008470860"))

    print(mg.get_protein_name("UniProtKB:P05231"))
    print(mg.get_protein_name("UniProtKB:Q8IW03"))