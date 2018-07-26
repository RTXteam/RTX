""" This module defines the module QueryLilGIM. QueryLilGIM provides
a method for finding neighboring genes (in a distance space defined
by correlation similarity) for a set of query genes, based on gene
expression data that are stored in a Google BigQuery table. The search
for neighboring genes is based on correlation measurements computed
in a specific anatomical context (specified by the user of this module).

Based on an example Jupyter notebook provided here:
https://github.com/NCATS-Tangerine/cq-notebooks/blob/master/BigGIM/lilGIM%20and%20BigCLAM%20Examples.ipynb
"""

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Theo Knijnenburg', 'John Earls', 'David Palzer']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import urllib.request
import urllib.parse
# NOTE: this module *WILL NOT WORK* if you use requests package if caching via requests-cache is turned on
import json
import pandas
import time
import sys
import os
import functools

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../kg-construction')))  # Go up one level and look for it

from QueryEBIOLS import QueryEBIOLS
from QueryMyGene import QueryMyGene
import CachedMethods

class QueryLilGIM:
    BASE_URL = "http://biggim.ncats.io/api"
    ENDPOINT = "lilgim/query"
    DEFAULT_LIMIT = 100

    def __init__(self, limit=DEFAULT_LIMIT):
        self.limit = limit
        self.mg = QueryMyGene()

    @staticmethod
    def _get(endpoint, data={}, base_url=BASE_URL):
        post_params = urllib.parse.urlencode(data)
        url = '%s/%s?%s' % (base_url, endpoint, post_params)
        req = urllib.request.urlopen(urllib.request.Request(url, headers={'Accept': 'application/json'}))
#        print("Sent: GET %s?%s" % (req.request.url, req.request.body))
        return json.loads(req.read().decode())

    @staticmethod
    def _jprint(dct):
        print(json.dumps(dct, indent=2))

    @staticmethod
    def _wrapper(endpoint, data={}, base_url=BASE_URL):
        try:
            response = QueryLilGIM._get(endpoint, data, base_url)
#            QueryLilGIM._jprint(response)
        except BaseException as e:
            print(e, file=sys.stderr)
            if e.response.status_code == 400:
                QueryLilGIM._jprint(e.response.json(), file=sys.stderr)
                raise
        try:
            ctr = 1
            while True:
                query_status = QueryLilGIM._get('%s/status/%s' % (endpoint.split('/')[0],
                                                                  response['request_id'],))
#                QueryLilGIM._jprint(query_status)
                if query_status['status'] != 'running':
                    # query has finished
                    break
                else:
                    time.sleep(ctr)
                    ctr += 1
                    # linear backoff
        except BaseException as e:
            print(e, file=sys.stderr)
            if e.response.status_code == 400:
                QueryLilGIM._jprint(e.response.json(), file=sys.stderr)
                raise
        return pandas.concat(map(pandas.read_csv, query_status['request_uri']))

    # anatomy_curie_id_str:  string CURIE ID for an Uberon anatomy term
    # protein_set_curie_id_str:  a tuple containing one or more string CURIE IDs for proteins (UniProtKB)
    # return value: a dict in which keys are string Uniprot CURIE IDs and values are correlation coeffs
    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def query_neighbor_genes_for_gene_set_in_a_given_anatomy(self,
                                                             anatomy_curie_id_str,
                                                             protein_set_curie_id_str,
                                                             allowed_proteins_filter_tuple=tuple()):

        assert type(protein_set_curie_id_str) == tuple
        assert len(protein_set_curie_id_str) > 0
        assert type(anatomy_curie_id_str) == str
        if allowed_proteins_filter_tuple:
            assert type(allowed_proteins_filter_tuple) == tuple
            assert len(allowed_proteins_filter_tuple) > 0

        # convert UBERON anatomy curie ID str to a brenda anatomy ID
        assert anatomy_curie_id_str.startswith("UBERON:")
        bto_id_set = QueryEBIOLS.get_bto_id_for_uberon_id(anatomy_curie_id_str)
        ret_dict = dict()
        if len(bto_id_set) == 0:
            return ret_dict

        assert len(bto_id_set) == 1

        bto_term = QueryEBIOLS.get_bto_term_for_bto_id(next(iter(bto_id_set))).replace(" ", "_")

        entrez_gene_ids = set()
        entrez_gene_ids_int = set()
        
        # convert uniprot IDs to Entrez gene IDs
        for protein_curie_id_str in protein_set_curie_id_str:
            assert protein_curie_id_str.startswith("UniProtKB:")
            uniprot_acc = protein_curie_id_str.split(":")[1]
            entrez_gene_id_set = self.mg.convert_uniprot_id_to_entrez_gene_ID(uniprot_acc)
            for entrez_gene_id in entrez_gene_id_set:
                entrez_gene_ids_int.add(entrez_gene_id)
                entrez_gene_ids.add(str(entrez_gene_id))

        entrez_gene_ids_str = ",".join(entrez_gene_ids)

        data = {"ids": entrez_gene_ids_str,
                "tissue": bto_term,
                "limit": self.limit}

        results = self._wrapper(self.ENDPOINT, data)

        ret_dict = dict()
        gene_dict = dict()
        
        for index, row in results.iterrows():
            gene1 = row["Gene1"]
            gene2 = row["Gene2"]
            avg_corr = row["aveCorr"]
            assert type(gene1) == int
            assert type(gene2) == int
            assert type(avg_corr) == float
            if gene1 in entrez_gene_ids_int:
                if gene2 in entrez_gene_ids_int:
                    # do nothing since this is not a new gene
                    new_gene_id = None
                else:
                    # gene2 is the new gene
                    new_gene_id = gene2
            else:
                if gene2 in entrez_gene_ids_int:
                    new_gene_id = gene1
                else:
                    print("neither gene was in the set of query genes, this should not happen", file=sys.stderr)
                    assert False
            if new_gene_id is not None:
                gene_dict[new_gene_id] = avg_corr

        for gene_id, avg_corr in gene_dict.items():
            uniprot_id_set = self.mg.convert_entrez_gene_id_to_uniprot_id(gene_id)
            if len(uniprot_id_set) > 0:
                for uniprot_id in uniprot_id_set:
                    if len(allowed_proteins_filter_tuple) == 0:
                        ret_dict["UniProtKB:" + uniprot_id] = avg_corr
                    else:
                        if uniprot_id in allowed_proteins_filter_tuple:
                            ret_dict["UniProtKB:" + uniprot_id] = avg_corr

        return ret_dict

if __name__ == '__main__':
    qlg = QueryLilGIM()
    print(qlg.query_neighbor_genes_for_gene_set_in_a_given_anatomy("UBERON:0002384", ("UniProtKB:P12004",)))
    new_tuple = ('Q14691', 'O75792', 'Q9Y242')
    print(qlg.query_neighbor_genes_for_gene_set_in_a_given_anatomy("UBERON:0002384", ("UniProtKB:P12004",), new_tuple))
    empty_tuple = ()
    print(qlg.query_neighbor_genes_for_gene_set_in_a_given_anatomy("UBERON:0002384", ("UniProtKB:P12004",), empty_tuple))
    # print(qlg.query_neighbor_genes_for_gene_set_in_a_given_anatomy("UBERON:0000178", {"UniProtKB:P01579"}))
