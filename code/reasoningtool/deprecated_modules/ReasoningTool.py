""" This module defines the ReasoningTool functions which carry out the expanding
 process from all types of nodes. It can calculate the joint of specific rounds
 of expanding. Moreover, it is responsible for connection with Neo4j database and
 handle the node, relation pushing and configuration to Neo4j databse.
"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import sys
import argparse
import requests_cache
import timeit
import os
import re
import os
from Orangeboard import Orangeboard
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryUniprot import QueryUniprot
from QueryReactome import QueryReactome
from QueryDisont import QueryDisont
from QueryDisGeNet import QueryDisGeNet
from QueryGeneProf import QueryGeneProf
from QueryBioLink import QueryBioLink
from QueryMiRGate import QueryMiRGate
from QueryMiRBase import QueryMiRBase
from QueryPharos import QueryPharos
## from QueryPC2 import QueryPC2  ## not currently using; so comment out until such time as we decide to use it

from timeit import default_timer as timer

## refuse to run in python version < 3.5 (in case accidentally invoked using "python" rather than "python3")
if sys.version_info[0] < 3 or sys.version_info[1] < 5:
    print("This script requires Python version 3.5 or greater")
    sys.exit(1)

#requests_cache.install_cache('orangeboard')
# specifiy the path of orangeboard database
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
dbpath = os.path.sep.join([*pathlist[:(RTXindex+1)],'data','orangeboard'])
requests_cache.install_cache(dbpath)

query_omim_obj = QueryOMIM()
query_mygene_obj = QueryMyGene(debug=False)

master_rel_is_directed = {'disease_affects': True,
                          'is_member_of': True,
                          'is_parent_of': True,
                          'gene_assoc_with': True,
                          'phenotype_assoc_with': True,
                          'interacts_with': False,
                          'controls_expression_of': True,
                          'is_expressed_in': True,
                          'targets': True}

master_rel_ids_in_orangeboard = {'disease_affects': dict(),
                                 'is_member_of': dict()}

master_node_ids_in_orangeboard = {'omim_disease': dict(),
                                  'disont_disease': dict(),
                                  'uniprot_protein': dict(),
                                  'reactome_pathway': dict(),
                                  'phenont_phenotype': dict(),
                                  'ncbigene_microrna': dict(),
                                  'anatont_anatomy': dict(),
                                  'pharos_drug': dict()}


def expand_pharos_drug(orangeboard, node):
    drug_name = node.name

    targets = QueryPharos.query_drug_name_to_targets(drug_name)
    for target in targets:
        uniprot_id = QueryPharos.query_target_uniprot_accession(str(target["id"]))

        target_node = orangeboard.add_node('uniprot_protein', uniprot_id, desc=target["name"])
        orangeboard.add_rel('targets', 'Pharos', node, target_node)


def is_mir(gene_symbol):
    return re.match('MIR\d.*', gene_symbol) is not None or re.match('MIRLET\d.*', gene_symbol) is not None


def expand_ncbigene_microrna(orangeboard, node):
    ncbi_gene_id = node.name
    assert 'NCBIGene:' in ncbi_gene_id

    anatomy_dict = QueryBioLink.get_anatomies_for_gene(ncbi_gene_id)
    for anatomy_id, anatomy_desc in anatomy_dict.items():
        anatomy_node = orangeboard.add_node('anatont_anatomy', anatomy_id, desc=anatomy_desc)
        orangeboard.add_rel('is_expressed_in', 'BioLink', node, anatomy_node)

    disease_ids_dict = QueryBioLink.get_diseases_for_gene_desc(ncbi_gene_id)
    for disease_id in disease_ids_dict.keys():
        if 'OMIM:' in disease_id:
            disease_node = orangeboard.add_node('omim_disease', disease_id, desc=disease_ids_dict[disease_id])
            orangeboard.add_rel('gene_assoc_with', 'BioLink', node, disease_node)
        else:
            if 'DOID:' in disease_id:
                disease_node = orangeboard.add_node('disont_disease', disease_id, desc=disease_ids_dict[disease_id])
                orangeboard.add_rel('gene_assoc_with', 'BioLink', node, disease_node)
            else:
                print('Warning: unexpected disease ID: ' + disease_id)

    phenotype_ids_dict = QueryBioLink.get_phenotypes_for_gene_desc(ncbi_gene_id)
    for phenotype_id in phenotype_ids_dict.keys():
        phenotype_node = orangeboard.add_node('phenont_phenotype', phenotype_id, desc=phenotype_ids_dict[phenotype_id])
        orangeboard.add_rel('gene_assoc_with', 'BioLink', node, phenotype_node)

    mirbase_ids = query_mygene_obj.convert_entrez_gene_ID_to_mirbase_ID(int(ncbi_gene_id.replace('NCBIGene:', '')))
    for mirbase_id in mirbase_ids:
        mature_mir_ids = QueryMiRBase.convert_mirbase_id_to_mature_mir_ids(mirbase_id)
        for mature_mir_id in mature_mir_ids:
            target_gene_symbols = QueryMiRGate.get_gene_symbols_regulated_by_microrna(mature_mir_id)
            for target_gene_symbol in target_gene_symbols:
                uniprot_ids = query_mygene_obj.convert_gene_symbol_to_uniprot_id(target_gene_symbol)

                for uniprot_id in uniprot_ids:
                    target_prot_node = orangeboard.add_node('uniprot_protein', uniprot_id, desc=target_gene_symbol)
                    orangeboard.add_rel('controls_expression_of', 'miRGate', node, target_prot_node)

                if len(uniprot_ids) == 0:
                    if is_mir(target_gene_symbol):
                        target_ncbi_entrez_ids = query_mygene_obj.convert_gene_symbol_to_entrez_gene_ID(
                            target_gene_symbol)
                        for target_ncbi_entrez_id in target_ncbi_entrez_ids:
                            target_mir_node = orangeboard.add_node('ncbigene_microrna',
                                                                   'NCBIGene:' + str(target_ncbi_entrez_id),
                                                                   desc=target_gene_symbol)
                            orangeboard.add_rel('controls_expression_of', 'miRGate', node, target_mir_node)


def expand_reactome_pathway(orangeboard, node):
    reactome_id_str = node.name
    uniprot_ids_from_reactome_dict = QueryReactome.query_reactome_pathway_id_to_uniprot_ids_desc(reactome_id_str)
    rel_sourcedb_dict = dict.fromkeys(uniprot_ids_from_reactome_dict.keys(), 'reactome')
    source_node = node
    for uniprot_id in uniprot_ids_from_reactome_dict.keys():
        target_node = orangeboard.add_node('uniprot_protein', uniprot_id,
                                           desc=uniprot_ids_from_reactome_dict[uniprot_id])
        orangeboard.add_rel('is_member_of', rel_sourcedb_dict[uniprot_id], target_node, source_node)


# uniprot_ids_from_pc2 = QueryPC2.pathway_id_to_uniprot_ids(reactome_id_str)  ## very slow query

def expand_anatont_anatomy(orangeboard, node):
    pass


def expand_uniprot_protein(orangeboard, node):
    uniprot_id_str = node.name
    #    pathways_set_from_pc2 = QueryPC2.uniprot_id_to_reactome_pathways(uniprot_id_str)  ## suspect these pathways are too high-level and not useful
    #    pathways_set_from_uniprot = QueryUniprot.uniprot_id_to_reactome_pathways(uniprot_id_str)  ## doesn't provide pathway descriptions; see if we can get away with not using it?
    ## protein-pathway membership:
    pathways_dict_from_reactome = QueryReactome.query_uniprot_id_to_reactome_pathway_ids_desc(uniprot_id_str)
    pathways_dict_sourcedb = dict.fromkeys(pathways_dict_from_reactome.keys(), 'reactome_pathway')
    node1 = node
    for pathway_id in pathways_dict_from_reactome.keys():
        target_node = orangeboard.add_node('reactome_pathway', pathway_id, desc=pathways_dict_from_reactome[pathway_id])
        orangeboard.add_rel('is_member_of', pathways_dict_sourcedb[pathway_id], node1, target_node)
    gene_symbols_set = query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id_str)
    for gene_symbol in gene_symbols_set:
        ## protein-DNA (i.e., gene regulatory) interactions:
        regulator_gene_symbols_set = QueryGeneProf.gene_symbol_to_transcription_factor_gene_symbols(gene_symbol)
        for reg_gene_symbol in regulator_gene_symbols_set:
            reg_uniprot_ids_set = query_mygene_obj.convert_gene_symbol_to_uniprot_id(reg_gene_symbol)
            for reg_uniprot_id in reg_uniprot_ids_set:
                node2 = orangeboard.add_node('uniprot_protein', reg_uniprot_id, desc=reg_gene_symbol)
                if node2.uuid != node1.uuid:
                    orangeboard.add_rel('controls_expression_of', 'GeneProf', node2, node1)
        ## microrna-gene interactions:
        microrna_regulators = QueryMiRGate.get_microrna_ids_that_regulate_gene_symbol(gene_symbol)
        for microrna_id in microrna_regulators:
            mir_gene_symbol = QueryMiRBase.convert_mirbase_id_to_mir_gene_symbol(microrna_id)
            if mir_gene_symbol is not None:
                mir_entrez_gene_ids = query_mygene_obj.convert_gene_symbol_to_entrez_gene_ID(mir_gene_symbol)
                if len(mir_entrez_gene_ids) > 0:
                    for mir_entrez_gene_id in mir_entrez_gene_ids:
                        mir_node = orangeboard.add_node('ncbigene_microrna', 'NCBIGene:' + str(mir_entrez_gene_id),
                                                        desc=mir_gene_symbol)
                        orangeboard.add_rel('controls_expression_of', 'miRGate', mir_node, node)

    entrez_gene_id = query_mygene_obj.convert_uniprot_id_to_entrez_gene_ID(uniprot_id_str)
    if len(entrez_gene_id) > 0:
        entrez_gene_id_str = 'NCBIGene:' + str(next(iter(entrez_gene_id)))

        ## protein-to-anatomy associations:
        anatomy_dict = QueryBioLink.get_anatomies_for_gene(entrez_gene_id_str)
        for anatomy_id, anatomy_desc in anatomy_dict.items():
            anatomy_node = orangeboard.add_node('anatont_anatomy', anatomy_id, desc=anatomy_desc)
            orangeboard.add_rel('is_expressed_in', 'BioLink', node, anatomy_node)

        ## protein-disease associations:
        disont_id_dict = QueryBioLink.get_diseases_for_gene_desc(entrez_gene_id_str)
        for disont_id in disont_id_dict.keys():
            if 'DOID:' in disont_id:
                node2 = orangeboard.add_node('disont_disease', disont_id, desc=disont_id_dict[disont_id])
                orangeboard.add_rel('gene_assoc_with', 'BioLink', node1, node2)
            else:
                if 'OMIM:' in disont_id:
                    node2 = orangeboard.add_node('omim_disease', disont_id, desc=disont_id_dict[disont_id])
                    orangeboard.add_rel('gene_assoc_with', 'BioLink', node1, node2)
        ## protein-phenotype associations:
        phenotype_id_dict = QueryBioLink.get_phenotypes_for_gene_desc(entrez_gene_id_str)
        for phenotype_id_str in phenotype_id_dict.keys():
            node2 = orangeboard.add_node('phenont_phenotype', phenotype_id_str,
                                         desc=phenotype_id_dict[phenotype_id_str])
            orangeboard.add_rel('gene_assoc_with', 'BioLink', node1, node2)
    ## protein-protein interactions:
    int_dict = QueryReactome.query_uniprot_id_to_interacting_uniprot_ids(uniprot_id_str)
    for int_uniprot_id in int_dict.keys():
        int_alias = int_dict[int_uniprot_id]
        node2 = orangeboard.add_node('uniprot_protein', int_uniprot_id, desc=int_alias)
        if node2.uuid != node1.uuid:
            orangeboard.add_rel('interacts_with', 'reactome', node1, node2)


def expand_phenont_phenotype(orangeboard, node):
    # EXPAND PHENOTYPE -> ANATOMY
    phenotype_id = node.name

    anatomy_dict = QueryBioLink.get_anatomies_for_phenotype(phenotype_id)
    for anatomy_id, anatomy_desc in anatomy_dict.items():
        anatomy_node = orangeboard.add_node('anatont_anatomy', anatomy_id, desc=anatomy_desc)
        orangeboard.add_rel('phenotype_assoc_with', 'BioLink', node, anatomy_node)

        ## TODO:  expand phenotype to child phenotypes, through the phenotype ontology as we do for disease ontology


def expand_omim_disease(orangeboard, node):
    res_dict = query_omim_obj.disease_mim_to_gene_symbols_and_uniprot_ids(node.name)
    uniprot_ids = res_dict['uniprot_ids']
    gene_symbols = res_dict['gene_symbols']
    if len(uniprot_ids) == 0 and len(gene_symbols) == 0:
        return  ## nothing else to do, for this MIM number
    uniprot_ids_to_gene_symbols_dict = dict()
    for gene_symbol in gene_symbols:
        uniprot_ids = query_mygene_obj.convert_gene_symbol_to_uniprot_id(gene_symbol)
        if len(uniprot_ids) == 0:
            ## this might be a microRNA
            if is_mir(gene_symbol):
                entrez_gene_ids = query_mygene_obj.convert_gene_symbol_to_entrez_gene_ID(gene_symbol)
                if len(entrez_gene_ids) > 0:
                    for entrez_gene_id in entrez_gene_ids:
                        curie_entrez_gene_id = 'NCBIGene:' + str(entrez_gene_id)
                        node2 = orangeboard.add_node('ncbigene_microrna', curie_entrez_gene_id, desc=gene_symbol)
                        orangeboard.add_rel('disease_affects', 'OMIM', node, node2)
        for uniprot_id in uniprot_ids:
            uniprot_ids_to_gene_symbols_dict[uniprot_id] = gene_symbol
    for uniprot_id in uniprot_ids:
        gene_symbol = query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id)
        if gene_symbol is not None:
            gene_symbol_str = ';'.join(gene_symbol)
            uniprot_ids_to_gene_symbols_dict[uniprot_id] = gene_symbol_str
    source_node = node
    for uniprot_id in uniprot_ids_to_gene_symbols_dict.keys():
        target_node = orangeboard.add_node('uniprot_protein', uniprot_id,
                                           desc=uniprot_ids_to_gene_symbols_dict[uniprot_id])
        orangeboard.add_rel('disease_affects', 'OMIM', source_node, target_node)


def expand_disont_disease(orangeboard, node):
    disont_id = node.name
    child_disease_ids_dict = QueryDisont.query_disont_to_child_disonts_desc(disont_id)
    for child_disease_id in child_disease_ids_dict.keys():
        target_node = orangeboard.add_node('disont_disease', child_disease_id,
                                           desc=child_disease_ids_dict[child_disease_id])
        orangeboard.add_rel('is_parent_of', 'DiseaseOntology', node, target_node)
    mesh_ids_set = QueryDisont.query_disont_to_mesh_id(disont_id)
    for mesh_id in mesh_ids_set:
        uniprot_ids_dict = QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc(mesh_id)
        for uniprot_id in uniprot_ids_dict.keys():
            source_node = orangeboard.add_node('uniprot_protein', uniprot_id, desc=uniprot_ids_dict[uniprot_id])
            orangeboard.add_rel('gene_assoc_with', 'DisGeNet', source_node, node)
    ## query for phenotypes associated with this disease
    phenotype_id_dict = QueryBioLink.get_phenotypes_for_disease_desc(disont_id)
    for phenotype_id_str in phenotype_id_dict.keys():
        phenotype_node = orangeboard.add_node('phenont_phenotype', phenotype_id_str,
                                              desc=phenotype_id_dict[phenotype_id_str])
        orangeboard.add_rel('phenotype_assoc_with', 'BioLink', phenotype_node, node)


def expand_node(orangeboard, node):
    node_type = node.nodetype
    method_name = 'expand_' + node_type
    method_obj = globals()[method_name]  ## dispatch to the correct function for expanding the node type
    method_obj(orangeboard, node)
    node.expanded = True


def expand_all_nodes(orangeboard):
    nodes = orangeboard.get_all_nodes_for_current_seed_node()
    for node in nodes:
        if not node.expanded:
            expand_node(orangeboard, node)


def bigtest():
    genetic_condition_mim_id = 'OMIM:603903'  # sickle-cell anemia
    target_disease_disont_id = 'DOID:12365'  # malaria
    ## cerebral malaria:  'DOID:014069'

    # genetic_condition_mim_id = 'OMIM:219700' # cystic fibrosis
    # target_disease_disont_id = 'DOID:1498' # cholera

    # genetic_condition_mim_id = 'OMIM:305900' # glucose-6-phosphate dehydrogenase (G6PD)
    # target_disease_disont_id = 'DOID:12365'   # malaria

    # genetic_condition_mim_id = 'OMIM:607786' # proprotein convertase, subtilisin/kexin-type, 9 (PCSK9)
    # target_disease_disont_id = 'DOID:13810'   # familial hypercholesterolemia

    # genetic_condition_mim_id = 'OMIM:184745' # kit ligard
    # target_disease_disont_id = 'DOID:2841' # asthma

    ob = Orangeboard(master_rel_is_directed, debug=True)

    ## add the initial target disease into the Orangeboard, as a 'disease ontology' node
    disease_node = ob.add_node('disont_disease', target_disease_disont_id, desc='malaria', seed_node_bool=True)

    print('----------- first round of expansion ----------')
    expand_all_nodes(ob)

    print('----------- second round of expansion ----------')
    expand_all_nodes(ob)

    print('----------- third round of expansion ----------')
    expand_all_nodes(ob)

    print('total number of nodes: ' + str(ob.count_nodes()))
    print('total number of edges: ' + str(ob.count_rels()))

    ## add the initial genetic condition into the Orangeboard, as a 'MIM' node
    mim_node = ob.add_node('omim_disease', genetic_condition_mim_id, desc='sickle-cell anemia', seed_node_bool=True)

    print('----------- first round of expansion ----------')
    expand_all_nodes(ob)

    print('----------- second round of expansion ----------')
    expand_all_nodes(ob)

    print('----------- third round of expansion ----------')
    expand_all_nodes(ob)

    print('total number of nodes: ' + str(ob.count_nodes()))
    print('total number of edges: ' + str(ob.count_rels()))

    # push the entire graph to neo4j
    ob.neo4j_set_url()  # use default url
    ob.neo4j_set_auth()  # use default username/password
    ob.neo4j_push()

    # clear out the neo4j graph derived from the MIM seed node
    # ob.neo4j_clear(mim_node)


def test_description_mim():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node('omim_disease', 'OMIM:603903', desc='sickle-cell anemia', seed_node_bool=True)
    expand_omim_disease(ob, node)
    ob.neo4j_set_url()  # use default url
    ob.neo4j_set_auth()  # use default username/password
    ob.neo4j_push()


def test_description_uniprot():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node('uniprot_protein', 'P68871', desc='HBB', seed_node_bool=True)
    print(ob.__str__())
    expand_uniprot_protein(ob, node)
    ob.neo4j_set_url()  # use default url
    ob.neo4j_set_auth()  # use default username/password
    ob.neo4j_push()


def test_description_disont():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node('disont_disease', 'DOID:12365', desc='malaria', seed_node_bool=True)
    expand_disont_disease(ob, node)
    ob.neo4j_set_url()  # use default url
    ob.neo4j_set_auth()  # use default username/password
    ob.neo4j_push()


def test_description_disont2():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node('disont_disease', 'DOID:9352', desc='foobar', seed_node_bool=True)
    expand_disont_disease(ob, node)
    ob.neo4j_set_url()  # use default url
    ob.neo4j_set_auth()  # use default username/password
    ob.neo4j_push()


def test_add_mim():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node('omim_disease', 'OMIM:603903', desc='sickle-cell anemia', seed_node_bool=True)
    expand_omim_disease(ob, node)
    ob.neo4j_set_url()
    ob.neo4j_set_auth()
    ob.neo4j_push()


def test_issue2():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node('omim_disease', 'OMIM:603933', desc='sickle-cell anemia', seed_node_bool=True)
    expand_omim_disease(ob, node)


def test_issue3():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    disease_node = ob.add_node('disont_disease', 'DOID:9352', desc='foo', seed_node_bool=True)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    expand_all_nodes(ob)


def test_issue6():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    ob.add_node('omim_disease', 'OMIM:605027', desc='LYMPHOMA, NON-HODGKIN, FAMILIAL', seed_node_bool=True)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    expand_all_nodes(ob)


def test_issue7():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    ob.add_node('omim_disease', 'OMIM:605275', desc='NOONAN SYNDROME 2; NS2', seed_node_bool=True)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    expand_all_nodes(ob)


def test_issue9():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node1 = ob.add_node('uniprot_protein', 'P16887', desc='HBB')
    node2 = ob.add_node('uniprot_protein', 'P09601', desc='HMOX1')
    ob.add_rel('interacts_with', 'reactome', node1, node2)
    ob.neo4j_set_url()
    ob.neo4j_set_auth()
    ob.neo4j_push()


def test_microrna():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    ob.add_node('omim_disease', 'OMIM:613074', desc='deafness', seed_node_bool=True)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    ob.neo4j_set_url()
    ob.neo4j_set_auth()
    ob.neo4j_push()


def test_anatomy_1():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    mir96 = ob.add_node('ncbigene_microrna', 'NCBIGene:407053', desc='MIR96', seed_node_bool=True)

    expand_ncbigene_microrna(ob, mir96)
    ob.neo4j_set_url()  # use default url
    ob.neo4j_set_auth()  # use default username/password
    ob.neo4j_push()


def test_anatomy_2():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    hmox1 = ob.add_node('uniprot_protein', 'P09601', desc='HMOX1', seed_node_bool=True)

    expand_uniprot_protein(ob, hmox1)
    ob.neo4j_set_url()
    ob.neo4j_set_auth()
    ob.neo4j_push()


def test_anatomy_3():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    mkd = ob.add_node('phenont_phenotype', 'HP:0000003', desc='Multicystic kidney dysplasia', seed_node_bool=True)

    expand_phenont_phenotype(ob, mkd)
    ob.neo4j_set_url()
    ob.neo4j_set_auth()
    ob.neo4j_push()


def test_expand_pharos_drug():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    lovastatin = ob.add_node('pharos_drug', 'lovastatin', desc='lovastatin', seed_node_bool=True)

    expand_pharos_drug(ob, lovastatin)
    ob.neo4j_set_url()
    ob.neo4j_set_auth()
    ob.neo4j_push()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='prototype reasoning tool for Q1, NCATS competition, 2017')
    parser.add_argument('--test', dest='test_function_to_call')
    args = parser.parse_args()
    args_dict = vars(args)
    if args_dict.get('test_function_to_call', None) is not None:
        print('going to call function: ' + args_dict['test_function_to_call'])
        print(timeit.timeit(lambda: globals()[args_dict['test_function_to_call']](), number=1))
