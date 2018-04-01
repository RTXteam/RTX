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

import pandas
import timeit
import argparse

MESH_ENTREZ_UID_BASE = 68000000

## configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')

## create an Orangeboard object
ob = Orangeboard(debug=True)

## configure the Orangeboard for Neo4j connectivity
ob.neo4j_set_url()
ob.neo4j_set_auth()

q1_diseases_dict = {'DOID:11476':   'osteoporosis',
                    'DOID:526':     'HIV infectious disease',
                    'DOID:1498':    'cholera',
                    'DOID:4325':    'Ebola hemmorhagic fever',
                    'DOID:12365':   'malaria',
                    'DOID:10573':   'Osteomalacia',
                    'DOID:13810':   'hypercholesterolemia',
                    'DOID:9352':    'type 2 diabetes mellitus',
                    'DOID:2841':    'asthma',
                    'DOID:4989':    'pancreatitis',
                    'DOID:10652':   'Alzheimer Disease',
                    'DOID:5844':    'Myocardial Infarction',
                    'DOID:11723':   'Duchenne Muscular Dystrophy',
                    'DOID:0060728': 'NGLY1-deficiency',
                    'DOID:0050741': 'Alcohol Dependence',
                    'DOID:1470':    'major depressive disorder',
                    'DOID:14504':   'Niemann-Pick disease',
                    'DOID:12858':   'Huntington\'s Disease',
                    'DOID:9270':    'Alkaptonuria',
                    'DOID:10923':   'sickle cell anemia',
                    'DOID:2055':    'post-traumatic stress disorder'}

q1_omim_to_uniprot_look_aside_dict = {'OMIM:166710': ['Q05925']}

q2_mesh_to_conditions_look_aside_dict = {'MESH:D000855': 'DOID:8689',
                                         'MESH:D016174': 'DOID:1883',
                                         'MESH:D001007': 'DOID:2030',
                                         'MESH:D056912': 'DOID:8670',
                                         'MESH:D007024': 'DOID:10556',
                                         'MESH:D010259': 'DOID:10938',
                                         'MESH:D009169': 'DOID:399',
                                         'MESH:D008414': 'DOID:10690',
                                         'MESH:D014549': 'DOID:724',
                                         'MESH:D016411': 'DOID:0050749',
                                         'MESH:D011247': 'HP:0002686',
                                         'MESH:D001777': 'HP:0001928',
                                         'MESH:D003085': 'HP:0011848',
                                         'MESH:D009057': 'HP:1091',
                                         'MESH:D004107': 'HP:0030449',
                                         'MESH:D016099': 'HP:12072',
                                         'MESH:D004927': 'HP:0005420',
                                         'MESH:D005393': 'DOID:104',
                                         'MESH:D030762': 'HP:0030449',
                                         'MESH:D051271': 'HP:0002315',
                                         'MESH:D006470': 'HP:0006535',
                                         'MESH:D019584': 'HP:0005968',
                                         'MESH:D007249': 'HP:0012531',
                                         'MESH:D018784': 'HP:0100592',
                                         'MESH:D055744': 'DOID:0050073',
                                         'MESH:D019266': 'HP:0001891',
                                         'MESH:D017116': 'HP:0003419',
                                         'MESH:D008593': 'HP:0100805',
                                         'MESH:D008597': 'HP:0000140',
                                         'MESH:D009126': 'HP:0002486',
                                         'MESH:D026201': 'HP:0002486',
                                         'MESH:D051474': 'DOID:9210',
                                         'MESH:D007744': 'HP:0030369',
                                         'MESH:D010272': 'DOID:1398',
                                         'MESH:D017698': 'DOID:11968',
                                         'MESH:D011183': 'DOID:8440',
                                         'MESH:D020250': 'HP:0002017',
                                         'MESH:D011248': 'HP:0001788',
                                         'MESH:D011275': 'HP:0030449',
                                         'MESH:D007752': 'HP:0001788',
                                         'MESH:D011595': 'HP:0002361',
                                         'MESH:D012120': 'HP:0002093',
                                         'MESH:D012140': 'DOID:1579',
                                         'MESH:D012141': 'HP:0011947',
                                         'MESH:D012550': 'DOID:0050597',
                                         'MESH:D012892': 'HP:0100785',
                                         'MESH:D012907': 'DOID:0050742',
                                         'MESH:D018461': 'HP:0002718',
                                         'MESH:D013035': 'HP:0006963',
                                         'MESH:D013614': 'HP:0006688',
                                         'MESH:D014593': 'HP:0002486',
                                         'MESH:D015430': 'HP:0004324',
                                         'MESH:D006376': 'DOID:883',
                                         'MESH:D015431': 'HP:0001824',
                                         'MESH:D019106': 'HP:0011891',
                                         'MESH:D009119': 'HP:0004305'  # not sure about this particular mapping
}

