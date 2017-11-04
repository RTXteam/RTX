from .Orangeboard import Orangeboard
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryPC2 import QueryPC2
from QueryUniprot import QueryUniprot

query_omim_obj = QueryOMIM()
query_mygene_obj = QueryMyGene()

genetic_condition_mim_id = 603903  # sickle-cell anemia
target_disease_disont_id = 12365  # malaria

master_node_is_expanded = dict()

master_rel_is_directed = {"genetic_cond_affects": True,
                          "is_member_of": True}

master_rel_ids_in_orangeboard = {"genetic_cond_affects": dict(),
                                 "is_member_of": dict()}

master_node_ids_in_orangeboard = {"mim": dict(),
                                  "disont": dict(),
                                  "uniprot": dict(),
                                  "gene": dict(),
                                  "reactome": dict()}


def is_expanded(node_uuid):
    return master_node_is_expanded[node_uuid]


def add_rel(orangeboard, rel_type, source_node_uuid, target_node_uuid):
    is_directed = master_rel_is_directed[rel_type]
    rel_uuid = orangeboard.add_rel(source_node_uuid,
                                   target_node_uuid,
                                   rel_type,
                                   is_directed)
    rel_key = source_node_uuid + "--" + target_node_uuid
    master_rel_ids_in_orangeboard[rel_type][rel_key] = rel_uuid
    return rel_uuid


def add_node(orangeboard, biotype, node_name):
    node_uuid = orangeboard.add_node(node_labels=set([biotype]),
                                     node_properties={'name': str(node_name),
                                                      'expanded': 'false'})
    master_node_ids_in_orangeboard[biotype][node_name] = node_uuid
    master_node_is_expanded[node_uuid] = False
    return node_uuid


def get_rel_if_in_orangeboard(source_node_uuid, target_node_uuid, rel_type):
    rel_type_map = master_rel_ids_in_orangeboard[rel_type]
    assert rel_type_map is not None

    rel_key = source_node_uuid + "--" + target_node_uuid
    # If no such key in dict, return None
    rel_uuid = rel_type_map.get(rel_key, None)

    if rel_uuid is None:
        # If `rel_type` is directed, `rel_key` must be "{source}--{target}"
        # If not directed, `rel_key` may be "{target}--{source}"
        if not master_rel_is_directed[rel_type]:
            rel_key = target_node_uuid + "--" + source_node_uuid
            rel_uuid = rel_type_map.get(rel_key, None)

    return rel_uuid


def add_rel_if_not_in_orangeboard(orangeboard, source_node_uuid, target_node_uuid, rel_type):
    rel_uuid = get_rel_if_in_orangeboard(source_node_uuid, target_node_uuid, rel_type)
    if rel_uuid is None:
        add_rel(orangeboard, rel_type, source_node_uuid, target_node_uuid)


def add_node_if_not_in_orangeboard(orangeboard, biotype, node_name):
    if node_name in master_node_ids_in_orangeboard[biotype]:
        node_uuid = master_node_ids_in_orangeboard[biotype][node_name]
    else:
        node_uuid = add_node(orangeboard, biotype, node_name)
    return node_uuid


def expand_reactome(orangeboard, node):
    source_node_uuid = node.get_uuid()

    reactome_id_str = node.get_bioname()
    proteins_set = QueryPC2.pathway_to_uniprot_ids(reactome_id_str)

    for uniprot_id in proteins_set:
        target_node_uuid = add_node_if_not_in_orangeboard(orangeboard, "uniprot", uniprot_id)
        add_rel_if_not_in_orangeboard(orangeboard, target_node_uuid, source_node_uuid, "is_member_of")


def expand_uniprot(orangeboard, node):
    source_node_uuid = node.get_uuid()

    uniprot_id_str = node.get_bioname()
    pathways_set_from_pc2 = QueryPC2.uniprot_id_to_reactome_pathways(uniprot_id_str)
    pathways_set_from_uniprot = QueryUniprot.uniprot_id_to_reactome_pathways(uniprot_id_str)
    pathways_set = pathways_set_from_pc2 | pathways_set_from_uniprot

    for pathway_id in pathways_set:
        target_node_uuid = add_node_if_not_in_orangeboard(orangeboard, "reactome", pathway_id)
        add_rel_if_not_in_orangeboard(orangeboard, source_node_uuid, target_node_uuid, "is_member_of")


def expand_mim(orangeboard, node):
    source_node_uuid = node.get_uuid()

    res_dict = query_omim_obj.disease_mim_to_gene_symbols_and_uniprot_ids(int(node.get_bioname()))
    uniprot_ids = res_dict["uniprot_ids"]
    gene_symbols = res_dict["gene_symbols"]
    for gene_symbol in gene_symbols:
        uniprot_id = query_mygene_obj.convert_gene_symbol_to_uniprot_id(gene_symbol)
        if uniprot_id is not None:
            uniprot_ids = uniprot_ids.union(uniprot_id)

    for uniprot_id in uniprot_ids:
        target_node_uuid = add_node_if_not_in_orangeboard(orangeboard, "uniprot", uniprot_id)
        add_rel_if_not_in_orangeboard(orangeboard, source_node_uuid, target_node_uuid, "genetic_cond_affects")


def expand_disont(orangeboard, node):
    print("expanding node: " + str(node))


def expand(orangeboard, node):
    node_type = node.get_biotype()

    method_name = "expand_" + node_type
    method_obj = globals()[method_name]  # dispatch to the correct function for expanding the node type
    method_obj(orangeboard, node)

    node_uuid = node.properties["UUID"]
    master_node_is_expanded[node_uuid] = True
    orangeboard.set_node_property(node_uuid, "expanded", "true")


def test():
    ob = Orangeboard()
    ob.clear()

    # add the initial genetic condition into the Orangeboard, as a "MIM" node
    add_node(ob, "mim", genetic_condition_mim_id)

    # add the initial target disease into the Orangeboard, as a "disease ontology" node
    add_node(ob, "disont", target_disease_disont_id)

    print("----------- first round of expansion ----------")
    for node in ob.get_all_nodes():
        if not node.is_expanded():
            expand(ob, node)

    print("----------- second round of expansion ----------")
    for node in ob.get_all_nodes():
        if not node.is_expanded():
            expand(ob, node)

    print("----------- third round of expansion ----------")
    for node in ob.get_all_nodes():
        if not node.is_expanded():
            expand(ob, node)

    ob.shutdown()
