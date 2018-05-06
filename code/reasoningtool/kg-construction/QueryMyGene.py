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

import mygene
import sys
import requests
import json
import requests_cache

class QueryMyGene:
    def __init__(self, debug=False):
        self.mygene_obj = mygene.MyGeneInfo()
        self.debug = debug

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
        try:
            res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
                                        fields='uniprot', verbose=False)
        except requests.exceptions.HTTPError:
            print('HTTP error for querying gene symbol to uniprot in mygene: ' + gene_symbol, file=sys.stderr)
            res = None            
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
        try:
            res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human',
                                        fields='symbol', verbose=False)
        except requests.exceptions.HTTPError:
            print('HTTP error for querying uniprot to gene symbol mygene: ' + uniprot_id, file=sys.stderr)
            res = None
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
        try:
            res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human',
                                        fields='entrezgene', verbose=False)
        except requests.exceptions.HTTPError:
            print('HTTP error for querying uniprot-to-entrezgene in mygene: ' + uniprot_id, file=sys.stderr)
            res = None
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

    def convert_gene_symbol_to_entrez_gene_ID(self, gene_symbol):
        res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
                                    fields='entrezgene', verbose=False)
        entrez_ids = set()
        if len(res) > 0:
            entrez_ids = set()
            for hit in res['hits']:
                entrez_id = hit.get('entrezgene', None)
                if entrez_id is not None:
                    entrez_ids.add(entrez_id)
        return entrez_ids

    def convert_entrez_gene_ID_to_mirbase_ID(self, entrez_gene_id):
        assert type(entrez_gene_id) == int
        res = self.mygene_obj.query('entrezgene:' + str(entrez_gene_id), species='human', fields='miRBase', verbose=False)
        mirbase_id = set()
        if len(res) > 0:
            res_hits = res.get("hits", None)
            if res_hits is not None and type(res_hits) == list:
                for hit in res_hits:
                    res_mirbase_id = hit.get("miRBase", None)
                    if res_mirbase_id is not None:
                        mirbase_id.add(res_mirbase_id)
                    else:
                        print("QueryMyGene.convert_entrez_gene_ID_to_mirbase_ID result missing miRBase field where it was expected; Entrez Gene ID: " +
                              entrez_gene_id, file=sys.stderr)
        return mirbase_id

    def get_gene_ontology_ids_bp_for_uniprot_id(self, uniprot_id):
        assert type(uniprot_id) == str
        res = dict()
        try:
            q_res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human', fields='go', verbose=False)
        except requests.exceptions.HTTPError:
            print("HTTP error in mygene_obj.query for GO fields for query string: " + uniprot_id, file=sys.stderr)
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

    def get_gene_ontology_ids_bp_for_entrez_gene_id(self, entrez_gene_id):
        assert type(entrez_gene_id) == int
        q_res = self.mygene_obj.query('entrezgene:' + str(entrez_gene_id), species='human', fields='go', verbose=False)
        res = dict()
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

    def get_cui(self, gene_id):
        if gene_id.startswith('NCBIGene:'):
            gene_id = int(gene_id.split(':')[1])
            res = self.mygene_obj.getgene(gene_id, fields = 'umls', verbose = False)
            cui_res = res.get('umls', None)
            cuis = None
            if cui_res is not None:
                cuis = [cui_res['cui']]
            return cuis
        elif gene_id.startswith('UniProt:'):
            res = self.mygene_obj.query(gene_id, fields = 'umls', verbose = False)
            if res is not None:
                cuis = []
                if 'hits' in res.keys():
                    for hit in res['hits']:
                        if 'umls' in hit.keys():
                            cuis.append(hit['umls']['cui'])
                if len(cuis) >0:
                    return cuis
                else:
                    return None
        return None



if __name__ == '__main__':
    mg = QueryMyGene()
    print(mg.convert_entrez_gene_ID_to_mirbase_ID(407053))
    print(mg.get_gene_ontology_ids_bp_for_entrez_gene_id(406991))
    print(mg.get_gene_ontology_ids_bp_for_uniprot_id('Q05925'))
    print(mg.convert_uniprot_id_to_gene_symbol('Q05925'))
    print(mg.convert_gene_symbol_to_uniprot_id('A2M'))
    print(mg.convert_gene_symbol_to_uniprot_id('A1BG'))
    print(mg.convert_gene_symbol_to_entrez_gene_ID('MIR96'))
    print(mg.convert_gene_symbol_to_uniprot_id("HMOX1"))
    print(mg.convert_gene_symbol_to_uniprot_id('RAD54B'))
    print(mg.convert_gene_symbol_to_uniprot_id('NS2'))
    print(mg.convert_uniprot_id_to_gene_symbol("P09601"))
    print(mg.convert_uniprot_id_to_entrez_gene_ID("P09601"))
    print(mg.convert_uniprot_id_to_entrez_gene_ID("XYZZY"))