ob.neo4j_set_url()
ob.neo4j_set_auth()
bne = BioNetExpander(ob)

def seed_and_expand_kg_q1(num_expansions):
    ## seed all 21 diseases in the Orangeboard
    ## set the seed node flag to True, for the first disease
    seed_node_bool = True
    for disont_id_str, disont_desc in q1_diseases_dict.items():
        bne.add_node_smart('disont_disease', disont_id_str, seed_node_bool, desc=disont_desc)
        ## for the rest of the diseases, do not set the seed-node flag
        seed_node_bool = False

    ## triple-expand the knowledge graph
    for _ in range(0, num_expansions):
        bne.expand_all_nodes()

    omim_df = pandas.read_csv('../../data/q1/Genetic_conditions_from_OMIM.txt',
                              sep='\t')[['MIM_number','preferred_title']]
    first_row = True
    for index, row in omim_df.iterrows():
        bne.add_node_smart('omim_disease', 'OMIM:' + str(row['MIM_number']),
                           seed_node_bool=first_row,
                           desc=row['preferred_title'])
        if first_row:
            first_row = False

    for omim_id in q1_omim_to_uniprot_look_aside_dict.keys():
        omim_node = ob.get_node('omim_disease', omim_id)
        assert omim_node is not None
        uniprot_ids_list = q1_omim_to_uniprot_look_aside_dict[omim_id]
#        print(uniprot_ids_list)
        for uniprot_id in uniprot_ids_list:
            gene_symbols = bne.query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id)
            print(gene_symbols)
            assert len(gene_symbols) > 0
            prot_node = bne.add_node_smart('protein', uniprot_id, desc=';'.join(list(gene_symbols)))
            ob.add_rel('associated with condition', 'OMIM', prot_node, omim_node, extended_reltype="associated with disease")

    ## triple-expand the knowledge graph
    for _ in range(0, num_expansions):
        bne.expand_all_nodes()

def convert_mesh_entrez_uid_to_curie_form(mesh_entrez_uid):
    assert mesh_entrez_uid > MESH_ENTREZ_UID_BASE
    return 'MESH:D' + format(mesh_entrez_uid - MESH_ENTREZ_UID_BASE, '06')

human_phenont_name_id_dict = ParsePhenont.get_name_id_dict('../../data/hpo/hp.obo')

def get_curie_ont_ids_for_mesh_term(mesh_term):
    ret_curie_ids = []
    mesh_uids = QueryNCBIeUtils.get_mesh_uids_for_mesh_term(mesh_term)
#    print(mesh_uids)
    if len(mesh_uids) > 0:
        for mesh_uid in mesh_uids:
            mesh_uid_int = int(mesh_uid)
            if mesh_uid_int > MESH_ENTREZ_UID_BASE:
                mesh_id_curie = convert_mesh_entrez_uid_to_curie_form(mesh_uid_int)
                disont_ids = QuerySciGraph.get_disont_ids_for_mesh_id(mesh_id_curie)
                if len(disont_ids) > 0:
                    ret_curie_ids += disont_ids
                else:
                    
                    lal_curie_id = q2_mesh_to_conditions_look_aside_dict.get(mesh_id_curie, None)
                    if lal_curie_id is not None:
                        ret_curie_ids += [lal_curie_id]
            else:
                print('Got MeSH UID less than ' + str(MESH_ENTREZ_UID_BASE) + ': ' + mesh_uid + \
                      '; for MeSH term: ' + mesh_term, file=sys.stderr)
    if len(ret_curie_ids)==0:
        human_phenont_id = human_phenont_name_id_dict.get(mesh_term, None)
        if human_phenont_id is not None:
            ret_curie_ids.append(human_phenont_id)
    return ret_curie_ids
    
