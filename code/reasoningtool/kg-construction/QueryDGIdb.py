"""This module defines the class QueryDGIdb which downloads and reads the
interactions.tsv file from the DGIdb database (http://www.dgidb.org/downloads)

"""

__author__ = "Stephen Ramsey"
__copyright__ = ""
__credits__ = ['Stephen Ramsey']
__license__ = ""
__version__ = ""
__maintainer__ = 'Stephen Ramsey'
__email__ = 'stephen.ramsey@oregonstate.edu'
__status__ = 'Prototype'

import pandas
import sys
from QueryMyGene import QueryMyGene
from QueryPubChem import QueryPubChem
from QueryChEMBL import QueryChEMBL


class QueryDGIdb:
    INTERACTIONS_TSV_URL = 'http://www.dgidb.org/data/interactions.tsv'

    mygene = QueryMyGene()

    predicate_map = {'inhibitor':                       'negatively_regulates',
                     'agonist':                         'positively_regulates',
                     'antagonist':                      'negatively_regulates',
                     'blocker':                         'negatively_regulates',
                     'positive allosteric modulator':   'positively_regulates',
                     'channel blocker':                 'negatively_regulates',
                     'allosteric modulator':            'negatively_regulates',
                     'activator':                       'positively_regulates',
                     'antibody':                        'affects',
                     'binder':                          'affects',
                     'modulator':                       'negatively_regulates',
                     'partial agonist':                 'positively_regulates',
                     'gating inhibitor':                'negatively_regulates',
                     'antisense':                       'negatively_regulates',
                     'vaccine':                         'negatively_regulates',
                     'inverse agonist':                 'negatively_regulates',
                     'stimulator':                      'positively_regulates',
                     'antisense oligonucleotide':       'negatively_regulates',
                     'cofactor':                        'physically_interacts_with',
                     'negative modulator':              'negatively_regulates',
                     'inducer':                         'positively_regulates',
                     'suppressor':                      'negatively_regulates',
                     'inhibitory allosteric modulator': 'negatively_regulates',
                     'affects':                         'affects'}

    def read_interactions():
        int_data = pandas.read_csv(QueryDGIdb.INTERACTIONS_TSV_URL, sep='\t')
        int_data.fillna('', inplace=True)
        res_list = []
        for index, row in int_data.iterrows():
            pmids = row['PMIDs']
            gene_name = row['gene_name']
            gene_claim_name = row['gene_claim_name']
            if gene_name != '':
                gene_symbol = gene_name
            else:
                if gene_claim_name != '':
                    gene_symbol = gene_claim_name
                else:
                    continue
            assert ',' not in gene_symbol
            uniprot_ids_set = QueryDGIdb.mygene.convert_gene_symbol_to_uniprot_id(gene_symbol)
            if len(uniprot_ids_set) == 0:
                continue

            drug_chembl_id = row['drug_chembl_id']
            drug_name = row['drug_name']

            if drug_chembl_id != '':
                if type(drug_chembl_id) == float:
                    print(row)
                assert ',' not in drug_chembl_id
                drug_chembl_id_set = {drug_chembl_id}
                if drug_name == '':
                    print("warning; ChEMBL compound has no drug name", file=sys.stderr)
            else:
                if drug_name != '':
                    assert ',' not in drug_name
                    drug_chembl_id_set = QueryPubChem.get_chembl_ids_for_drug(drug_name)
                    if len(drug_chembl_id_set) == 0:
                        drug_chembl_id_set = QueryChEMBL.get_chembl_ids_for_drug(drug_name)
                        if len(drug_chembl_id_set) == 0:
                            continue
                else:
                    continue

            interaction_claim_source_field = row['interaction_claim_source']
            interaction_types_field = row['interaction_types']
            if interaction_types_field != '':
                assert type(interaction_types_field) == str
                predicate_list = interaction_types_field.split(',')
            else:
                predicate_list = ['affects']

            for uniprot_id in uniprot_ids_set:
                for predicate_str in predicate_list:
                    res_list.append({
                        'drug_chembl_id': drug_chembl_id,
                        'drug_name': drug_name,
                        'predicate': QueryDGIdb.predicate_map[predicate_str],
                        'predicate_extended': predicate_str,
                        'protein_uniprot_id': uniprot_id,
                        'protein_gene_symbol': gene_symbol,
                        'sourcedb': interaction_claim_source_field,
                        'pmids': pmids})
#                    print(drug_chembl_id + '\t' + predicate_str + '\t' + uniprot_id + '\t' + interaction_claim_source_field + '\t' + ','.join(pmids_list))
        return res_list


if __name__ == '__main__':
    res_list = QueryDGIdb.read_interactions()
    for tuple in res_list:
        print(tuple)
