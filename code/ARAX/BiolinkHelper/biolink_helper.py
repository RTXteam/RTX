#!/bin/env python3
import os
import pathlib
import pickle
import sys
from collections import defaultdict
from typing import Optional, List, Set, Dict, Union, Tuple

import requests
import yaml
from treelib import Tree

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse


class BiolinkHelper:

    def __init__(self, biolink_version: Optional[str] = None, log: ARAXResponse = ARAXResponse()):
        self.log = log
        self.biolink_version = biolink_version if biolink_version else self.get_current_arax_biolink_version()
        biolink_helper_dir = os.path.dirname(os.path.abspath(__file__))
        self.biolink_lookup_map_path = f"{biolink_helper_dir}/biolink_lookup_map_{self.biolink_version}.pickle"
        self.biolink_lookup_map = self._load_biolink_lookup_map()

    def get_ancestors(self, biolink_items: Union[str, List[str]], include_mixins: bool = True) -> List[str]:
        input_item_set = self._convert_to_set(biolink_items)
        categories = input_item_set.intersection(set(self.biolink_lookup_map["categories"]))
        predicates = input_item_set.intersection(set(self.biolink_lookup_map["predicates"]))
        ancestors = input_item_set
        for category in categories:
            ancestors.update(self.biolink_lookup_map["categories"][category]["ancestors"])
        for predicate in predicates:
            ancestors.update(self.biolink_lookup_map["predicates"][predicate]["ancestors"])
        return list(ancestors)

    def get_descendants(self, biolink_items: Union[str, List[str]], include_mixins: bool = True) -> List[str]:
        input_item_set = self._convert_to_set(biolink_items)
        categories = input_item_set.intersection(set(self.biolink_lookup_map["categories"]))
        predicates = input_item_set.intersection(set(self.biolink_lookup_map["predicates"]))
        descendants = input_item_set
        for category in categories:
            descendants.update(self.biolink_lookup_map["categories"][category]["descendants"])
        for predicate in predicates:
            descendants.update(self.biolink_lookup_map["predicates"][predicate]["descendants"])
        return list(descendants)

    def filter_out_mixins(self, predicates: List[str]) -> List[str]:
        pass

    def get_canonical_predicates(self, predicates: Union[str, List[str]]) -> List[str]:
        input_predicate_set = self._convert_to_set(predicates)
        valid_predicates = input_predicate_set.intersection(self.biolink_lookup_map["predicates"])
        invalid_predicates = input_predicate_set.difference(valid_predicates)
        if invalid_predicates:
            self.log.warning(f"Provided predicate(s) {invalid_predicates} do not exist in Biolink {self.biolink_version}")
        canonical_predicates = {self.biolink_lookup_map["predicates"][predicate]["canonical_predicate"]
                                for predicate in valid_predicates}
        canonical_predicates.update(invalid_predicates)  # Go ahead and include those we don't have canonical info for
        return list(canonical_predicates)

    @staticmethod
    def get_current_arax_biolink_version() -> str:
        # Grab the current ARAX Biolink version from the OpenAPI yaml
        code_dir = f"{os.path.dirname(os.path.abspath(__file__))}/../.."
        openapi_yaml_path = f"{code_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml"
        with open(openapi_yaml_path) as api_file:
            openapi_yaml = yaml.safe_load(api_file)
        biolink_version = openapi_yaml["info"]["x-translator"]["biolink-version"]
        return biolink_version

    # -------------------------------- Internal methods -------------------------------------------------- #

    def _load_biolink_lookup_map(self):
        lookup_map_file = pathlib.Path(self.biolink_lookup_map_path)
        if not lookup_map_file.exists():
            # Parse the relevant Biolink yaml file and create/save local indexes
            return self._create_biolink_lookup_map()
        else:
            # A local file already exists for this Biolink version, so just load it
            self.log.debug(f"Loading Biolink {self.biolink_version} lookup map")
            with open(self.biolink_lookup_map_path, "rb") as biolink_map_file:
                biolink_lookup_map = pickle.load(biolink_map_file)
            return biolink_lookup_map

    def _create_biolink_lookup_map(self) -> Dict[str, Dict[str, Dict[str, Union[str, List[str]]]]]:
        self.log.debug(f"Building local Biolink {self.biolink_version} ancestor/descendant lookup map because one "
                       f"doesn't yet exist")
        biolink_lookup_map = {"predicates": dict(), "categories": dict()}
        # Grab the relevant Biolink yaml file
        response = requests.get(f"https://raw.githubusercontent.com/biolink/biolink-model/{self.biolink_version}/biolink-model.yaml",
                                timeout=10)
        if response.status_code == 200:
            # Build predicate and category trees from the Biolink yaml
            biolink_model = yaml.safe_load(response.text)
            predicate_tree, canonical_predicate_map = self._build_predicate_tree(biolink_model)
            category_tree = self._build_category_tree(biolink_model)

            # Then flatmap all info we need for easy access
            for predicate_node in predicate_tree.all_nodes():
                predicate = predicate_node.identifier
                biolink_lookup_map["predicates"][predicate] = {
                    "descendants": self._get_descendants_from_tree(predicate, predicate_tree),
                    "ancestors": self._get_ancestors_from_tree(predicate, predicate_tree),
                    "canonical_predicate": canonical_predicate_map.get(predicate, predicate)
                }
            for category_node in category_tree.all_nodes():
                category = category_node.identifier
                biolink_lookup_map["categories"][category] = {
                    "descendants": self._get_descendants_from_tree(category, category_tree),
                    "ancestors": self._get_ancestors_from_tree(category, category_tree)
                }

            # And cache it (never needs to be refreshed for the given Biolink version)
            with open(self.biolink_lookup_map_path, "wb") as output_file:
                pickle.dump(biolink_lookup_map, output_file)
        else:
            self.log.error(f"Unable to load Biolink yaml file.", error_code="BiolinkLoadError")

        return biolink_lookup_map

    def _build_predicate_tree(self, biolink_model: dict) -> Tuple[Tree, Dict[str, str]]:
        # Build helper maps for predicates
        root_predicate = "biolink:related_to"
        parent_to_child_dict = defaultdict(set)
        canonical_predicate_map = dict()
        predicate_tree = Tree()
        for slot_name_english, info in biolink_model["slots"].items():
            slot_name = self._convert_english_predicate_to_trapi_format(slot_name_english)
            parent_name_english = info.get("is_a")
            if parent_name_english:
                parent_name = self._convert_english_predicate_to_trapi_format(parent_name_english)
                parent_to_child_dict[parent_name].add(slot_name)
            if info.get("inverse"):
                inverse_predicate_english = info["inverse"]
                inverse_info = biolink_model["slots"][inverse_predicate_english]
                if inverse_info.get("annotations"):
                    # Hack around a bug in the biolink yaml file (blank line causing parse issues)
                    annotations = inverse_info["annotations"][0] if isinstance(inverse_info["annotations"], list) else inverse_info["annotations"]
                    if annotations.get("tag") == "biolink:canonical_predicate" and annotations.get("value"):
                        canonical_predicate = self._convert_english_predicate_to_trapi_format(inverse_predicate_english)
                        canonical_predicate_map[slot_name] = canonical_predicate
        # Recursively build the predicates tree starting with the root
        predicate_tree.create_node(root_predicate, root_predicate)
        self._create_tree_recursive(root_predicate, parent_to_child_dict, predicate_tree)
        return predicate_tree, canonical_predicate_map

    def _build_category_tree(self, biolink_model: dict) -> Tree:
        # Build helper maps for predicates
        root_category = "biolink:NamedThing"
        parent_to_child_dict = defaultdict(set)
        category_tree = Tree()
        for class_name_english, info in biolink_model["classes"].items():
            class_name = self._convert_english_category_to_trapi_format(class_name_english)
            parent_name_english = info.get("is_a")
            if parent_name_english:
                parent_name = self._convert_english_category_to_trapi_format(parent_name_english)
                parent_to_child_dict[parent_name].add(class_name)
        # Recursively build the categories tree starting with the root
        category_tree.create_node(root_category, root_category)
        self._create_tree_recursive(root_category, parent_to_child_dict, category_tree)
        return category_tree

    def _create_tree_recursive(self, root_id: str, parent_to_child_map: defaultdict, tree: Tree):
        for child_id in parent_to_child_map.get(root_id, []):
            tree.create_node(child_id, child_id, parent=root_id)
            self._create_tree_recursive(child_id, parent_to_child_map, tree)

    @staticmethod
    def _get_ancestors_from_tree(node_identifier: str, tree: Tree) -> Set[str]:
        ancestors = {node_identifier for node_identifier in tree.rsearch(node_identifier)}
        return ancestors

    @staticmethod
    def _get_descendants_from_tree(node_identifier: str, tree: Tree) -> Set[str]:
        sub_tree = tree.subtree(node_identifier)
        descendants = {node.identifier for node in sub_tree.all_nodes()}
        return descendants

    @staticmethod
    def _convert_english_predicate_to_trapi_format(english_predicate: str):
        return f"biolink:{english_predicate.replace(' ', '_')}"

    @staticmethod
    def _convert_english_category_to_trapi_format(english_category: str):
        camel_case_class_name = "".join([f"{word[0].upper()}{word[1:]}" for word in english_category.split(" ")])
        return f"biolink:{camel_case_class_name}"

    @staticmethod
    def _convert_to_set(items: any) -> Set[str]:
        if isinstance(items, str):
            return {items}
        elif isinstance(items, list):
            return set(items)
        else:
            return set()
