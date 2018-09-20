""" This is a module to define class BioNetExpander.
BioNetExpander carries the function of expanding objects to objects (two objects
can belong to distinct types or same type) from multiple online sources.
BioNetExpander is capable of expanding from nodes of various types, including:
    * drug
    * gene
    * disease
    * pathway
    * anatomy
    * protein
    * phenotype
"""

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University',
__credits__ = ['Yao Yao', 'Stephen Ramsey', 'Zheng Liu']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

import re
from operator import methodcaller
import timeit
import argparse
import sys

from Orangeboard import Orangeboard
from QueryOMIM import QueryOMIM
from QueryMyGene import QueryMyGene
from QueryReactome import QueryReactome
from QueryDisont import QueryDisont
from QueryDisGeNet import QueryDisGeNet
from QueryGeneProf import QueryGeneProf
from QueryBioLink import QueryBioLink
from QueryMiRGate import QueryMiRGate
from QueryMiRBase import QueryMiRBase
from QueryPharos import QueryPharos
from QuerySciGraph import QuerySciGraph
from QueryChEMBL import QueryChEMBL
# from QueryUniprotExtended import QueryUniprotExtended
from QueryKEGG import QueryKEGG
from QueryUniprot import QueryUniprot
from DrugMapper import DrugMapper


