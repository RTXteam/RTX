import sys

if sys.version_info[0] < 3 or sys.version_info[1] < 5:
    print("This script requires Python version 3.5 or greater")
    sys.exit(1)

from Orangeboard import Orangeboard
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryPC2 import QueryPC2
from QueryUniprot import QueryUniprot
from QueryReactome import QueryReactome
from QueryDisont import QueryDisont
from QueryDisGeNet import QueryDisGeNet
from QueryGeneProf import QueryGeneProf

import argparse

query_omim_obj = QueryOMIM()
query_mygene_obj = QueryMyGene()

master_node_is_expanded = dict()

master_rel_is_directed = {"genetic_cond_affects": True,
                          "is_member_of": True,
                          "is_parent_of": True,
                          "gene_assoc_with": True}

master_rel_ids_in_orangeboard = {"genetic_cond_affects": dict(),
                                 "is_member_of": dict()}

master_node_ids_in_orangeboard = {"mim_geneticcond":  dict(),
                                  "disont_disease":   dict(),
                                  "uniprot_protein":  dict(),
                                  "gene":             dict(),
                                  "reactome_pathway": dict()}

def expand_reactome_pathway(orangeboard, node):
    reactome_id_str = node.name
    uniprot_ids_from_reactome_dict = QueryReactome.query_reactome_pathway_id_to_uniprot_ids_desc(reactome_id_str)
    rel_sourcedb_dict = dict.fromkeys(uniprot_ids_from_reactome_dict.keys(), "reactome")
    source_node = node
    for uniprot_id in uniprot_ids_from_reactome_dict.keys():
        target_node = orangeboard.add_node("uniprot_protein", uniprot_id, desc=uniprot_ids_from_reactome_dict[uniprot_id])
        orangeboard.add_rel("is_member_of", rel_sourcedb_dict[uniprot_id], target_node, source_node)
#    uniprot_ids_from_pc2 = QueryPC2.pathway_id_to_uniprot_ids(reactome_id_str)  ## very slow query

def expand_uniprot_protein(orangeboard, node):
    uniprot_id_str = node.name
#    pathways_set_from_pc2 = QueryPC2.uniprot_id_to_reactome_pathways(uniprot_id_str)  ## suspect these pathways are too high-level and not useful
    pathways_dict_from_reactome = QueryReactome.query_uniprot_id_to_reactome_pathway_ids_desc(uniprot_id_str)
    pathways_dict_sourcedb = dict.fromkeys(pathways_dict_from_reactome.keys(), "reactome_pathway")
#    pathways_set_from_uniprot = QueryUniprot.uniprot_id_to_reactome_pathways(uniprot_id_str)  ## doesn't provide pathway descriptions; see if we can get away with not using it?
    node1 = node
    for pathway_id in pathways_dict_from_reactome.keys():
        target_node = orangeboard.add_node("reactome_pathway", pathway_id, desc=pathways_dict_from_reactome[pathway_id])
        orangeboard.add_rel("is_member_of", pathways_dict_sourcedb[pathway_id], node1, target_node)
    gene_symbols_set = query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id_str)
    for gene_symbol in gene_symbols_set:
        regulator_gene_symbols_set = QueryGeneProf.gene_symbol_to_transcription_factor_gene_symbols(gene_symbol)
        for reg_gene_symbol in regulator_gene_symbols_set:
            reg_uniprot_ids_set = query_mygene_obj.convert_gene_symbol_to_uniprot_id(reg_gene_symbol)
            for reg_uniprot_id in reg_uniprot_ids_set:
                node2 = orangeboard.add_node("uniprot_protein", reg_uniprot_id, desc=reg_gene_symbol)
                orangeboard.add_rel("regulates", "GeneProf", node2, node1)

def expand_mim_geneticcond(orangeboard, node):
    res_dict = query_omim_obj.disease_mim_to_gene_symbols_and_uniprot_ids(int(node.name))
    uniprot_ids = res_dict["uniprot_ids"]
    gene_symbols = res_dict["gene_symbols"]
    if len(uniprot_ids)==0 and len(gene_symbols)==0:
        return  ## nothing else to do, for this MIM number
    uniprot_ids_to_gene_symbols_dict = dict()
    for gene_symbol in gene_symbols:
        uniprot_ids = query_mygene_obj.convert_gene_symbol_to_uniprot_id(gene_symbol)
        for uniprot_id in uniprot_ids:
            uniprot_ids_to_gene_symbols_dict[uniprot_id] = gene_symbol
    for uniprot_id in uniprot_ids:
        gene_symbol = query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id)
        if gene_symbol is not None:
            gene_symbol_str = ';'.join(gene_symbol)
            uniprot_ids_to_gene_symbols_dict[uniprot_id]=gene_symbol_str
    source_node = node
    for uniprot_id in uniprot_ids_to_gene_symbols_dict.keys():
        target_node = orangeboard.add_node("uniprot_protein", uniprot_id, desc=uniprot_ids_to_gene_symbols_dict[uniprot_id])
#        print("target node for uniprot id: " + uniprot_id + "; " + str(target_node.expanded))
        orangeboard.add_rel("genetic_cond_affects", "OMIM", source_node, target_node)

