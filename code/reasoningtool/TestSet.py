import argparse
import timeit
import requests_cache
import sys
from Orangeboard import Orangeboard
from BioNetExpander import BioNetExpander

requests_cache.install_cache('orangeboard')

ob = Orangeboard(debug=True)

master_rel_is_directed = {'disease_affects': True,
                          'is_member_of': True,
                          'is_parent_of': True,
                          'gene_assoc_with': True,
                          'phenotype_assoc_with': True,
                          'interacts_with': False,
                          'controls_expression_of': True,
                          'is_expressed_in': True,
                          'targets': True}

ob.set_dict_reltype_dirs(master_rel_is_directed)
ob.neo4j_set_url()
ob.neo4j_set_auth()

bne = BioNetExpander(ob)


def bigtest():
#    genetic_condition_mim_id = 'OMIM:603903'  # sickle-cell anemia
#    target_disease_disont_id = 'DOID:12365'  # malaria
    # cerebral malaria:  'DOID:14069'

    # genetic_condition_mim_id = 'OMIM:219700' # cystic fibrosis
#    target_disease_disont_id = 'DOID:1498' # cholera

    # genetic_condition_mim_id = 'OMIM:305900' # glucose-6-phosphate dehydrogenase (G6PD)
    # target_disease_disont_id = 'DOID:12365'   # malaria

    # genetic_condition_mim_id = 'OMIM:607786' # proprotein convertase, subtilisin/kexin-type, 9 (PCSK9)
    # target_disease_disont_id = 'DOID:13810'   # familial hypercholesterolemia

    # genetic_condition_mim_id = 'OMIM:184745' # kit ligard
    # target_disease_disont_id = 'DOID:2841' # asthma


    # add the initial target disease into the Orangeboard, as a 'disease ontology' node
    ob.add_node('disont_disease', 'DOID:12365', desc='malaria', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:1498', desc='cholera', seed_node_bool=True)

    print('----------- first round of expansion ----------')
    bne.expand_all_nodes()

    print('----------- second round of expansion ----------')
    bne.expand_all_nodes()

    print('----------- third round of expansion ----------')
    bne.expand_all_nodes()

    print('total number of nodes: ' + str(ob.count_nodes()))
    print('total number of edges: ' + str(ob.count_rels()))

    # add the initial genetic condition into the Orangeboard, as a 'MIM' node
    mim_node = ob.add_node('omim_disease', 'OMIM:603903', desc='sickle-cell anemia', seed_node_bool=True)

    print('----------- first round of expansion ----------')
    bne.expand_all_nodes()

    print('----------- second round of expansion ----------')
    bne.expand_all_nodes()

    print('----------- third round of expansion ----------')
    bne.expand_all_nodes()

    print('total number of nodes: ' + str(ob.count_nodes()))
    print('total number of edges: ' + str(ob.count_rels()))

    # push the entire graph to neo4j
    ob.neo4j_push()


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

def test_print_for_arash():

    # add the initial target disease into the Orangeboard, as a 'disease ontology' node
    ob.add_node('disont_disease', 'DOID:12365', desc='malaria', seed_node_bool=True)
#    ob.add_node('disont_disease', 'DOID:1498', desc='cholera')

    # add the initial genetic condition into the Orangeboard, as a 'MIM' node
    ob.add_node('omim_disease', 'OMIM:603903', desc='sickle-cell anemia')
#    ob.add_node('omim_disease', 'OMIM:219700', desc='cystic fibrosis')
    
    print('----------- first round of expansion ----------')
    bne.expand_all_nodes()

    print('----------- second round of expansion ----------')
    bne.expand_all_nodes()

    print('----------- third round of expansion ----------')
    bne.expand_all_nodes()

    print('total number of nodes: ' + str(ob.count_nodes()))
    print('total number of edges: ' + str(ob.count_rels()))

    print(ob.simple_print(), file=sys.stderr)
    
def lysine_test_6():
    ob.add_node('disont_disease', 'DOID:12365', desc='malaria', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:1498', desc='cholera', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:2841', desc='asthma', seed_node_bool=True)
    ob.add_node('disont_disease', 'DOID:526', desc='HIV', seed_node_bool=True)

    bne.expand_all_nodes()
    bne.expand_all_nodes()
    bne.expand_all_nodes()
    ob.neo4j_push()

    print("[lysine_test_6] count(Node) = {}".format(ob.count_nodes()))
    print("[lysine_test_6] count(Rel) = {}".format(ob.count_rels()))


def test_expand_phenont_phenotype():
    ob.add_node('phenont_phenotype', "HP:0000107", desc='Renal cyst', seed_node_bool=True)
    bne.expand_all_nodes()
    ob.neo4j_push()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Testing prototype for Q1, NCATS competition, 2017')
    parser.add_argument('--test', dest='test_function_to_call')
    args = parser.parse_args()
    args_dict = vars(args)
    if args_dict.get('test_function_to_call', None) is not None:
        print('going to call function: ' + args_dict['test_function_to_call'])
        print(timeit.timeit(lambda: globals()[args_dict['test_function_to_call']](), number=1))