class BioNetExpander:

    CURIE_PREFIX_TO_IRI_PREFIX = {"OMIM": "http://purl.obolibrary.org/obo/OMIM_",
                                  "UniProtKB": "http://identifiers.org/uniprot/",
                                  "NCBIGene": "https://www.ncbi.nlm.nih.gov/gene/",
                                  "HP": "http://purl.obolibrary.org/obo/HP_",
                                  "DOID": "http://purl.obolibrary.org/obo/DOID_",
                                  "REACT": "https://reactome.org/content/detail/",
                                  "CHEMBL.COMPOUND": "https://www.ebi.ac.uk/chembl/compound/inspect/",
                                  "UBERON": "http://purl.obolibrary.org/obo/UBERON_",
                                  "GO": "http://purl.obolibrary.org/obo/GO_",
                                  "CL": "http://purl.obolibrary.org/obo/CL_",
                                  "KEGG": "http://www.genome.jp/dbget-bin/www_bget?"}

    NODE_SIMPLE_TYPE_TO_CURIE_PREFIX = {"chemical_substance": "CHEMBL.COMPOUND",
                                        "protein": "UniProtKB",
                                        "genetic_condition": "OMIM",
                                        "anatomical_entity": "UBERON",
                                        "microRNA": "NCBIGene",
                                        "phenotypic_feature": "HP",
                                        "disease": "DOID",
                                        "pathway": "REACT",
                                        "biological_process": "GO",
                                        "cellular_component": "GO",
                                        "molecular_function": "GO",
                                        "metabolite": "KEGG"}

    MASTER_REL_IS_DIRECTED = {"subclass_of": True,
                              "gene_associated_with_condition": True,
                              "affects": True,
                              "regulates": True,
                              "expressed_in": True,
                              "physically_interacts_with": False,
                              "gene_mutations_contribute_to": True,
                              "participates_in": True,
                              "involved_in": True,
                              "has_phenotype": True,
                              "has_part": True,
                              "capable_of": True,
                              "indicated_for": True,
                              "contraindicated_for": True,
                              "causes_or_contributes_to": True,
                              'positively_regulates': True,
                              'negatively_regulates': True}

    GO_ONTOLOGY_TO_PREDICATE = {"biological_process": "involved_in",
                                "cellular_component": "expressed_in",
                                "molecular_function": "capable_of"}

    def __init__(self, orangeboard):
        orangeboard.set_dict_reltype_dirs(self.MASTER_REL_IS_DIRECTED)
        self.orangeboard = orangeboard
        self.query_omim_obj = QueryOMIM()
        self.query_mygene_obj = QueryMyGene(debug=False)
        self.gene_symbols_to_protein_nodes = dict()

    def add_node_smart(self, simple_node_type, name, seed_node_bool=False, desc=''):
        if name.endswith("PHENOTYPE") or name.startswith("MP:"):
            return None

        simple_node_type_fixed = simple_node_type
        if simple_node_type == "disease" and "OMIM:" in name:
            simple_node_type_fixed = "genetic_condition"

        curie_prefix = self.NODE_SIMPLE_TYPE_TO_CURIE_PREFIX[simple_node_type_fixed]
        if name.startswith("CL:"):
            curie_prefix = "CL"

        iri_prefix = self.CURIE_PREFIX_TO_IRI_PREFIX[curie_prefix]
        if ":" not in name:
            accession = name
            curie_id = curie_prefix + ":" + name
            iri = iri_prefix + name
        else:
            curie_id = name
            accession = name.split(":")[1]
            iri = iri_prefix + accession

        if simple_node_type == "protein" and desc == "":
            gene_symbol = QueryUniprot.get_protein_gene_symbol(curie_id)
            desc = gene_symbol

        node = None

        if simple_node_type == "protein":
            gene_symbol = desc
            if gene_symbol in self.gene_symbols_to_protein_nodes:
                node = self.gene_symbols_to_protein_nodes[gene_symbol]

        if node is None:
            if simple_node_type == "protein":
                protein_name = self.query_mygene_obj.get_protein_name(name)
                if protein_name == "None":
                    protein_name = desc
                node = self.orangeboard.add_node(simple_node_type,
                                                 name,
                                                 seed_node_bool,
                                                 protein_name)
            else:
                node = self.orangeboard.add_node(simple_node_type,
                                                 name,
                                                 seed_node_bool,
                                                 desc)

            extra_props = {"uri": iri,
                           "id": curie_id,
                           "accession": accession}

            assert ":" in curie_id
            
            if simple_node_type == "protein" or simple_node_type == "microRNA":
                extra_props["symbol"] = desc

            node.set_extra_props(extra_props)

            if simple_node_type == "protein":
                gene_symbol = desc
                self.gene_symbols_to_protein_nodes[gene_symbol] = node

        return node

    @staticmethod
    def is_mir(gene_symbol):
        return re.match('MIR\d.*', gene_symbol) is not None or re.match('MIRLET\d.*', gene_symbol) is not None

    def expand_metabolite(self, node):
        assert node.nodetype == "metabolite"
        metabolite_kegg_id = node.name
        ec_ids = QueryKEGG.map_kegg_compound_to_enzyme_commission_ids(metabolite_kegg_id)
        if len(ec_ids) > 0:
            if len(ec_ids) > 300:
                print("Warning: metabolite " + metabolite_kegg_id + " has a huge number of associated ECs: " + str(len(ec_ids)),
                      file=sys.stderr)
            for ec_id in ec_ids:
                uniprot_ids = QueryUniprot.map_enzyme_commission_id_to_uniprot_ids(ec_id)
                if len(uniprot_ids) > 0:
                    for uniprot_id in uniprot_ids:
                        gene_symbols = self.query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id)
                        if len(gene_symbols) > 0:
                            gene_symbol = ";".join(list(gene_symbols))
                            prot_node = self.add_node_smart("protein", uniprot_id, desc=gene_symbol)
                            if prot_node is not None:
                                self.orangeboard.add_rel("physically_interacts_with", "KEGG;UniProtKB", node, prot_node, extended_reltype="physically_interacts_with")

    def expand_chemical_substance(self, node):
        assert node.nodetype == "chemical_substance"
        compound_desc = node.desc
        target_uniprot_ids = QueryChEMBL.get_target_uniprot_ids_for_drug(compound_desc)
        if target_uniprot_ids is not None:
            for target_uniprot_id_curie in target_uniprot_ids.keys():
                target_uniprot_id = target_uniprot_id_curie.replace("UniProtKB:", "")
                probability = target_uniprot_ids[target_uniprot_id]
                gene_names = self.query_mygene_obj.convert_uniprot_id_to_gene_symbol(target_uniprot_id)
                node_desc = ';'.join(list(gene_names))
                target_node = self.add_node_smart('protein', target_uniprot_id, desc=node_desc)
                if target_node is not None:
                    self.orangeboard.add_rel('physically_interacts_with', 'ChEMBL', node, target_node, prob=probability, extended_reltype='targets')

        targets = QueryPharos.query_drug_name_to_targets(compound_desc)
        if targets is not None:
            for target in targets:
                uniprot_id = QueryPharos.query_target_uniprot_accession(str(target["id"]))
                assert '-' not in uniprot_id
                gene_symbol = self.query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id)
                if gene_symbol is not None:
                    gene_symbol = ';'.join(list(gene_symbol))
                else:
                    gene_symbol = ''
                target_node = self.add_node_smart('protein', uniprot_id, desc=gene_symbol)
                if target_node is not None:
                    self.orangeboard.add_rel('physically_interacts_with', 'Pharos', node, target_node, extended_reltype="targets")

        res_dict = DrugMapper.map_drug_to_ontology(node.name)
        res_indications_set = res_dict['indications']
        res_contraindications_set = res_dict['contraindications']

        for ont_term in res_indications_set:
            if ont_term.startswith('DOID:') or ont_term.startswith('OMIM:'):
                ont_name = QueryBioLink.get_label_for_disease(ont_term)
                ont_node = self.add_node_smart('disease', ont_term, desc=ont_name)
                self.orangeboard.add_rel('indicated_for', 'MyChem.info', node, ont_node, extended_reltype='indicated_for')
            elif ont_term.startswith('HP:'):
                ont_name = QueryBioLink.get_label_for_phenotype(ont_term)
                ont_node = self.add_node_smart('phenotypic_feature', ont_term, desc=ont_name)
                self.orangeboard.add_rel('indicated_for', 'MyChem.info', node, ont_node, extended_reltype='indicated_for')

        for ont_term in res_contraindications_set:
            if ont_term.startswith('DOID:') or ont_term.startswith('OMIM:'):
                ont_name = QueryBioLink.get_label_for_disease(ont_term)
                ont_node = self.add_node_smart('disease', ont_term, desc=ont_name)
                self.orangeboard.add_rel('contraindicated_for', 'MyChem.info', node, ont_node, extended_reltype='contraindicated_for')
            elif ont_term.startswith('HP:'):
                ont_name = QueryBioLink.get_label_for_phenotype(ont_term)
                ont_node = self.add_node_smart('phenotypic_feature', ont_term, desc=ont_name)
                self.orangeboard.add_rel('contraindicated_for', 'MyChem.info', node, ont_node, extended_reltype='contraindicated_for')

        res_hp_set = DrugMapper.map_drug_to_hp_with_side_effects(node.name)

        for hp_term in res_hp_set:
            if hp_term.startswith('HP:'):
                hp_name = QueryBioLink.get_label_for_phenotype(hp_term)
                hp_node = self.add_node_smart('phenotypic_feature', hp_term, desc=hp_name)
                self.orangeboard.add_rel('causes_or_contributes_to', 'SIDER', node, hp_node, extended_reltype="causes_or_contributes_to")


    def expand_microRNA(self, node):
        assert node.nodetype == "microRNA"
        ncbi_gene_id = node.name
        assert 'NCBIGene:' in ncbi_gene_id

        entrez_gene_id = int(ncbi_gene_id.replace("NCBIGene:", ""))
        # microRNA-to-GO (biological process):
        go_bp_dict = self.query_mygene_obj.get_gene_ontology_ids_bp_for_entrez_gene_id(entrez_gene_id)
        for go_id, go_term in go_bp_dict.items():
            gene_ontology_category_and_term_dict = QuerySciGraph.query_get_ontology_node_category_and_term(go_id)
            if len(gene_ontology_category_and_term_dict) > 0:
                ontology_name_str = gene_ontology_category_and_term_dict["category"].replace(" ", "_")
                node2 = self.add_node_smart(ontology_name_str, go_id, desc=go_term)
                if node2 is not None:
                    predicate = self.GO_ONTOLOGY_TO_PREDICATE[ontology_name_str]
                    self.orangeboard.add_rel(predicate,
                                             'gene_ontology', node, node2, extended_reltype=predicate)

        anatomy_dict = QueryBioLink.get_anatomies_for_gene(ncbi_gene_id)
        for anatomy_id, anatomy_desc in anatomy_dict.items():
            anatomy_node = self.add_node_smart("anatomical_entity", anatomy_id, desc=anatomy_desc)
            if anatomy_node is not None:
                self.orangeboard.add_rel('expressed_in', 'BioLink', node, anatomy_node, extended_reltype="expressed_in")

        disease_ids_dict = QueryBioLink.get_diseases_for_gene_desc(ncbi_gene_id)
        for disease_id in disease_ids_dict.keys():
            if 'OMIM:' in disease_id:
                disease_node = self.add_node_smart('disease', disease_id, desc=disease_ids_dict[disease_id])
                if disease_node is not None:
                    self.orangeboard.add_rel('gene_associated_with_condition', 'BioLink', node, disease_node, extended_reltype="associated_with_disease")
            elif 'DOID:' in disease_id:
                disease_node = self.add_node_smart('disease', disease_id,
                                                   desc=disease_ids_dict[disease_id])
                if disease_node is not None:
                    self.orangeboard.add_rel('gene_associated_with_condition', 'BioLink', node, disease_node, extended_reltype="associated_with_disease")
            else:
                print('Warning: unexpected disease ID: ' + disease_id)

        phenotype_ids_dict = QueryBioLink.get_phenotypes_for_gene_desc(ncbi_gene_id)
        for phenotype_id in phenotype_ids_dict.keys():
            phenotype_node = self.add_node_smart("phenotypic_feature", phenotype_id, desc=phenotype_ids_dict[phenotype_id])
            if phenotype_node is not None:
                self.orangeboard.add_rel('has_phenotype', 'BioLink', node, phenotype_node, extended_reltype="has_phenotype")

        mirbase_ids = self.query_mygene_obj.convert_entrez_gene_ID_to_mirbase_ID(
            int(ncbi_gene_id.replace('NCBIGene:', '')))
        for mirbase_id in mirbase_ids:
            mature_mir_ids = QueryMiRBase.convert_mirbase_id_to_mature_mir_ids(mirbase_id)
            for mature_mir_id in mature_mir_ids:
                target_gene_symbols = QueryMiRGate.get_gene_symbols_regulated_by_microrna(mature_mir_id)
                for target_gene_symbol in target_gene_symbols:
                    uniprot_ids = self.query_mygene_obj.convert_gene_symbol_to_uniprot_id(target_gene_symbol)
                    for uniprot_id in uniprot_ids:
                        assert '-' not in uniprot_id
                        target_prot_node = self.add_node_smart('protein', uniprot_id, desc=target_gene_symbol)
                        if target_prot_node is not None:
                            self.orangeboard.add_rel('regulates', 'miRGate', node, target_prot_node, extended_reltype="regulates_expression_of")
                    if len(uniprot_ids) == 0:
                        if BioNetExpander.is_mir(target_gene_symbol):
                            target_ncbi_entrez_ids = self.query_mygene_obj.convert_gene_symbol_to_entrez_gene_ID(
                                target_gene_symbol)
                            for target_ncbi_entrez_id in target_ncbi_entrez_ids:
                                target_mir_node = self.add_node_smart('microRNA',
                                                                      'NCBIGene:' + str(target_ncbi_entrez_id),
                                                                      desc=target_gene_symbol)
                                if target_mir_node is not None and target_mir_node != node:
                                    self.orangeboard.add_rel('regulates', 'miRGate', node, target_mir_node, extended_reltype="regulates_expression_of")

    def expand_pathway(self, node):
        assert node.nodetype == "pathway"
        reactome_id_str = node.name
        uniprot_ids_from_reactome_dict = QueryReactome.query_reactome_pathway_id_to_uniprot_ids_desc(reactome_id_str)
        rel_sourcedb_dict = dict.fromkeys(uniprot_ids_from_reactome_dict.keys(), 'reactome')
        source_node = node
        for uniprot_id in uniprot_ids_from_reactome_dict.keys():
            assert '-' not in uniprot_id
            target_node = self.add_node_smart('protein', uniprot_id, desc=uniprot_ids_from_reactome_dict[uniprot_id])
            if target_node is not None:
                self.orangeboard.add_rel('participates_in', rel_sourcedb_dict[uniprot_id], target_node, source_node, extended_reltype="participates_in")

    def expand_anatomical_entity(self, node):
        assert node.nodetype == "anatomical_entity"
        anatomy_curie_id_str = node.name
        if not anatomy_curie_id_str.startswith("UBERON:"):
            print("Anatomy node does not start with UBERON: " + anatomy_curie_id_str, file=sys.stderr)
