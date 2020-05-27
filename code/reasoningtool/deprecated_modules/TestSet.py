''' This module defines all the unit tests and integration testing.

    NOTE:  run this script with
              python3 -u
    in order to see print debugging statements as they are printed, if you
    are redirecting stdout and stderr to a file.
'''

__author__ = 'Yao Yao'
__copyright__ = 'Oregon State University'
__credits__ = ['Yao Yao', 'Zheng Liu', 'Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import argparse
import timeit
import requests_cache
import sys
from Orangeboard import Orangeboard
from BioNetExpander import BioNetExpander
import pandas
import os
import re

#requests_cache.install_cache('orangeboard')
# specifiy the path of orangeboard database
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
dbpath = os.path.sep.join([*pathlist[:(RTXindex+1)],'data','orangeboard'])
requests_cache.install_cache(dbpath)

ob = Orangeboard(debug=True)
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

def seed_kg_q1():
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

def seed_kg_q2():
    
    drug_dis_df = pandas.read_csv('../../q2/q2-drugandcondition-list.txt',
                                  sep='\t')

    first_row = True
    for index, row in drug_dis_df.iterrows():
        ob.add_node('pharos_drug', row['Drug'].lower(), seed_node_bool=first_row)
        if first_row:
            first_row = False

    ## triple-expand the knowledge graph
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    
def make_master_kg():
    seed_kg_q1()
    seed_kg_q2()
    ob.neo4j_set_url('bolt://0.0.0.0:7687')
    ob.neo4j_push()
    print("count(Node) = {}".format(ob.count_nodes()))
    print("count(Rel) = {}".format(ob.count_rels()))

def make_q1_kg_and_save_as_csv():
    seed_kg_q1()
    nodes_file = open('nodes.csv', 'w')
    nodes_file.write(ob.simple_print_nodes())
    nodes_file.close()
    rels_file = open('rels.csv', 'w')
    rels_file.write(ob.simple_print_rels())
    rels_file.close()
    
def test_omim_8k():
    omim_df = pandas.read_csv('../../genetic_conditions/Genetic_conditions_from_OMIM.txt',
                              sep='\t')[['MIM_number','preferred_title']]
    first_row = True
    for index, row in omim_df.iterrows():
        ob.add_node('omim_disease', 'OMIM:' + str(row['MIM_number']), seed_node_bool=first_row)
        if first_row:
            first_row = False

    ## expand the knowledge graph
    bne.expand_all_nodes()

def read_drug_dis():
    drug_dis_df = pandas.read_csv('../../q2/q2-drugandcondition-list.txt',
                                  sep='\t')
    for index, row in drug_dis_df.iterrows():
        print('add drug: ' + row['Drug'].lower())

def test_description_mim():
    node = ob.add_node('omim_disease', 'OMIM:603903', desc='sickle-cell anemia', seed_node_bool=True)
    bne.expand_omim_disease(node)
    ob.neo4j_push()


def test_description_uniprot():
    node = ob.add_node('uniprot_protein', 'P68871', desc='HBB', seed_node_bool=True)
    print(ob)
    bne.expand_uniprot_protein(node)
    ob.neo4j_push()


def test_description_disont():
    node = ob.add_node('disont_disease', 'DOID:12365', desc='malaria', seed_node_bool=True)
    bne.expand_disont_disease(node)
    ob.neo4j_push()


def test_description_disont2():
    node = ob.add_node('disont_disease', 'DOID:9352', desc='foobar', seed_node_bool=True)
    bne.expand_disont_disease(node)
    ob.neo4j_push()


def test_add_mim():
    node = ob.add_node('omim_disease', 'OMIM:603903', desc='sickle-cell anemia', seed_node_bool=True)
    bne.expand_omim_disease(node)
    ob.neo4j_push()


def test_issue2():
    node = ob.add_node('omim_disease', 'OMIM:603933', desc='sickle-cell anemia', seed_node_bool=True)
    bne.expand_omim_disease(node)


def test_issue3():
    disease_node = ob.add_node('disont_disease', 'DOID:9352', desc='foo', seed_node_bool=True)
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()


def test_issue6():
    ob.add_node('omim_disease', 'OMIM:605027', desc='LYMPHOMA, NON-HODGKIN, FAMILIAL', seed_node_bool=True)
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()


def test_issue7():
    ob.add_node('omim_disease', 'OMIM:605275', desc='NOONAN SYNDROME 2; NS2', seed_node_bool=True)
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()


def test_issue9():
    node1 = ob.add_node('uniprot_protein', 'P16887', desc='HBB', seed_node_bool=True)
    node2 = ob.add_node('uniprot_protein', 'P09601', desc='HMOX1')
    ob.add_rel('interacts_with', 'reactome', node1, node2)
    ob.neo4j_push()


def test_microrna():
    ob.add_node('omim_disease', 'OMIM:613074', desc='deafness', seed_node_bool=True)
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    ob.neo4j_push()


def test_anatomy_1():
    mir96 = ob.add_node('ncbigene_microrna', 'NCBIGene:407053', desc='MIR96', seed_node_bool=True)

    bne.expand_ncbigene_microrna(mir96)
    ob.neo4j_push()


def test_anatomy_2():
    hmox1 = ob.add_node('uniprot_protein', 'P09601', desc='HMOX1', seed_node_bool=True)

    bne.expand_uniprot_protein(hmox1)
    ob.neo4j_push()


def test_anatomy_3():
    mkd = ob.add_node('phenont_phenotype', 'HP:0000003', desc='Multicystic kidney dysplasia', seed_node_bool=True)

    bne.expand_phenont_phenotype(mkd)
    ob.neo4j_push()


def test_expand_pharos_drug():
    lovastatin = ob.add_node('pharos_drug', 'lovastatin', desc='lovastatin', seed_node_bool=True)

    bne.expand_pharos_drug(lovastatin)
    ob.neo4j_push()

def lysine_test_1():
    ob.add_node('pharos_drug', 'acetaminophen', desc='acetaminophen', seed_node_bool=True)

    bne.expand_all_nodes()
    ob.neo4j_push()

def lysine_test_2():
    ob.add_node('pharos_drug', 'acetaminophen', desc='acetaminophen', seed_node_bool=True)

    bne.expand_all_nodes()
    bne.expand_all_nodes()
    ob.neo4j_push()

def lysine_test_3():
    ob.add_node('pharos_drug', 'acetaminophen', desc='acetaminophen', seed_node_bool=True)

    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    ob.neo4j_push()

def lysine_test_4():
    ob.add_node('disont_disease', 'DOID:1498', desc='cholera', seed_node_bool=True)

    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    ob.neo4j_push()

    print("[lysine_test_4] count(Node) = {}".format(ob.count_nodes()))
    print("[lysine_test_4] count(Rel) = {}".format(ob.count_rels()))

def lysine_test_5():
    ob.add_node('disont_disease', 'DOID:12365', desc='malaria', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:1498', desc='cholera', seed_node_bool=True)

    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    ob.neo4j_push()

    print("[lysine_test_5] count(Node) = {}".format(ob.count_nodes()))
    print("[lysine_test_5] count(Rel) = {}".format(ob.count_rels()))

def test_issue19():
     genetic_condition_mim_id = 'OMIM:219700' # cystic fibrosis
     target_disease_disont_id = 'DOID:1498' # cholera

     disease_node = ob.add_node('disont_disease', target_disease_disont_id, desc='cholera', seed_node_bool=True)

     print('----------- first round of expansion ----------')
     bne.expand_all_nodes()

     print('----------- second round of expansion ----------')
     bne.expand_all_nodes()

     print('----------- third round of expansion ----------')
     bne.expand_all_nodes()

def test_q1_singleexpand():
    ## seed all 21 diseases in the Orangeboard
    ## set the seed node flag to True, for the first disease
    seed_node_bool = True
    for disont_id_str in q1_diseases_dict.keys():
        ob.add_node('disont_disease', disont_id_str, seed_node_bool)
        ## for the rest of the diseases, do not set the seed-node flag
        seed_node_bool = False

    bne.expand_all_nodes()

    ob.neo4j_set_url('bolt://0.0.0.0:7687')
    ob.neo4j_push()

    print("[Q1] count(Node) = {}".format(ob.count_nodes()))
    print("[Q1] count(Rel) = {}".format(ob.count_rels()))

def test_q1_no_push():
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

    ob.neo4j_set_url('bolt://0.0.0.0:7687')
#    ob.neo4j_push()

    print("[Q1] count(Node) = {}".format(ob.count_nodes()))
    print("[Q1] count(Rel) = {}".format(ob.count_rels()))

def lysine_test_6():
    ob.add_node('disont_disease', 'DOID:12365', desc='malaria', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:1498', desc='cholera', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:2841', desc='asthma', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:526', desc='HIV', seed_node_bool=True)

    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
 #   ob.neo4j_push()

    print("[lysine_test_6] count(Node) = {}".format(ob.count_nodes()))
    print("[lysine_test_6] count(Rel) = {}".format(ob.count_rels()))

def test_ob_size():
    ob.add_node('phenont_phenotype', "HP:0000107", desc='Renal cyst', seed_node_bool=True)
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    print('size is: ' + str(ob.bytesize()))

def test_expand_phenont_phenotype():
    ob.add_node('phenont_phenotype', "HP:0000107", desc='Renal cyst', seed_node_bool=True)
    bne.expand_all_nodes()
    ob.neo4j_push()

def test_query_path_from_gc_to_disease():
    # this test should be conducted after bigtest or bigtest2 complete
    # ob = Orangeboard(debug=False)
    # master_rel_is_directed = {'disease_affects': True,
    #                          'is_member_of': True,
    #                          'is_parent_of': True,
    #                          'gene_assoc_with': True,
    #                          'phenotype_assoc_with': True,
    #                          'interacts_with': False,
    #                          'controls_expression_of': True,
    #                          'is_expressed_in': True,
    #                          'targets': True}
    #ob.set_dict_reltype_dirs(master_rel_is_directed)
    #ob.neo4j_set_url()
    #ob.neo4j_set_auth()
    # path = ob.neo4j_run_cypher_query("Match p=(a:omim_disease)<--(b)-->(c:uniprot_protein) "
    #                                      "RETURN p LIMIT 1").single()['p']

    result = ob.neo4j_run_cypher_query("match p=(n)-[*..3]-(m) where n.name='OMIM:219700' and m.name='DOID:1498' return p, nodes(p), relationships(p)")

    for record in result:
        print('path:')
        nodes = record[1]
        rels = record[2]

        for r in rels:
            start_node_desc = [n for n in nodes if n.get('UUID') == r.get('source_node_uuid')][0].get('description')
            end_node_desc = [n for n in nodes if n.get('UUID') == r.get('target_node_uuid')][0].get('description')
            rel_desc = r.type
            print("    ({}) ---- [{}] ---->({})".format(start_node_desc, rel_desc, end_node_desc))
        print("\n")

def test_count_nodes_by_nodetype():
    num_nodes_by_nodetype = ob.count_nodes_by_nodetype()
    print(num_nodes_by_nodetype)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Testing prototype for Q1, NCATS competition, 2017')
    parser.add_argument('--test', dest='test_function_to_call')
    args = parser.parse_args()
    args_dict = vars(args)
    if args_dict.get('test_function_to_call', None) is not None:
        print('going to call function: ' + args_dict['test_function_to_call'])
        test_function_name = args_dict['test_function_to_call']
        try:
            test_function = globals()[test_function_name]
        except KeyError:
            sys.exit('Unable to find test function named: ' + test_function_name)
        test_running_time = timeit.timeit(lambda: test_function(), number=1)
        print('running time for test: ' + str(test_running_time))
