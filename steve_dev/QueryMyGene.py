import mygene

class QueryMyGene:
    def __init__(self):
        self.mygene_obj = mygene.MyGeneInfo()

    def convert_gene_symbol_to_uniprot_id(self, gene_symbol):
        res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
                           fields='uniprot')
        uniprot_id = None
        if len(res) > 0:
            uniprot_id = set([hit["uniprot"]["Swiss-Prot"] for hit in res["hits"]])
            return uniprot_id
    