def expand_disont_disease(orangeboard, node):
    disont_id = node.name
    child_disease_ids_dict = QueryDisont.query_disont_to_child_disonts_desc(disont_id)
    for child_disease_id in child_disease_ids_dict.keys():
        target_node = orangeboard.add_node("disont_disease", child_disease_id, desc=child_disease_ids_dict[child_disease_id])
        orangeboard.add_rel("is_parent_of", "DiseaseOntology", node, target_node)
    mesh_ids_set = QueryDisont.query_disont_to_mesh_id(disont_id)
    for mesh_id in mesh_ids_set:
        uniprot_ids_dict = QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc(mesh_id)
        for uniprot_id in uniprot_ids_dict.keys():
            source_node = orangeboard.add_node("uniprot_protein", uniprot_id, desc=uniprot_ids_dict[uniprot_id])
            orangeboard.add_rel("gene_assoc_with", "DisGeNet", source_node, node)
## TODO:  add node for uniprot_id here

def expand_node(orangeboard, node):
    node_type = node.nodetype
    method_name = "expand_" + node_type
    method_obj = globals()[method_name]  ## dispatch to the correct function for expanding the node type
    method_obj(orangeboard, node)
    node.expanded = True

def expand_all_nodes(orangeboard):
    for node in orangeboard.get_all_nodes_for_current_seed_node():
        if not node.expanded:
            expand_node(orangeboard, node)


def bigtest():
    genetic_condition_mim_id = 603903  # sickle-cell anemia
    target_disease_disont_id = 'DOID:12365'   # malaria
    ## cerebral malaria:  D014069

    # genetic_condition_mim_id = 219700 # cystic fibrosis
    # target_disease_disont_id = 'DOID:1498' # cholera

    # genetic_condition_mim_id = 305900 # glucose-6-phosphate dehydrogenase (G6PD)
    # target_disease_disont_id = 'DOID:12365'   # malaria

    # genetic_condition_mim_id = 607786 # proprotein convertase, subtilisin/kexin-type, 9 (PCSK9)
    # target_disease_disont_id = 'DOID:13810'   # familial hypercholesterolemia

    # genetic_condition_mim_id = 184745 # kit ligard
    # target_disease_disont_id = 'DOID:2841' # asthma

    ob = Orangeboard(master_rel_is_directed, debug=True)

    ## add the initial target disease into the Orangeboard, as a "disease ontology" node
    disease_node = ob.add_node("disont_disease", target_disease_disont_id, desc="malaria", seed_node_bool=True)

    print("----------- first round of expansion ----------")
    expand_all_nodes(ob)

    print("----------- second round of expansion ----------")
    expand_all_nodes(ob)

    print("----------- third round of expansion ----------")
    expand_all_nodes(ob)

    print("total number of nodes: " + str(ob.count_nodes()))
    print("total number of edges: " + str(ob.count_rels()))

    ## add the initial genetic condition into the Orangeboard, as a "MIM" node
    mim_node = ob.add_node("mim_geneticcond", genetic_condition_mim_id, desc="sickle-cell anemia", seed_node_bool=True)

    print("----------- first round of expansion ----------")
    expand_all_nodes(ob)

    print("----------- second round of expansion ----------")
    expand_all_nodes(ob)

    print("----------- third round of expansion ----------")
    expand_all_nodes(ob)

    print("total number of nodes: " + str(ob.count_nodes()))
    print("total number of edges: " + str(ob.count_rels()))

    # push the entire graph to neo4j
    ob.neo4j_push()

    # clear out the neo4j graph derived from the MIM seed node
    #ob.neo4j_clear(mim_node)


def test_description_mim():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node("mim_geneticcond", "603903", desc='sickle-cell anemia', seed_node_bool=True)
    expand_mim_geneticcond(ob, node)
    ob.neo4j_push()

def test_description_uniprot():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node("uniprot_protein", "P68871", desc='HBB', seed_node_bool=True)
    print(ob.__str__())
    expand_uniprot_protein(ob, node)
    ob.neo4j_push()

def test_description_disont():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node("disont_disease", "DOID:12365", desc='malaria', seed_node_bool=True)
    expand_disont_disease(ob, node)
    ob.neo4j_push()

def test_description_disont2():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node("disont_disease", "DOID:9352", desc='foobar', seed_node_bool=True)
    expand_node(ob)
    expand_node(ob)
    expand_node(ob)
    ob.neo4j_push()

def test_add_mim():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node("mim_geneticcond", "603903", desc='sickle-cell anemia', seed_node_bool=True)
    expand_mim_geneticcond(ob, node)
    ob.neo4j_push()

def test_issue2():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    node = ob.add_node("mim_geneticcond", "603933", desc='sickle-cell anemia', seed_node_bool=True)
    expand_mim_geneticcond(ob, node)

def test_issue3():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    disease_node = ob.add_node("disont_disease", 'DOID:9352', desc="foo", seed_node_bool=True)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    expand_all_nodes(ob)

def test_issue6():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    ob.add_node("mim_geneticcond", '605027', desc="LYMPHOMA, NON-HODGKIN, FAMILIAL", seed_node_bool=True)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    expand_all_nodes(ob)

def test_issue7():
    ob = Orangeboard(master_rel_is_directed, debug=True)
    ob.add_node("mim_geneticcond", '605275', desc="NOONAN SYNDROME 2; NS2", seed_node_bool=True)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    expand_all_nodes(ob)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="prototype reasoning tool for Q1, NCATS competition, 2017")
    parser.add_argument('--test', dest='test_function_to_call')
    args = parser.parse_args()
    args_dict = vars(args)
    if args_dict.get("test_function_to_call", None) is not None:
        print("going to call function: " + args_dict["test_function_to_call"])
        globals()[args_dict["test_function_to_call"]]()
