from Orangeboard import Orangeboard
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryPC2 import QueryPC2
from QueryUniprot import QueryUniprot
from QueryReactome import QueryReactome
from QueryDisont import QueryDisont
from QueryDisGeNet import QueryDisGeNet

query_omim_obj = QueryOMIM()
query_mygene_obj = QueryMyGene()

genetic_condition_mim_id = 603903  # sickle-cell anemia
target_disease_disont_id = 12365   # malaria
## cerebral malaria:  D014069

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
#    uniprot_ids_from_pc2 = QueryPC2.pathway_id_to_uniprot_ids(reactome_id_str)  ## very slow query
    uniprot_ids_from_reactome = QueryReactome.query_reactome_pathway_id_to_uniprot_ids(reactome_id_str)
    uniprot_ids_dict = dict.fromkeys(uniprot_ids_from_reactome, "reactome_pathway")
    uniprot_ids = uniprot_ids_dict.keys()
    source_node = node
    for uniprot_id in uniprot_ids:
        target_node = orangeboard.add_node("uniprot_protein", uniprot_id)
        orangeboard.add_rel("is_member_of", uniprot_ids_dict[uniprot_id], target_node, source_node)
        
def expand_uniprot_protein(orangeboard, node):
    uniprot_id_str = node.name
#    pathways_set_from_pc2 = QueryPC2.uniprot_id_to_reactome_pathways(uniprot_id_str)  ## suspect these pathways are too high-level and not useful
    pathways_set_from_reactome = QueryReactome.query_uniprot_id_to_reactome_pathway_ids(uniprot_id_str)
    pathways_dict = dict.fromkeys(pathways_set_from_reactome, "reactome_pathway")
    pathways_set_from_uniprot = QueryUniprot.uniprot_id_to_reactome_pathways(uniprot_id_str)
    for pathway_id in pathways_set_from_uniprot:
        if pathways_dict.get(pathway_id, None) is None:
            pathways_dict[pathway_id] = "uniprotkb"
    pathways_set = pathways_dict.keys()
    source_node = node
    for pathway_id in pathways_set:
#        print(pathway_id)
        target_node = orangeboard.add_node("reactome_pathway", pathway_id)
        orangeboard.add_rel("is_member_of", pathways_dict[pathway_id], source_node, target_node)
        
def expand_mim_geneticcond(orangeboard, node):
    res_dict = query_omim_obj.disease_mim_to_gene_symbols_and_uniprot_ids(int(node.name))
    uniprot_ids = res_dict["uniprot_ids"]
    gene_symbols = res_dict["gene_symbols"]
    for gene_symbol in gene_symbols:
        uniprot_id = query_mygene_obj.convert_gene_symbol_to_uniprot_id(gene_symbol)
        if uniprot_id is not None:
            uniprot_ids = uniprot_ids.union(uniprot_id)
    source_node = node
    for uniprot_id in uniprot_ids:
        target_node = orangeboard.add_node("uniprot_protein", uniprot_id)
        orangeboard.add_rel("genetic_cond_affects", "OMIM", source_node, target_node)

def expand_disont_disease(orangeboard, node):
    disont_id = int(node.name)
    child_disease_ids = QueryDisont.query_disont_to_child_disonts(disont_id)
    for child_disease_id in child_disease_ids:
        target_node = orangeboard.add_node("disont_disease", str(child_disease_id))
        orangeboard.add_rel("is_parent_of", "DiseaseOntology", node, target_node)
    mesh_ids_set = QueryDisont.query_disont_to_mesh_id(disont_id)
    for mesh_id in mesh_ids_set:
        uniprot_ids_set = QueryDisGeNet.query_mesh_id_to_uniprot_ids(mesh_id)
        for uniprot_id in uniprot_ids_set:
            source_node = orangeboard.add_node("uniprot_protein", uniprot_id)
            orangeboard.add_rel("gene_assoc_with", "DisGeNet", source_node, node)
## TODO:  add node for uniprot_id here

    
def expand(orangeboard, node):
    node_type = node.nodetype
    method_name = "expand_" + node_type
    method_obj = globals()[method_name]  ## dispatch to the correct function for expanding the node type
    method_obj(orangeboard, node)
    node.expanded = True

ob = Orangeboard(debug=False)

ob.set_reltype_dirs(master_rel_is_directed)

# # ## add the initial target disease into the Orangeboard, as a "disease ontology" node
# disease_node = ob.add_node("disont_disease", target_disease_disont_id, seed_node=True)

# ## add the initial genetic condition into the Orangeboard, as a "MIM" node

# print("----------- first round of expansion ----------")
# for node in ob.get_all_nodes_for_current_seed_node():
#     if not node.expanded:
#         expand(ob, node)
    
# print("----------- second round of expansion ----------")
# for node in ob.get_all_nodes_for_current_seed_node():
#     if not node.expanded:
#         expand(ob, node)

# print(ob.get_node("uniprot_protein", "P09601"))
# print(ob.count_rels_for_node_slow(ob.get_node("uniprot_protein", "P09601")))


mim_node = ob.add_node("mim_geneticcond", genetic_condition_mim_id, seed_node=True)

print("----------- first round of expansion ----------")
for node in ob.get_all_nodes_for_current_seed_node():
    if not node.expanded:
        expand(ob, node)
    
print("----------- second round of expansion ----------")
for node in ob.get_all_nodes_for_current_seed_node():
    if not node.expanded:
        expand(ob, node)

print("----------- third round of expansion ----------")
for node in ob.get_all_nodes_for_current_seed_node():
    if not node.expanded:
        expand(ob, node)

#exit()

# push the entire graph to neo4j
#ob.neo4j_push()

print(ob.count_rels_for_node_slow(ob.get_node("uniprot_protein", "P09601")))

# clear out the neo4j graph derived from the MIM seed node
#ob.neo4j_clear(mim_node)