#        assert anatomy_curie_id_str.startswith("UBERON:")
        gene_ontology_dict = QuerySciGraph.get_gene_ontology_curie_ids_for_uberon_curie_id(anatomy_curie_id_str)
        for gene_ontology_curie_id_str, gene_ontology_term_dict in gene_ontology_dict.items():
            gene_ontology_type_str = gene_ontology_term_dict["ontology"].replace(" ", "_")
            target_node = self.add_node_smart(gene_ontology_type_str, gene_ontology_curie_id_str,
                                              desc=gene_ontology_term_dict["name"])
            if target_node is not None:
                predicate_str = gene_ontology_term_dict["predicate"].replace(" ", "_")
                if gene_ontology_type_str == "cellular_component":
                    minimal_predicate_str = "has_part"
                else:
                    minimal_predicate_str = "capable_of"
                self.orangeboard.add_rel(minimal_predicate_str, "Monarch_SciGraph", node, target_node, extended_reltype=predicate_str)

    def expand_protein(self, node):
        assert node.nodetype == "protein"
        uniprot_id_str = node.name

        # # SAR:  I suspect these pathways are too high-level and not useful:
        # pathways_set_from_pc2 = QueryPC2.uniprot_id_to_reactome_pathways(uniprot_id_str)
        # doesn't provide pathway descriptions; see if we can get away with not using it?
        # pathways_set_from_uniprot = QueryUniprot.uniprot_id_to_reactome_pathways(uniprot_id_str)

        # protein-pathway membership:
        pathways_dict_from_reactome = QueryReactome.query_uniprot_id_to_reactome_pathway_ids_desc(uniprot_id_str)
        pathways_dict_sourcedb = dict.fromkeys(pathways_dict_from_reactome.keys(), 'reactome')
        node1 = node
        for pathway_id in pathways_dict_from_reactome.keys():
            target_node = self.add_node_smart('pathway',
                                              "REACT:" + pathway_id,
                                              desc=pathways_dict_from_reactome[pathway_id])
            if target_node is not None:
                self.orangeboard.add_rel('participates_in', pathways_dict_sourcedb[pathway_id], node1, target_node, extended_reltype="participates_in")
        gene_symbols_set = self.query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id_str)
        for gene_symbol in gene_symbols_set:
            # protein-DNA (i.e., gene regulatory) interactions:
            regulator_gene_symbols_set = QueryGeneProf.gene_symbol_to_transcription_factor_gene_symbols(gene_symbol)
            for reg_gene_symbol in regulator_gene_symbols_set:
                reg_uniprot_ids_set = self.query_mygene_obj.convert_gene_symbol_to_uniprot_id(reg_gene_symbol)
                for reg_uniprot_id in reg_uniprot_ids_set:
                    assert '-' not in reg_uniprot_id
                    node2 = self.add_node_smart('protein', reg_uniprot_id, desc=reg_gene_symbol)
                    if node2 is not None and node2.uuid != node1.uuid:
                        self.orangeboard.add_rel('regulates', 'GeneProf', node2, node1, extended_reltype="regulates_expression_of")

            # microrna-gene interactions:
            microrna_regulators = QueryMiRGate.get_microrna_ids_that_regulate_gene_symbol(gene_symbol)
            for microrna_id in microrna_regulators:
                mir_gene_symbol = QueryMiRBase.convert_mirbase_id_to_mir_gene_symbol(microrna_id)
                if mir_gene_symbol is not None:
                    mir_entrez_gene_ids = self.query_mygene_obj.convert_gene_symbol_to_entrez_gene_ID(mir_gene_symbol)
                    if len(mir_entrez_gene_ids) > 0:
                        for mir_entrez_gene_id in mir_entrez_gene_ids:
                            mir_node = self.add_node_smart('microRNA',
                                                           'NCBIGene:' + str(mir_entrez_gene_id),
                                                           desc=mir_gene_symbol)
                            if mir_node is not None:
                                self.orangeboard.add_rel('regulates', 'miRGate', mir_node, node, extended_reltype="regulates_expression_of")

        entrez_gene_id = self.query_mygene_obj.convert_uniprot_id_to_entrez_gene_ID(uniprot_id_str)
        if len(entrez_gene_id) > 0:
            entrez_gene_id_str = 'NCBIGene:' + str(next(iter(entrez_gene_id)))

            # protein-to-anatomy associations:
            anatomy_dict = QueryBioLink.get_anatomies_for_gene(entrez_gene_id_str)
            for anatomy_id, anatomy_desc in anatomy_dict.items():
                anatomy_node = self.add_node_smart("anatomical_entity", anatomy_id, desc=anatomy_desc)
                if anatomy_node is not None:
                    self.orangeboard.add_rel('expressed_in', 'BioLink', node, anatomy_node, extended_reltype="expressed_in")

            # protein-disease associations:
            disont_id_dict = QueryBioLink.get_diseases_for_gene_desc(entrez_gene_id_str)
            for disont_id in disont_id_dict.keys():
                if 'DOID:' in disont_id:
                    node2 = self.add_node_smart('disease', disont_id, desc=disont_id_dict[disont_id])
                    if node2 is not None:
                        self.orangeboard.add_rel('gene_associated_with_condition', 'BioLink', node1, node2, extended_reltype="associated_with_disease")
                else:
                    if 'OMIM:' in disont_id:
                        node2 = self.add_node_smart('disease', disont_id, desc=disont_id_dict[disont_id])
                        if node2 is not None:
                            self.orangeboard.add_rel('gene_associated_with_condition', 'BioLink', node1, node2, extended_reltype="associated_with_disease")

            # protein-phenotype associations:
            phenotype_id_dict = QueryBioLink.get_phenotypes_for_gene_desc(entrez_gene_id_str)
            for phenotype_id_str in phenotype_id_dict.keys():
                node2 = self.add_node_smart("phenotypic_feature", phenotype_id_str,
                                            desc=phenotype_id_dict[phenotype_id_str])
                if node2 is not None:
                    self.orangeboard.add_rel('has_phenotype', 'BioLink', node1, node2, extended_reltype="has_phenotype")

        # protein-protein interactions:
        int_dict = QueryReactome.query_uniprot_id_to_interacting_uniprot_ids_desc(uniprot_id_str)
        for int_uniprot_id in int_dict.keys():
            if self.query_mygene_obj.uniprot_id_is_human(int_uniprot_id):
                int_alias = int_dict[int_uniprot_id]
                if 'BINDSGENE:' not in int_alias:
                    node2 = self.add_node_smart('protein', int_uniprot_id, desc=int_alias)
                    if node2 is not None and node2.uuid != node1.uuid:
                        self.orangeboard.add_rel('physically_interacts_with', 'reactome', node1, node2, extended_reltype="physically_interacts_with")
                else:
                    target_gene_symbol = int_alias.split(':')[1]
                    target_uniprot_ids_set = self.query_mygene_obj.convert_gene_symbol_to_uniprot_id(target_gene_symbol)
                    for target_uniprot_id in target_uniprot_ids_set:
                        assert '-' not in target_uniprot_id
                        node2 = self.add_node_smart('protein', target_uniprot_id, desc=target_gene_symbol)
                        if node2 is not None and node2 != node1:
                            self.orangeboard.add_rel('regulates', 'Reactome', node1, node2, extended_reltype="regulates_expression_of")

        # protein-to-GO (biological process):
        go_dict = self.query_mygene_obj.get_gene_ontology_ids_for_uniprot_id(uniprot_id_str)
        for go_id, go_term_dict in go_dict.items():
            go_term = go_term_dict.get('term', None)
            ontology_name_str = go_term_dict.get('ont', None)
            if go_term is not None and ontology_name_str is not None:
                node2 = self.add_node_smart(ontology_name_str, go_id, desc=go_term)
                if node2 is not None:
                    predicate = self.GO_ONTOLOGY_TO_PREDICATE[ontology_name_str]
                    self.orangeboard.add_rel(predicate,
                                             'gene_ontology', node1, node2, extended_reltype=predicate)

    def expand_gene_ontology(self, node, gene_ontology_type_str):
        node_go_id = node.name
        child_go_ids_dict = QuerySciGraph.query_sub_ontology_terms_for_ontology_term(node_go_id)
        if child_go_ids_dict is not None:
            for child_go_id, child_go_term in child_go_ids_dict.items():
                child_node = self.add_node_smart(gene_ontology_type_str, child_go_id, desc=child_go_term)
                if child_node is not None and child_node != node:
                    self.orangeboard.add_rel("subclass_of", 'gene_ontology', child_node, node, extended_reltype="subclass_of")

    def expand_molecular_function(self, node):
        assert node.nodetype == "molecular_function"
        self.expand_gene_ontology(node, "molecular_function")

    def expand_cellular_component(self, node):
        assert node.nodetype == "cellular_component"
        self.expand_gene_ontology(node, "cellular_component")

    def expand_biological_process(self, node):
        assert node.nodetype == "biological_process"
        self.expand_gene_ontology(node, "biological_process")

    def expand_phenotypic_feature(self, node):
        assert node.nodetype == "phenotypic_feature"
        # expand phenotype=>anatomy
        phenotype_id = node.name
        anatomy_dict = QueryBioLink.get_anatomies_for_phenotype(phenotype_id)
        for anatomy_id, anatomy_desc in anatomy_dict.items():
            anatomy_node = self.add_node_smart("anatomical_entity", anatomy_id, desc=anatomy_desc)
            if anatomy_node is not None:
                self.orangeboard.add_rel("affects", 'BioLink', node, anatomy_node, extended_reltype="affects")

        sub_phe_dict = QuerySciGraph.query_sub_ontology_terms_for_ontology_term(phenotype_id)
        for sub_phe_id, sub_phe_desc in sub_phe_dict.items():
            sub_phe_node = self.add_node_smart("phenotypic_feature", sub_phe_id, desc=sub_phe_desc)
            if sub_phe_node is not None:
                self.orangeboard.add_rel("subclass_of", 'Monarch_SciGraph', sub_phe_node, node, extended_reltype="subclass_of")

    def expand_genetic_condition(self, node):
        assert node.name.startswith("OMIM:")
        res_dict = self.query_omim_obj.disease_mim_to_gene_symbols_and_uniprot_ids(node.name)
        uniprot_ids = res_dict['uniprot_ids']
        gene_symbols = res_dict['gene_symbols']
        if len(uniprot_ids) == 0 and len(gene_symbols) == 0:
            return  # nothing else to do, for this MIM number
        uniprot_ids_to_gene_symbols_dict = dict()
        for gene_symbol in gene_symbols:
            uniprot_ids = self.query_mygene_obj.convert_gene_symbol_to_uniprot_id(gene_symbol)
            if len(uniprot_ids) == 0:
                # this might be a microRNA
                if BioNetExpander.is_mir(gene_symbol):
                    entrez_gene_ids = self.query_mygene_obj.convert_gene_symbol_to_entrez_gene_ID(gene_symbol)
                    if len(entrez_gene_ids) > 0:
                        for entrez_gene_id in entrez_gene_ids:
                            curie_entrez_gene_id = 'NCBIGene:' + str(entrez_gene_id)
                            node2 = self.add_node_smart('microRNA',
                                                        curie_entrez_gene_id,
                                                        desc=gene_symbol)
                            if node2 is not None:
                                self.orangeboard.add_rel("gene_mutations_contribute_to",
                                                         "OMIM", node2, node,
                                                         extended_reltype="gene_mutations_contribute_to")
            for uniprot_id in uniprot_ids:
                uniprot_ids_to_gene_symbols_dict[uniprot_id] = gene_symbol
        for uniprot_id in uniprot_ids:
            gene_symbol = self.query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id)
            if gene_symbol is not None:
                gene_symbol_str = ';'.join(gene_symbol)
                uniprot_ids_to_gene_symbols_dict[uniprot_id] = gene_symbol_str
        source_node = node
        for uniprot_id in uniprot_ids_to_gene_symbols_dict.keys():
            assert '-' not in uniprot_id
            target_node = self.add_node_smart('protein', uniprot_id,
                                              desc=uniprot_ids_to_gene_symbols_dict[uniprot_id])
            if target_node is not None:
                self.orangeboard.add_rel("gene_mutations_contribute_to",
                                         "OMIM", target_node, source_node,
                                         extended_reltype="gene_mutations_contribute_to")

        # query for phenotypes associated with this disease
        phenotype_id_dict = QueryBioLink.get_phenotypes_for_disease_desc(node.name)
        for phenotype_id_str in phenotype_id_dict.keys():
            phenotype_node = self.add_node_smart("phenotypic_feature", phenotype_id_str, desc=phenotype_id_dict[phenotype_id_str])
            if phenotype_node is not None:
                self.orangeboard.add_rel("has_phenotype", 'BioLink', node, phenotype_node, extended_reltype="has_phenotype")

    def expand_mondo_disease(self, node):
        genes_list = QueryBioLink.get_genes_for_disease_desc(node.name)
        for hgnc_gene_id in genes_list:
            if hgnc_gene_id.startswith("HGNC:"):
                uniprot_id_set = self.query_mygene_obj.convert_hgnc_gene_id_to_uniprot_id(hgnc_gene_id)
                if len(uniprot_id_set) > 0:
                    uniprot_id = next(iter(uniprot_id_set))
                    gene_symbol_set = self.query_mygene_obj.convert_uniprot_id_to_gene_symbol(uniprot_id)
                    if len(gene_symbol_set) > 0:
                        protein_node = self.add_node_smart('protein', uniprot_id,
                                                           desc=next(iter(gene_symbol_set)))
                        self.orangeboard.add_rel("gene_associated_with_condition",
                                                 "BioLink",
                                                 protein_node, node, extended_reltype="associated_with_disease")

    def expand_disease(self, node):
        assert node.nodetype == "disease"
        disease_name = node.name

        gene_ontology_dict = QuerySciGraph.get_gene_ontology_curie_ids_for_disease_curie_id(disease_name)
        for gene_ontology_curie_id_str, gene_ontology_term_dict in gene_ontology_dict.items():
            gene_ontology_type_str = gene_ontology_term_dict["ontology"].replace(" ", "_")
            target_node = self.add_node_smart(gene_ontology_type_str, gene_ontology_curie_id_str,
                                              desc=gene_ontology_term_dict["name"])
            if target_node is not None:
                predicate_str = gene_ontology_term_dict["predicate"].replace(" ", "_")
                self.orangeboard.add_rel("affects", "Monarch_SciGraph", node, target_node, extended_reltype=predicate_str)

        if "OMIM:" in disease_name:
            self.expand_genetic_condition(node)
            return

        if "MONDO:" in disease_name:
            self.expand_mondo_disease(node)
            return

        # if we get here, this is a Disease Ontology disease
        disont_id = disease_name

        child_disease_ids_dict = QueryDisont.query_disont_to_child_disonts_desc(disont_id)
        for child_disease_id in child_disease_ids_dict.keys():
            target_node = self.add_node_smart('disease', child_disease_id,
                                              desc=child_disease_ids_dict[child_disease_id])
            if target_node is not None:
                self.orangeboard.add_rel('subclass_of', 'DiseaseOntology',
                                         target_node, node, extended_reltype="subclass_of")

        mesh_ids_set = QueryDisont.query_disont_to_mesh_id(disont_id)
        for mesh_id in mesh_ids_set:
            uniprot_ids_dict = QueryDisGeNet.query_mesh_id_to_uniprot_ids_desc(mesh_id)
            for uniprot_id in uniprot_ids_dict.keys():
                assert '-' not in uniprot_id
                source_node = self.add_node_smart('protein', uniprot_id,
                                                  desc=uniprot_ids_dict[uniprot_id])
                if source_node is not None:
                    self.orangeboard.add_rel("gene_associated_with_condition", "DisGeNet", source_node,
                                             node, extended_reltype="gene_associated_with_condition")

        # query for phenotypes associated with this disease
        phenotype_id_dict = QueryBioLink.get_phenotypes_for_disease_desc(disont_id)
        for phenotype_id_str in phenotype_id_dict.keys():
            phenotype_node = self.add_node_smart("phenotypic_feature", phenotype_id_str,
                                                 desc=phenotype_id_dict[phenotype_id_str])
            if phenotype_node is not None:
                self.orangeboard.add_rel("has_phenotype", 'BioLink', node, phenotype_node, extended_reltype="has_phenotype")

    def expand_node(self, node):
        node_type = node.nodetype

        method_name = 'expand_' + node_type
        # Find the corresponding method and feed a keyword argument `node`
        expand_method = methodcaller(method_name, node=node)
        # Call this method on the orangeboard instance
        # Identical to `self.expand_xxx(node=node)` given `nodetype = "xxx"`
        expand_method(self)

        node.expanded = True

    def expand_all_nodes(self):
        nodes = self.orangeboard.get_all_nodes_for_current_seed_node()
        num_nodes_to_expand = sum([not mynode.expanded for mynode in nodes])
        print('----------------------------------------------------')
        print('Number of nodes to expand: ' + str(num_nodes_to_expand))
        print('----------------------------------------------------')
        for node in nodes:
            if not node.expanded:
                self.expand_node(node)
                num_nodes_to_expand -= 1
                if (num_nodes_to_expand % 100 == 0):
                    print('Number of nodes left to expand in this iteration: ' + str(num_nodes_to_expand))

    def test_go_bp_protein():
        ob = Orangeboard(debug=False)
        ob.set_dict_reltype_dirs({'targets': True})
        bne = BioNetExpander(ob)
        protein_node = bne.add_node_smart('protein', 'Q75MH2', seed_node_bool=True, desc='IL6')
        bne.expand_protein(protein_node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_go_bp_microrna():
        ob = Orangeboard(debug=False)
        ob.set_dict_reltype_dirs({'targets': True})
        bne = BioNetExpander(ob)
        microrna_node = bne.add_node_smart('microRNA', 'NCBIGene:406991', seed_node_bool=True, desc='test microrna')
        bne.expand_microrna(microrna_node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_go_term():
        ob = Orangeboard(debug=False)
        ob.set_dict_reltype_dirs({'targets': True})
        bne = BioNetExpander(ob)
        go_node = bne.add_node_smart('biological_process', 'GO:1904685', seed_node_bool=True, desc='test biological process')
        bne.expand_biological_process(go_node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_disease_to_go():
        ob = Orangeboard(debug=False)
        ob.set_dict_reltype_dirs({'affects': True})
        bne = BioNetExpander(ob)
        node = bne.add_node_smart('disease', 'DOID:906', seed_node_bool=True, desc='peroxisomal disease')
        bne.expand_disease(node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_anatomy_to_go():
        ob = Orangeboard(debug=False)
        ob.set_dict_reltype_dirs({'capable_of': True})
        bne = BioNetExpander(ob)
        node = bne.add_node_smart('anatomical_entity', 'UBERON:0000171', seed_node_bool=True, desc='respiration organ')
        bne.expand_disease(node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_metabolite_to_protein():
        ob = Orangeboard(debug=False)
        ob.set_dict_reltype_dirs({'physically_interacts_with': True})
        bne = BioNetExpander(ob)
        node = bne.add_node_smart('metabolite', 'KEGG:C00190', seed_node_bool=True, desc='UDP-D-xylose')
        bne.expand_metabolite(node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_mondo_liver():
        ob = Orangeboard(debug=False)
        ob.set_dict_reltype_dirs({'gene_associated_with_condition': True,
                                  'has_phenotype': True})
        bne = BioNetExpander(ob)
        node = bne.add_node_smart('disease', 'MONDO:0005359', seed_node_bool=True, desc='drug-induced liver injury')
        bne.expand_disease(node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_double_proteins():
        ob = Orangeboard(debug=False)
        bne = BioNetExpander(ob)
        bne.add_node_smart('protein', 'Q59F02', seed_node_bool=True, desc='PMM2')
        bne.add_node_smart('protein', 'H3BV55', seed_node_bool=True, desc='PMM2')
        bne.add_node_smart('protein', 'A0A0S2Z4J6', seed_node_bool=True, desc='PMM2')
        bne.add_node_smart('protein', 'H3BV34', seed_node_bool=True, desc='PMM2')
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_issue_228():
        ob = Orangeboard(debug=False)
        bne = BioNetExpander(ob)
        bne.add_node_smart('disease', 'MONDO:0005359', seed_node_bool=True, desc='drug-induced liver injury')
        bne.add_node_smart('protein', 'Q59F02', seed_node_bool=True, desc='PMM2')
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_issue_237():
        ob = Orangeboard(debug=False)
        bne = BioNetExpander(ob)
        chem_node = bne.add_node_smart('chemical_substance',
                                       'KWHRDNMACVLHCE-UHFFFAOYSA-N', seed_node_bool=True,
                                       desc='ciprofloxacin')
        bne.expand_chemical_substance(chem_node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

    def test_issue_235():
        ob = Orangeboard(debug=False)
        bne = BioNetExpander(ob)
        omim_node = bne.add_node_smart('disease',
                                       'OMIM:105150', seed_node_bool=True,
                                       desc='CEREBRAL AMYLOID ANGIOPATHY, CST3-RELATED')
        bne.expand_genetic_condition(omim_node)
        ob.neo4j_set_url()
        ob.neo4j_set_auth()
        ob.neo4j_push()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Builds the master knowledge graph')
    parser.add_argument('--runfunc', dest='runfunc')
    args = parser.parse_args()
    args_dict = vars(args)
    if args_dict.get('runfunc', None) is not None:
        run_function_name = args_dict['runfunc']
    else:
        sys.exit("must specify --runfunc")
    run_method = getattr(BioNetExpander, run_function_name, None)
    if run_method is None:
        sys.exit("function not found: " + run_function_name)

    # print(QueryEBIOLSExtended.get_disease_description('DOID:0060185'))
    running_time = timeit.timeit(lambda: run_method(), number=1)
    print('running time for function: ' + str(running_time))

