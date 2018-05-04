'''Builds a master knowledge graph and pushes it to Neo4j.  Uses BioNetExpander and Orangeboard.

   Usage:  sh run_build_master_kg.sh
'''

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Yao Yao', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import requests_cache
import sys
from Orangeboard import Orangeboard
from BioNetExpander import BioNetExpander
from QueryNCBIeUtils import QueryNCBIeUtils
from QuerySciGraph import QuerySciGraph
from QueryDisont import QueryDisont
from ParsePhenont import ParsePhenont
from QueryChEMBL import QueryChEMBL
from QueryPubChem import QueryPubChem

import pandas
import timeit
import argparse

MESH_ENTREZ_UID_BASE = 68000000

# configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')

# create an Orangeboard object
ob = Orangeboard(debug=True)

# configure the Orangeboard for Neo4j connectivity
ob.neo4j_set_url()
ob.neo4j_set_auth()

bne = BioNetExpander(ob)


def convert_mesh_entrez_uid_to_curie_form(mesh_entrez_uid):
    assert mesh_entrez_uid > MESH_ENTREZ_UID_BASE
    return 'MESH:D' + format(mesh_entrez_uid - MESH_ENTREZ_UID_BASE, '06')


human_phenont_name_id_dict = ParsePhenont.get_name_id_dict('../../../data/hpo/hp.obo')


def get_curie_ont_ids_for_mesh_term(mesh_term):
    ret_curie_ids = []
    mesh_uids = QueryNCBIeUtils.get_mesh_uids_for_mesh_term(mesh_term)
    if len(mesh_uids) > 0:
        for mesh_uid in mesh_uids:
            mesh_uid_int = int(mesh_uid)
            if mesh_uid_int > MESH_ENTREZ_UID_BASE:
                mesh_id_curie = convert_mesh_entrez_uid_to_curie_form(mesh_uid_int)
                disont_ids = QuerySciGraph.get_disont_ids_for_mesh_id(mesh_id_curie)
                if len(disont_ids) > 0:
                    ret_curie_ids += disont_ids
            else:
                print('Got MeSH UID less than ' + str(MESH_ENTREZ_UID_BASE) + ': ' + mesh_uid + 
                      '; for MeSH term: ' + mesh_term, file=sys.stderr)
    if len(ret_curie_ids) == 0:
        human_phenont_id = human_phenont_name_id_dict.get(mesh_term, None)
        if human_phenont_id is not None:
            ret_curie_ids.append(human_phenont_id)
    return ret_curie_ids

def add_pc2_to_kg():
    sif_data = pandas.read_csv('../../../data/pc2/PathwayCommons9.All.hgnc.sif',
                               sep='\t', names=['gene1', 'interaction_type', 'gene2'])
    interaction_types = set(['interacts-with',
                             'controls-expression-of',
                             'controls-state-change-of',
                             'controls-phosphorylation-of'])
    sif_data = sif_data[sif_data.interaction_type.isin(interaction_types)]
    genes = set(sif_data['gene1'].tolist() + sif_data['gene2'].tolist())
    genes_uniprot_dict = dict()
    print('converting gene names')
    for gene in genes:
        genes_uniprot_dict[gene] = bne.query_mygene_obj.convert_gene_symbol_to_uniprot_id(gene)
    print('testing interactions to see if nodes are in the orangeboard')
    for index, row in sif_data.iterrows():
        interaction_type = row['interaction_type']
        gene1 = row['gene1']
        gene2 = row['gene2']
        uniprots1 = genes_uniprot_dict.get(gene1, None)
        uniprots2 = genes_uniprot_dict.get(gene2, None)
        if uniprots1 is not None and len(uniprots1) == 1 and \
           uniprots2 is not None and len(uniprots2) == 1:
            uniprot1 = next(iter(uniprots1))
            uniprot2 = next(iter(uniprots2))
            node1 = ob.get_node('protein', uniprot1)
            node2 = ob.get_node('protein', uniprot2)
            if node1 is not None and node2 is not None and node1.uuid != node2.uuid:
                if interaction_type == 'interacts-with':
                    ob.add_rel('directly_interacts_with', 'PC2', node1, node2, extended_reltype="directly_interacts_with")
                else:
                    if interaction_type == 'controls-expression-of':
                        ob.add_rel("regulates", 'PC2', node1, node2, extended_reltype="regulates_expression_of")
                    else:
                        if interaction_type == 'controls-state-change-of' or \
                           interaction_type == 'controls-phosphorylation-of':
                            ob.add_rel("regulates", 'PC2', node1, node2, extended_reltype="regulates_activity_of")
                        else:
                            assert False


def seed_nodes_from_master_tsv_file():
    seed_node_data = pandas.read_csv('../../../data/seed_nodes.tsv',
                                     sep="\t",
                                     names=['type', 'rtx_name', 'term', 'purpose'],
                                     header=0,
                                     dtype={'rtx_name': str})
    first_row = True
    for index, row in seed_node_data.iterrows():
        bne.add_node_smart(row['type'], row['rtx_name'], seed_node_bool=first_row, desc=row['term'])
        if first_row is True:
            first_row = False


def make_master_kg():
    seed_nodes_from_master_tsv_file()
    add_pc2_to_kg()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    ob.neo4j_set_url('bolt://0.0.0.0:7687')
    ob.neo4j_push()
    print("count(Node) = {}".format(ob.count_nodes()))
    print("count(Rel) = {}".format(ob.count_rels()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Builds the master knowledge graph')
    parser.add_argument('--runfunc', dest='runfunc')
    args = parser.parse_args()
    args_dict = vars(args)
    if args_dict.get('runfunc', None) is not None:
        run_function_name = args_dict['runfunc']
    else:
        run_function_name = 'make_master_kg'
    try:
        run_function = globals()[run_function_name]
    except KeyError:
        sys.exit('In module BuildMasterKG.py, unable to find function named: ' + run_function_name)
    running_time = timeit.timeit(lambda: run_function(), number=1)
    print('running time for function: ' + str(running_time))
