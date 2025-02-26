#!/bin/env python3
"""
Usage:  python biolink_helper.py [biolink version number, e.g. 3.0.3]
"""

import argparse
import datetime
import json
import os
import sys
import pathlib
import pickle
from collections import defaultdict
from typing import Optional, List, Set, Dict, Union, Tuple

import networkx as nx
import requests
import yaml

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

class BiolinkHelper:

    def __init__(self, biolink_version: Optional[str] = None, is_test: bool = False):
        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: DEBUG: In BiolinkHelper init")

        self.biolink_version = biolink_version if biolink_version else self.get_current_arax_biolink_version()
        if self.biolink_version == "4.2.0":
            eprint(f"{timestamp}: DEBUG: Overriding Biolink version from 4.2.0 to 4.2.1 due to issues with "
                   f"treats predicates in 4.2.0")
            self.biolink_version = "4.2.1"
        self.root_category = "biolink:NamedThing"
        self.root_predicate = "biolink:related_to"
        biolink_helper_dir = os.path.dirname(os.path.abspath(__file__))
        self.biolink_lookup_map_path = f"{biolink_helper_dir}/biolink_lookup_map_{self.biolink_version}_v5.pickle"

        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: DEBUG: Loading BL lookup map...")
        self.biolink_lookup_map = self._load_biolink_lookup_map(is_test=is_test)
        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: DEBUG: Done loading BL lookup map")

        protein_like_categories = {"biolink:Protein", "biolink:Gene"}
        disease_like_categories = {"biolink:Disease", "biolink:PhenotypicFeature", "biolink:DiseaseOrPhenotypicFeature"}
        self.arax_conflations = {
            "biolink:Protein": protein_like_categories,
            "biolink:Gene": protein_like_categories,
            "biolink:Disease": disease_like_categories,
            "biolink:PhenotypicFeature": disease_like_categories,
            "biolink:DiseaseOrPhenotypicFeature": disease_like_categories
        }

    def get_ancestors(self, biolink_items: Union[str, List[str]], include_mixins: bool = True, include_conflations: bool = True) -> List[str]:
        """
        Returns the ancestors of Biolink categories, predicates, category mixins, or predicate mixins. Input
        categories/predicates/mixins are themselves included in the returned ancestor list. For proper
        categories/predicates, inclusion of mixin ancestors can be turned on or off via the include_mixins flag.
        Note that currently the 'include_mixins' flag is only relevant when inputting *proper* predicates/categories;
        if only predicate/category *mixins* are input, then the 'include_mixins' flag does nothing (mixins will always
        be included in that case). Inclusion of ARAX-defined conflations (e.g., gene == protein) can be controlled via
        the include_conflations parameter.
        """
        input_item_set = self._convert_to_set(biolink_items)
        categories = input_item_set.intersection(set(self.biolink_lookup_map["categories"]))
        predicates = input_item_set.intersection(set(self.biolink_lookup_map["predicates"]))
        aspects = input_item_set.intersection(set(self.biolink_lookup_map["aspects"]))
        directions = input_item_set.intersection(set(self.biolink_lookup_map["directions"]))
        ancestors = input_item_set.copy()
        if include_conflations:
            categories = set(self.add_conflations(categories))
        for category in categories:
            ancestor_property = "ancestors" if not include_mixins and "ancestors" in self.biolink_lookup_map["categories"][category] else "ancestors_with_mixins"
            ancestors.update(self.biolink_lookup_map["categories"][category][ancestor_property])
        for predicate in predicates:
            ancestor_property = "ancestors" if not include_mixins and "ancestors" in self.biolink_lookup_map["predicates"][predicate] else "ancestors_with_mixins"
            ancestors.update(self.biolink_lookup_map["predicates"][predicate][ancestor_property])
        for aspect in aspects:
            ancestors.update(self.biolink_lookup_map["aspects"][aspect]["ancestors"])
        for direction in directions:
            ancestors.update(self.biolink_lookup_map["directions"][direction]["ancestors"])
        return list(ancestors)

    def get_descendants(self, biolink_items: Union[str, List[str], Set[str]], include_mixins: bool = True, include_conflations: bool = True) -> List[str]:
        """
        Returns the descendants of Biolink categories, predicates, category mixins, or predicate mixins. Input
        categories/predicates/mixins are themselves included in the returned descendant list. For proper
        categories/predicates, inclusion of mixin descendants can be turned on or off via the include_mixins flag.
        Note that currently the 'include_mixins' flag is only relevant when inputting *proper* predicates/categories;
        if only predicate/category mixins are input, then the 'include_mixins' flag does nothing (mixins will always
        be included in that case). Inclusion of ARAX-defined conflations (e.g., gene == protein) can be controlled
        via the include_conflations parameter.
        """
        input_item_set = self._convert_to_set(biolink_items)
        categories = input_item_set.intersection(set(self.biolink_lookup_map["categories"]))
        predicates = input_item_set.intersection(set(self.biolink_lookup_map["predicates"]))
        aspects = input_item_set.intersection(set(self.biolink_lookup_map["aspects"]))
        directions = input_item_set.intersection(set(self.biolink_lookup_map["directions"]))
        descendants = input_item_set.copy()
        if include_conflations:
            categories = set(self.add_conflations(categories))
        for category in categories:
            descendant_property = "descendants" if not include_mixins and "descendants" in self.biolink_lookup_map["categories"][category] else "descendants_with_mixins"
            descendants.update(self.biolink_lookup_map["categories"][category][descendant_property])
        for predicate in predicates:
            descendant_property = "descendants" if not include_mixins and "descendants" in self.biolink_lookup_map["predicates"][predicate] else "descendants_with_mixins"
            descendants.update(self.biolink_lookup_map["predicates"][predicate][descendant_property])
        for aspect in aspects:
            descendants.update(self.biolink_lookup_map["aspects"][aspect]["descendants"])
        for direction in directions:
            descendants.update(self.biolink_lookup_map["directions"][direction]["descendants"])
        return list(descendants)

    def get_canonical_predicates(self, predicates: Union[str, List[str], Set[str]], print_warnings: bool = True) -> List[str]:
        """
        Returns the canonical version of the input predicate(s). Accepts a single predicate or multiple predicates as
        input and always returns the canonical predicate(s) in a list. Works with both proper and mixin predicates.
        """
        input_predicate_set = self._convert_to_set(predicates)
        valid_predicates = input_predicate_set.intersection(self.biolink_lookup_map["predicates"])
        invalid_predicates = input_predicate_set.difference(valid_predicates)
        if invalid_predicates and print_warnings:
            eprint(f"WARNING: Provided predicate(s) {invalid_predicates} do not exist in Biolink {self.biolink_version}")
        canonical_predicates = {self.biolink_lookup_map["predicates"][predicate]["canonical_predicate"]
                                for predicate in valid_predicates}
        canonical_predicates.update(invalid_predicates)  # Go ahead and include those we don't have canonical info for
        return list(canonical_predicates)
    
    def get_predicate_depth_map(self)->Dict[str,int]:
        response = self._download_biolink_model()
        if response.status_code == 200:
            biolink_model = yaml.safe_load(response.text)
            predicate_dag = self._build_predicate_dag(biolink_model)
            
        else:
            raise RuntimeError(f"ERROR: Request to get Biolink {self.biolink_version} YAML file returned "
                               f"{response.status_code} response. Cannot load BiolinkHelper.")
        return self._get_depths_from_root(predicate_dag)
    
    def is_symmetric(self, predicate: str) -> Optional[bool]:
        if predicate in self.biolink_lookup_map["predicates"]:
            return self.biolink_lookup_map["predicates"][predicate]["is_symmetric"]
        else:
            return True  # Consider unrecognized predicates symmetric (rather than throw error)

    def replace_mixins_with_direct_mappings(self, biolink_items: Union[str, List[str], Set[str]]) -> List[str]:
        # TODO: After Plover is revised to not use this method, delete it.. (nothing else uses it)
        input_item_set = self._convert_to_set(biolink_items)
        return list(input_item_set)

    def filter_out_mixins(self, biolink_items: Union[List[str], Set[str]]) -> List[str]:
        """
        Removes any predicate or category mixins in the input list.
        """
        input_item_set = self._convert_to_set(biolink_items)
        non_mixin_items = set(item for item in biolink_items if not (self.biolink_lookup_map["predicates"].get(item, dict()).get("is_mixin") or
                                                                     self.biolink_lookup_map["categories"].get(item, dict()).get("is_mixin")))
        return list(non_mixin_items)

    def add_conflations(self, categories: Union[str, List[str], Set[str]]) -> List[str]:
        """
        Adds any "equivalent" categories (according to ARAX) to the input categories.
        """
        category_set = self._convert_to_set(categories)
        return list({conflated_category for category in category_set
                     for conflated_category in self.arax_conflations.get(category, {category})})

    def get_root_category(self) -> str:
        return self.root_category

    def get_root_predicate(self) -> str:
        return self.root_predicate

    @staticmethod
    def get_current_arax_biolink_version() -> str:
        """
        Returns the current Biolink version that the ARAX system is using, according to the OpenAPI YAML file.
        """
        code_dir = f"{os.path.dirname(os.path.abspath(__file__))}/../.."
        openapi_yaml_path = f"{code_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml"
        openapi_json_path = f"{code_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.json"

        # Read the cached JSON openAPI file if it's already been created by RTXConfiguration (faster than YAML)
        openapi_json_file = pathlib.Path(openapi_json_path)
        if openapi_json_file.exists():
            with open(openapi_json_file) as json_file:
                opanapi_data = json.load(json_file)
        else:
            with open(openapi_yaml_path) as api_file:
                opanapi_data = yaml.safe_load(api_file)
        return opanapi_data["info"]["x-translator"]["biolink-version"]

    # ------------------------------------- Internal methods -------------------------------------------------- #

    def _load_biolink_lookup_map(self, is_test: bool = False):
        lookup_map_file = pathlib.Path(self.biolink_lookup_map_path)
        timestamp = str(datetime.datetime.now().isoformat())

        if is_test or not lookup_map_file.exists():
            if is_test:
                eprint(f"{timestamp}: DEBUG: in test mode")
            else:
                eprint(f"{timestamp}: DEBUG: lookup map not here! {lookup_map_file}")
            # Parse the relevant Biolink yaml file and create/save local indexes
            return self._create_biolink_lookup_map()
        else:
            # A local file already exists for this Biolink version, so just load it
            eprint(f"{timestamp}: DEBUG: Loading pickle file: {self.biolink_lookup_map_path}")
            with open(self.biolink_lookup_map_path, "rb") as biolink_map_file:
                biolink_lookup_map = pickle.load(biolink_map_file)
            return biolink_lookup_map
        
    def _download_biolink_model(self):
        response = requests.get(f"https://raw.githubusercontent.com/biolink/biolink-model/{self.biolink_version}/biolink-model.yaml",
                                timeout=10)
        if response.status_code != 200:  # Sometimes Biolink's tags start with 'v', so try that
            response = requests.get(f"https://raw.githubusercontent.com/biolink/biolink-model/v{self.biolink_version}/biolink-model.yaml",
                                    timeout=10)
        return response
    
    def _create_biolink_lookup_map(self) -> Dict[str, Dict[str, Dict[str, Union[str, List[str], bool]]]]:
        timestamp = str(datetime.datetime.now().isoformat())
        eprint(f"{timestamp}: INFO: Building local Biolink {self.biolink_version} ancestor/descendant lookup map "
               f"because one doesn't yet exist")
        biolink_lookup_map = {"predicates": dict(), "categories": dict(),
                              "aspects": dict(), "directions": dict()}
        # Grab the relevant Biolink yaml file
        response = self._download_biolink_model()

        if response.status_code == 200:
            biolink_model = yaml.safe_load(response.text)

            # --------------------------------  PREDICATES --------------------------------- #
            predicate_dag = self._build_predicate_dag(biolink_model)
            # Build our map of predicate ancestors/descendants for easy lookup, first WITH mixins
            for node_id in list(predicate_dag.nodes):
                node_info = predicate_dag.nodes[node_id]
                biolink_lookup_map["predicates"][node_id] = {
                    "ancestors_with_mixins": self._get_ancestors_nx(predicate_dag, node_id),
                    "descendants_with_mixins": self._get_descendants_nx(predicate_dag, node_id),
                    "is_symmetric": node_info.get("is_symmetric", False),
                    "canonical_predicate": node_info.get("canonical_predicate"),
                    "is_mixin": node_info.get("is_mixin", False)
                }
            # Now build our predicate ancestor/descendant lookup maps WITHOUT mixins
            mixin_node_ids = [node_id for node_id, data in predicate_dag.nodes(data=True) if data.get("is_mixin")]
            for mixin_node_id in mixin_node_ids:
                predicate_dag.remove_node(mixin_node_id)
            for node_id in list(predicate_dag.nodes):
                biolink_lookup_map["predicates"][node_id]["ancestors"] = self._get_ancestors_nx(predicate_dag, node_id)
                biolink_lookup_map["predicates"][node_id]["descendants"] = self._get_descendants_nx(predicate_dag, node_id)

            # --------------------------------  CATEGORIES --------------------------------- #
            category_dag = self._build_category_dag(biolink_model)
            # Build our map of category ancestors/descendants for easy lookup, first WITH mixins
            for node_id in list(category_dag.nodes):
                node_info = category_dag.nodes[node_id]
                biolink_lookup_map["categories"][node_id] = {
                    "ancestors_with_mixins": self._get_ancestors_nx(category_dag, node_id),
                    "descendants_with_mixins": self._get_descendants_nx(category_dag, node_id),
                    "is_mixin": node_info.get("is_mixin", False)
                }
            # Now build our category ancestor/descendant lookup maps WITHOUT mixins
            mixin_node_ids = [node_id for node_id, data in category_dag.nodes(data=True) if data.get("is_mixin")]
            for mixin_node_id in mixin_node_ids:
                category_dag.remove_node(mixin_node_id)
            for node_id in list(category_dag.nodes):
                biolink_lookup_map["categories"][node_id]["ancestors"] = self._get_ancestors_nx(category_dag, node_id)
                biolink_lookup_map["categories"][node_id]["descendants"] = self._get_descendants_nx(category_dag, node_id)

            # --------------------------------  ASPECTS --------------------------------- #
            aspect_dag = self._build_aspect_dag(biolink_model)
            for node_id in list(aspect_dag.nodes):
                biolink_lookup_map["aspects"][node_id] = {
                    "ancestors": self._get_ancestors_nx(aspect_dag, node_id),
                    "descendants": self._get_descendants_nx(aspect_dag, node_id)
                }

            # --------------------------------  DIRECTIONS --------------------------------- #
            direction_dag = self._build_direction_dag(biolink_model)
            for node_id in list(direction_dag.nodes):
                biolink_lookup_map["directions"][node_id] = {
                    "ancestors": self._get_ancestors_nx(direction_dag, node_id),
                    "descendants": self._get_descendants_nx(direction_dag, node_id)
                }

            # Cache our Biolink lookup map (never needs to be refreshed for the given Biolink version)
            with open(self.biolink_lookup_map_path, "wb") as output_file:
                pickle.dump(biolink_lookup_map, output_file)  # Use pickle so we can save Sets
            # Also save a JSON version to help with debugging
            json_file_path = self.biolink_lookup_map_path.replace(".pickle", ".json")
            with open(json_file_path, "w+") as output_json_file:
                json.dump(biolink_lookup_map, output_json_file, default=self._serialize_with_sets, indent=4)
        else:
            raise RuntimeError(f"ERROR: Request to get Biolink {self.biolink_version} YAML file returned "
                               f"{response.status_code} response. Cannot load BiolinkHelper.")

        return biolink_lookup_map

    def _build_predicate_dag(self, biolink_model: dict) -> nx.DiGraph:
        predicate_dag = nx.DiGraph()

        # NOTE: 'slots' includes some things that aren't predicates, but we don't care; doesn't hurt to include them
        for slot_name_english, info in biolink_model["slots"].items():
            slot_name = self._convert_to_biolink_snakecase(slot_name_english)
            # Record relationship between this node and its parent, if provided
            parent_name_english = info.get("is_a")
            if parent_name_english:
                parent_name = self._convert_to_biolink_snakecase(parent_name_english)
                predicate_dag.add_edge(parent_name, slot_name)
            # Record relationship between this node and any direct 'mixins', if provided (treat same as is_a)
            direct_mappings_english = info.get("mixins", [])
            direct_mappings = {self._convert_to_biolink_snakecase(mapping_english)
                               for mapping_english in direct_mappings_english}
            for direct_mapping in direct_mappings:
                predicate_dag.add_edge(direct_mapping, slot_name)

            # Record node metadata
            self._add_node_if_doesnt_exist(predicate_dag, slot_name)
            if info.get("mixin"):
                predicate_dag.nodes[slot_name]["is_mixin"] = True
            if info.get("symmetric"):
                predicate_dag.nodes[slot_name]["is_symmetric"] = True
            # Record the canonical form of this predicate
            inverse_predicate_english = info.get("inverse")
            is_canonical_predicate = info.get("annotations", dict()).get("canonical_predicate")
            # A couple 'inverse' pairs of predicates in Biolink 3.0.3 seem to be missing a 'canonical_predicate' label,
            # so we work around that below (see https://github.com/biolink/biolink-model/issues/1112)
            canonical_predicate_english = slot_name_english if is_canonical_predicate or not inverse_predicate_english else inverse_predicate_english
            canonical_predicate = self._convert_to_biolink_snakecase(canonical_predicate_english)
            predicate_dag.nodes[slot_name]["canonical_predicate"] = canonical_predicate

        # Last, filter out things that are not predicates (Biolink 'slots' includes other things too..)
        non_predicate_node_ids = [node_id for node_id, data in predicate_dag.nodes(data=True)
                                  if not (self.root_predicate in self._get_ancestors_nx(predicate_dag, node_id)
                                          or data.get("is_mixin"))]
        for non_predicate_node_id in non_predicate_node_ids:
            predicate_dag.remove_node(non_predicate_node_id)

        return predicate_dag

    def _build_category_dag(self, biolink_model: dict) -> nx.DiGraph:
        category_dag = nx.DiGraph()

        for class_name_english, info in biolink_model["classes"].items():
            class_name = self._convert_to_biolink_camelcase(class_name_english)
            # Record relationship between this node and its parent, if provided
            parent_name_english = info.get("is_a")
            if parent_name_english:
                parent_name = self._convert_to_biolink_camelcase(parent_name_english)
                category_dag.add_edge(parent_name, class_name)
            # Record relationship between this node and any direct 'mixins', if provided (treat same as is_a)
            direct_mappings_english = info.get("mixins", [])
            direct_mappings = {self._convert_to_biolink_camelcase(mapping_english)
                               for mapping_english in direct_mappings_english}
            for direct_mapping in direct_mappings:
                category_dag.add_edge(direct_mapping, class_name)

            # Record node metadata
            self._add_node_if_doesnt_exist(category_dag, class_name)
            if info.get("mixin"):
                category_dag.nodes[class_name]["is_mixin"] = True

        # Last, filter out things that are not categories (Biolink 'classes' includes other things too..)
        non_category_node_ids = [node_id for node_id, data in category_dag.nodes(data=True)
                                  if not (self.root_category in self._get_ancestors_nx(category_dag, node_id)
                                          or data.get("is_mixin"))]
        for non_category_node_id in non_category_node_ids:
            category_dag.remove_node(non_category_node_id)

        return category_dag

    def _build_aspect_dag(self, biolink_model: dict) -> nx.DiGraph:
        aspect_dag = nx.DiGraph()

        aspect_enum_field_name = "gene_or_gene_product_or_chemical_entity_aspect_enum" if self.biolink_version.startswith("3.0") else "GeneOrGeneProductOrChemicalEntityAspectEnum"
        parent_to_child_dict = defaultdict(set)
        for aspect_name_english, info in biolink_model["enums"][aspect_enum_field_name]["permissible_values"].items():
            aspect_name_trapi = self._convert_to_biolink_snakecase(aspect_name_english, add_biolink_prefix=False)
            parent_name_english = info.get("is_a") if info else None
            if parent_name_english:
                parent_name_trapi = self._convert_to_biolink_snakecase(parent_name_english, add_biolink_prefix=False)
                aspect_dag.add_edge(parent_name_trapi, aspect_name_trapi)

        return aspect_dag

    def _build_direction_dag(self, biolink_model: dict) -> nx.DiGraph:
        direction_dag = nx.DiGraph()

        direction_enum_field_name = "direction_qualifier_enum" if self.biolink_version.startswith("3.0") else "DirectionQualifierEnum"
        parent_to_child_dict = defaultdict(set)
        for direction_name_english, info in biolink_model["enums"][direction_enum_field_name]["permissible_values"].items():
            direction_name_trapi = self._convert_to_biolink_snakecase(direction_name_english, add_biolink_prefix=False)
            parent_name_english = info.get("is_a") if info else None
            if parent_name_english:
                parent_name_trapi = self._convert_to_biolink_snakecase(parent_name_english, add_biolink_prefix=False)
                direction_dag.add_edge(parent_name_trapi, direction_name_trapi)

        return direction_dag
    
    def _get_depths_from_root(self, dag)-> Dict[str,int]:
        node_depths = {}
        for node in nx.topological_sort(dag):
            # Skip if the node is the start node
            
            # Get all predecessors of the current node
            predecessors = list(dag.predecessors(node))
            
            # If the node has predecessors, calculate its depth as max(depth of predecessors) + 1
            if predecessors:
                node_depths[node] = max(node_depths[pred] for pred in predecessors) + 1
            else:
                node_depths[node] = 0  # Handle nodes that have no predecessors (if any)
        
        return node_depths
    
    @staticmethod
    def _get_ancestors_nx(nx_graph: nx.DiGraph, node_id: str) -> List[str]:
        return list(nx.ancestors(nx_graph, node_id).union({node_id}))

    @staticmethod
    def _get_descendants_nx(nx_graph: nx.DiGraph, node_id: str) -> List[str]:
        return list(nx.descendants(nx_graph, node_id).union({node_id}))

    @staticmethod
    def _add_node_if_doesnt_exist(nx_graph: nx.DiGraph, node_id: str):
        if not nx_graph.has_node(node_id):
            nx_graph.add_node(node_id)

    @staticmethod
    def _convert_to_biolink_snakecase(english_term: str, add_biolink_prefix: bool = True):
        # NOTE: aspects/directions should *not* have 'biolink' prefix, that's why that is controlled via a flag..
        snakecase_term = english_term.replace(' ', '_')
        if add_biolink_prefix and not snakecase_term.startswith("biolink:"):
            return f"biolink:{snakecase_term}"
        else:
            return snakecase_term

    @staticmethod
    def _convert_to_biolink_camelcase(english_term: str):
        camel_case_class_name = "".join([f"{word[0].upper()}{word[1:]}" for word in english_term.split(" ")])
        if camel_case_class_name.startswith("biolink:"):
            return camel_case_class_name
        else:
            return f"biolink:{camel_case_class_name}"

    @staticmethod
    def _convert_to_set(items: any) -> Set[str]:
        if isinstance(items, str):
            return {items}
        elif isinstance(items, list):
            return set(items)
        elif isinstance(items, set):
            return items
        else:
            return set()

    @staticmethod
    def _serialize_with_sets(obj: any) -> any:
        return list(obj) if isinstance(obj, set) else obj


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('version', nargs='?', help="The Biolink Model version number to use")
    args = arg_parser.parse_args()

    bh = BiolinkHelper(biolink_version=args.version, is_test=True)

    assert bh.root_predicate in bh.biolink_lookup_map["predicates"]
    assert bh.root_category in bh.biolink_lookup_map["categories"]

    # Test descendants
    chemical_entity_descendants = bh.get_descendants("biolink:ChemicalEntity", include_mixins=True)
    assert "biolink:Drug" in chemical_entity_descendants
    assert "biolink:ChemicalEntity" in chemical_entity_descendants
    assert "biolink:SmallMolecule" in chemical_entity_descendants
    assert "biolink:NamedThing" not in chemical_entity_descendants
    chemical_entity_descenants_no_mixins = bh.get_descendants("biolink:ChemicalEntity", include_mixins=False)
    assert "biolink:Drug" in chemical_entity_descenants_no_mixins
    assert "biolink:NamedThing" not in chemical_entity_descenants_no_mixins

    # Test ancestors
    protein_ancestors = bh.get_ancestors("biolink:Protein", include_mixins=True)
    assert "biolink:NamedThing" in protein_ancestors
    assert "biolink:ProteinIsoform" not in protein_ancestors
    assert "biolink:GeneProductMixin" in protein_ancestors
    protein_ancestors_no_mixins = bh.get_ancestors("biolink:Protein", include_mixins=False)
    assert "biolink:NamedThing" in protein_ancestors_no_mixins
    assert "biolink:ProteinIsoform" not in protein_ancestors_no_mixins
    assert "biolink:GeneProductMixin" not in protein_ancestors_no_mixins
    assert len(protein_ancestors_no_mixins) < len(protein_ancestors)

    # Test predicates
    treats_ancestors = bh.get_ancestors("biolink:treats")
    assert "biolink:treats_or_applied_or_studied_to_treat" in treats_ancestors
    related_to_descendants = bh.get_descendants("biolink:related_to", include_mixins=True)
    assert "biolink:treats" in related_to_descendants
    assert "biolink:same_as" in bh.get_descendants("biolink:close_match")
    assert "biolink:close_match" in bh.get_ancestors("biolink:same_as")

    # Test lists
    combined_ancestors = bh.get_ancestors(["biolink:Gene", "biolink:Drug"])
    assert "biolink:Drug" in combined_ancestors
    assert "biolink:Gene" in combined_ancestors
    assert "biolink:BiologicalEntity" in combined_ancestors

    # Test conflations
    protein_ancestors = bh.get_ancestors("biolink:Protein", include_conflations=True)
    assert "biolink:Gene" in protein_ancestors
    gene_descendants = bh.get_descendants("biolink:Gene", include_conflations=True)
    assert "biolink:Protein" in gene_descendants
    gene_conflations = bh.add_conflations("biolink:Gene")
    assert set(gene_conflations) == {"biolink:Gene", "biolink:Protein"}

    # Test canonical predicates
    canonical_treated_by = bh.get_canonical_predicates("biolink:treated_by")
    canonical_treats = bh.get_canonical_predicates("biolink:treats")
    assert canonical_treated_by == ["biolink:treats"]
    assert canonical_treats == ["biolink:treats"]
    canonical_related_to = bh.get_canonical_predicates("biolink:related_to")
    assert canonical_related_to == ["biolink:related_to"]
    assert bh.get_canonical_predicates("biolink:superclass_of") == ["biolink:subclass_of"]

    # Test filtering out mixins
    mixin_less_list = bh.filter_out_mixins(["biolink:Protein", "biolink:Drug", "biolink:PhysicalEssence"])
    assert set(mixin_less_list) == {"biolink:Protein", "biolink:Drug"}

    # Test treats predicates
    treats_or_descendants = bh.get_descendants("biolink:treats_or_applied_or_studied_to_treat",
                                               include_mixins=True)
    print(f"Descendants of 'biolink:treats_or_applied_or_studied_to_treat are: \n{treats_or_descendants}")
    assert "biolink:treats" in treats_or_descendants
    assert "biolink:applied_to_treat" in treats_or_descendants
    assert "biolink:ameliorates_condition" in treats_or_descendants
    assert "biolink:treats" in bh.get_descendants("biolink:related_to",
                                                  include_mixins=True)

    # Test predicate symmetry
    assert bh.is_symmetric("biolink:related_to")
    assert bh.is_symmetric("biolink:close_match")
    assert not bh.is_symmetric("biolink:subclass_of")

    # Test getting biolink version
    biolink_version = bh.get_current_arax_biolink_version()
    assert biolink_version >= "2.1.0"

    # Test aspects
    assert "molecular_modification" in bh.get_ancestors("ribosylation")
    assert "activity" in bh.get_descendants("activity_or_abundance")

    # Test directions
    assert "increased" in bh.get_ancestors("upregulated")
    assert "downregulated" in bh.get_descendants("decreased")

    # Test excluding mixins
    assert "biolink:treats" not in bh.get_descendants("biolink:related_to", include_mixins=False)

    # Test replacing mixins with direct mappings TODO: remove after usages of this method in Plover are removed..
    assert ["biolink:treats"] == bh.replace_mixins_with_direct_mappings(["biolink:treats"])

    print("All BiolinkHelper tests passed!")


if __name__ == "__main__":
    main()