def seed_and_expand_kg_q2(num_expansions=3, seed_parts=None):
    
    drug_dis_df = pandas.read_csv('../../data/q2/q2-drugandcondition-list.txt',
                                  sep='\t')

    if seed_parts is None or 'conditions' in seed_parts:

        print('=====================> seeding disease nodes for Q2')
        first_row = True
        mesh_terms_set = set()
        mesh_term_to_curie_ids_dict = dict()
        curie_ids_for_df = []
        for index, row in drug_dis_df.iterrows():
            mesh_term = row['Condition']
            if mesh_term not in mesh_terms_set:
                mesh_term_to_curie_ids_dict[mesh_term] = None
                mesh_terms_set.add(mesh_term)
                curie_ids = get_curie_ont_ids_for_mesh_term(mesh_term)
                if len(curie_ids) > 0:
                    assert type(curie_ids)==list
                    for curie_id in curie_ids:
                        if 'DOID:' in curie_id:
                            disont_desc = QueryDisont.query_disont_to_label(curie_id)
                            bne.add_node_smart('disont_disease', curie_id, seed_node_bool=first_row, desc=disont_desc)
                            mesh_term_to_curie_ids_dict[mesh_term] = curie_id
                            first_row = False
                        else:
                            if 'HP:' in curie_id:
                                bne.add_node_smart('phenont_phenotype', curie_id, seed_node_bool=first_row, desc=mesh_term)
                                mesh_term_to_curie_ids_dict[mesh_term] = curie_id
                                first_row = False
                            else:
                                assert False ## should never get here
            curie_ids_for_df.append(mesh_term_to_curie_ids_dict[mesh_term])
        drug_dis_df['CURIE_ID'] = pandas.Series(curie_ids_for_df, index=drug_dis_df.index)
        drug_dis_df.to_csv('../../data/q2/q2-drugandcondition-list-mapped-output.txt', sep='\t')
        ## triple-expand the knowledge graph
        for _ in range(0, num_expansions):
            bne.expand_all_nodes()
                
    if seed_parts is None or 'drugs' in seed_parts:
        print('=====================> seeding drug nodes for Q2')
        first_row = True
        all_drugs = set()
        
        for index, row in drug_dis_df.iterrows():
            drug_name = row['Drug'].lower()
            all_drugs.add(drug_name)

        fda_drug_df = pandas.read_csv('../../data/q2/drugset2017_filt.txt',
                                      sep='\t')

        for index, row in fda_drug_df.iterrows():
            drug_name = row['NAME'].lower()
            all_drugs.add(drug_name)
            
        for drug_name in all_drugs:
            print(drug_name)
            chembl_ids = QueryChEMBL.get_chembl_ids_for_drug(drug_name)
            if chembl_ids is not None and len(chembl_ids) > 0:
                chembl_id = next(iter(chembl_ids))
            else:
                chembl_id = ''
            bne.add_node_smart('compound', chembl_id, seed_node_bool=first_row, desc=drug_name)
            first_row = False

        ## triple-expand the knowledge graph
        for _ in range(0, num_expansions):
            bne.expand_all_nodes()

def add_pc2_to_kg():
    sif_data = pandas.read_csv('../../data/pc2/PathwayCommons9.All.hgnc.sif',
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
        if uniprots1 is not None and len(uniprots1)==1 and \
           uniprots2 is not None and len(uniprots2)==1:
            uniprot1 = next(iter(uniprots1))
            uniprot2 = next(iter(uniprots2))
            node1 = ob.get_node('protein', uniprot1)
            node2 = ob.get_node('protein', uniprot2)
            if node1 is not None and node2 is not None and node1.uuid != node2.uuid:
                if interaction_type == 'interacts-with':
                    ob.add_rel('directly interacts with', 'PC2', node1, node2, extended_reltype="directly interacts with")
                else:
                    if interaction_type == 'controls-expression-of':
                        ob.add_rel("regulates", 'PC2', node1, node2, extended_reltype="regulates expression of")
                    else:
                        if interaction_type == 'controls-state-change-of' or \
                           interaction_type == 'controls-phosphorylation-of':
                            ob.add_rel("regulates", 'PC2', node1, node2, extended_reltype="regulates activity of")
                        else:
                            assert False

def seed_and_expand_kg_q2_cop(num_expansions=3):
    q2_cop_data = pandas.read_csv('../../data/q2/cop_data.tsv',
                                  sep="\t",
                                  names=['type', 'curie_id', 'term'],
                                  header=0)
    first_row = True
    for index, row in q2_cop_data.iterrows():
        bne.add_node_smart(row['type'], row['curie_id'], seed_node_bool=first_row, desc=row['term'])
        if first_row == True:
            first_row = False
    for _ in range(0, num_expansions):
        bne.expand_all_nodes()
    
def make_master_kg():
    seed_and_expand_kg_q2_cop(num_expansions=3)
    seed_and_expand_kg_q2(num_expansions=3)
    seed_and_expand_kg_q1(num_expansions=3)
    add_pc2_to_kg()
    ob.neo4j_set_url('bolt://0.0.0.0:7687')
    ob.neo4j_push()
    print("count(Node) = {}".format(ob.count_nodes()))
    print("count(Rel) = {}".format(ob.count_rels()))


def test_seed_q2_drugs():
    seed_and_expand_kg_q2(num_expansions=1, seed_parts=['drugs'])
    ob.neo4j_set_url('bolt://0.0.0.0:7687')
    ob.neo4j_push()
    print("count(Node) = {}".format(ob.count_nodes()))
    print("count(Rel) = {}".format(ob.count_rels()))


def test_fa():
    print(get_curie_ont_ids_for_mesh_term("Fanconi Anemia"))


def make_file_q2_mapping():
    seed_and_expand_kg_q2(num_expansions=0)


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
                        
    

