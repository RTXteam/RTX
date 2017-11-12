import mygene
import functools
import CachedMethods


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

    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def convert_gene_symbol_to_uniprot_id(self, gene_symbol):
        res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
                                    fields='uniprot', verbose=False)
        uniprot_ids_set = set()
        if len(res) > 0:
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

    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def convert_uniprot_id_to_gene_symbol(self, uniprot_id):
        res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human',
                                    fields='symbol', verbose=False)
        gene_symbol = set()
        if len(res) > 0:
            gene_symbol = set([hit["symbol"] for hit in res["hits"]])
        return gene_symbol

    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def convert_uniprot_id_to_entrez_gene_ID(self, uniprot_id):
        res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human',
                                    fields='entrezgene', verbose=False)
        entrez_ids = set()
        if len(res) > 0:
            entrez_ids = set([hit["entrezgene"] for hit in res["hits"]])
        return entrez_ids

    def convert_gene_symbol_to_entrez_gene_ID(self, gene_symbol):
        res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
                                    fields='entrezgene', verbose=False)
        entrez_ids = set()
        if len(res) > 0:
            entrez_ids = set([hit['entrezgene'] for hit in res['hits']])
        return entrez_ids
    
    def test():
        mg = QueryMyGene()
        print(mg.convert_gene_symbol_to_entrez_gene_ID('MIR96'))
        print(mg.convert_gene_symbol_to_uniprot_id("HMOX1"))
        print(mg.convert_gene_symbol_to_uniprot_id('RAD54B'))
        print(mg.convert_gene_symbol_to_uniprot_id('NS2'))
        print(mg.convert_uniprot_id_to_gene_symbol("P09601"))
        print(mg.convert_uniprot_id_to_entrez_gene_ID("P09601"))
        
if __name__ == '__main__':
    QueryMyGene.test()
