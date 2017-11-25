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

import pandas
import timeit
import argparse

## configure requests package to use the "orangeboard.sqlite" cache
requests_cache.install_cache('orangeboard')

## create an Orangeboard object
ob = Orangeboard(debug=True)

## configure the Orangeboard for Neo4j connectivity
ob.neo4j_set_url()
ob.neo4j_set_auth()


master_rel_is_directed = {'disease_affects': True,
                          'is_member_of': True,
                          'is_parent_of': True,
                          'gene_assoc_with': True,
                          'phenotype_assoc_with': True,
                          'interacts_with': False,
                          'controls_expression_of': True,
                          'is_expressed_in': True,
                          'targets': True}

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

ob.set_dict_reltype_dirs(master_rel_is_directed)
ob.neo4j_set_url()
ob.neo4j_set_auth()

bne = BioNetExpander(ob)

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

q2_mesh_to_diseases_look_aside_dict = {'MESH:D000855': 'DOID:8689',
                                       'MESH:D016174': 'DOID:1883',
                                       'MESH:D001007': 'DOID:2030',
                                       'MESH:D056912': 'DOID:8670',
                                       'MESH:D007024': 'DOID:10556',
                                       'MESH:D010259': 'DOID:10938',
                                       'MESH:D009169': 'DOID:399',
                                       'MESH:D008414': 'DOID:10690',
                                       'MESH:D014549': 'DOID:724',
                                       'MESH:D016411': 'DOID:0050749'}

def seed_and_expand_kg_q1():
    ## seed all 21 diseases in the Orangeboard
    ## set the seed node flag to True, for the first disease
    seed_node_bool = True
    for disont_id_str in q1_diseases_dict.keys():
        ob.add_node('disont_disease', disont_id_str, seed_node_bool)
        ## for the rest of the diseases, do not set the seed-node flag
        seed_node_bool = False

    ## triple-expand the knowledge graph
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()

    omim_df = pandas.read_csv('../../q1/Genetic_conditions_from_OMIM.txt',
                              sep='\t')[['MIM_number','preferred_title']]
    first_row = True
    for index, row in omim_df.iterrows():
        ob.add_node('omim_disease', 'OMIM:' + str(row['MIM_number']),
                    desc=row['preferred_title'],
                    seed_node_bool=first_row)
        if first_row:
            first_row = False

    ## triple-expand the knowledge graph
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()

MESH_ENTREZ_UID_BASE = 68000000

def convert_mesh_entrez_uid_to_curie_form(mesh_entrez_uid):
    assert mesh_entrez_uid > MESH_ENTREZ_UID_BASE
    return 'MESH:D' + format(mesh_entrez_uid - MESH_ENTREZ_UID_BASE, '06')

human_phenont_name_id_dict = ParsePhenont.get_name_id_dict('../../hpo/hp.obo')

def get_disont_ids_for_mesh_term(mesh_term):
    ret_disont_ids = []
    mesh_uids = QueryNCBIeUtils.get_mesh_uids_for_mesh_term(mesh_term)
    if len(mesh_uids) > 0:
        for mesh_uid in mesh_uids:
            mesh_uid_int = int(mesh_uid)
            if mesh_uid_int > MESH_ENTREZ_UID_BASE:
                mesh_id_curie = convert_mesh_entrez_uid_to_curie_form(mesh_uid_int)
                disont_ids = QuerySciGraph.get_disont_ids_for_mesh_id(mesh_id_curie)
                if len(disont_ids) > 0:
                    ret_disont_ids += disont_ids
                else:
                    lal_disont_id = q2_mesh_to_diseases_look_aside_dict.get(mesh_id_curie, None)
                    if lal_disont_id is not None:
                        ret_disont_ids += [lal_disont_id]
            else:
                print('Got MeSH UID less than ' + str(MESH_ENTREZ_UID_BASE) + ': ' + mesh_uid + \
                      '; for MeSH term: ' + mesh_term, file=sys.stderr)

    return ret_disont_ids
    
def seed_and_expand_kg_q2():
    
    drug_dis_df = pandas.read_csv('../../q2/q2-drugandcondition-list.txt',
                                  sep='\t')

    print('=====================> seeding disease nodes for Q2')
    
    first_row = True
    mesh_terms_set = set()
    for index, row in drug_dis_df.iterrows():
        mesh_term = row['Condition']
        if mesh_term not in mesh_terms_set:
            mesh_terms_set.add(mesh_term)
            disont_ids = get_disont_ids_for_mesh_term(mesh_term)
            if len(disont_ids) > 0:
                assert type(disont_ids)==list
                for disont_id in disont_ids:
                    disont_desc = QueryDisont.query_disont_to_label(disont_id)
                    ob.add_node('disont_disease', disont_id, desc=disont_desc, seed_node_bool=first_row)
                    first_row = False
            else:
                human_phenont_id = human_phenont_name_id_dict.get(mesh_term, None)
                if human_phenont_id is not None:
                    ob.add_node('phenont_phenotype', human_phenont_id, desc=mesh_term, seed_node_bool=first_row)
                    first_row = False
                else:
                    print('Unable to get Disease Ontology ID or Human Phenotype Ontology ID for MeSH term: ' + mesh_term, file=sys.stdout)                        
                    

    ## triple-expand the knowledge graph
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
                
    print('=====================> seeding drug nodes for Q2')
    first_row = True
    for index, row in drug_dis_df.iterrows():
        ob.add_node('pharos_drug', row['Drug'].lower(), seed_node_bool=first_row)
        first_row = False

    ## triple-expand the knowledge graph
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    
def make_master_kg():
    seed_and_expand_kg_q1()
    seed_and_expand_kg_q2()
    ob.neo4j_set_url('bolt://0.0.0.0:7687')
    ob.neo4j_push()
    print("count(Node) = {}".format(ob.count_nodes()))
    print("count(Rel) = {}".format(ob.count_rels()))

running_time = timeit.timeit(lambda: make_master_kg(), number=1)
print('running time for test: ' + str(running_time))

