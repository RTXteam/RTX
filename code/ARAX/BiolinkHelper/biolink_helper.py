#!/bin/env python3
import json
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
        """
        Returns the ancestors of Biolink categories, predicates, category mixins, or predicate mixins. Input
        categories/predicates/mixins are themselves included in the returned ancestor list. For categories/predicates,
        inclusion of mixin ancestors can be turned on or off via the include_mixins flag.
        """
        input_item_set = self._convert_to_set(biolink_items)
        categories = input_item_set.intersection(set(self.biolink_lookup_map["categories"]))
        predicates = input_item_set.intersection(set(self.biolink_lookup_map["predicates"]))
        category_mixins = input_item_set.intersection(set(self.biolink_lookup_map["category_mixins"]))
        predicate_mixins = input_item_set.intersection(set(self.biolink_lookup_map["predicate_mixins"]))
        ancestors = input_item_set.copy()
        ancestor_property = "ancestors_with_mixins" if include_mixins else "ancestors"
        for category in categories:
            ancestors.update(self.biolink_lookup_map["categories"][category][ancestor_property])
        for predicate in predicates:
            ancestors.update(self.biolink_lookup_map["predicates"][predicate][ancestor_property])
        for category_mixin in category_mixins:
            ancestors.update(self.biolink_lookup_map["category_mixins"][category_mixin]["ancestors"])
        for predicate_mixin in predicate_mixins:
            ancestors.update(self.biolink_lookup_map["predicate_mixins"][predicate_mixin]["ancestors"])
        return list(ancestors)

    def get_descendants(self, biolink_items: Union[str, List[str]], include_mixins: bool = True) -> List[str]:
        """
        Returns the descendants of Biolink categories, predicates, category mixins, or predicate mixins. Input
        categories/predicates/mixins are themselves included in the returned descendant list. For categories/predicates,
        inclusion of mixin descendants can be turned on or off via the include_mixins flag.
        """
        input_item_set = self._convert_to_set(biolink_items)
        categories = input_item_set.intersection(set(self.biolink_lookup_map["categories"]))
        predicates = input_item_set.intersection(set(self.biolink_lookup_map["predicates"]))
        category_mixins = input_item_set.intersection(set(self.biolink_lookup_map["category_mixins"]))
        predicate_mixins = input_item_set.intersection(set(self.biolink_lookup_map["predicate_mixins"]))
        descendants = input_item_set.copy()
        descendant_property = "descendants_with_mixins" if include_mixins else "descendants"
        for category in categories:
            descendants.update(self.biolink_lookup_map["categories"][category][descendant_property])
        for predicate in predicates:
            descendants.update(self.biolink_lookup_map["predicates"][predicate][descendant_property])
        for category_mixin in category_mixins:
            descendants.update(self.biolink_lookup_map["category_mixins"][category_mixin]["descendants"])
        for predicate_mixin in predicate_mixins:
            descendants.update(self.biolink_lookup_map["predicate_mixins"][predicate_mixin]["descendants"])
        return list(descendants)

    def get_canonical_predicates(self, predicates: Union[str, List[str]]) -> List[str]:
        """
        Returns the canonical version of the input predicate(s). Accepts a single predicate or multiple predicates as
        input and always returns the canonical predicate(s) in a list.
        """
        # TODO: Add canonical predicates for predicate mixins?
        input_predicate_set = self._convert_to_set(predicates)
        valid_predicates = input_predicate_set.intersection(self.biolink_lookup_map["predicates"])
        invalid_predicates = input_predicate_set.difference(valid_predicates)
        if invalid_predicates:
            self.log.warning(f"Provided predicate(s) {invalid_predicates} do not exist in Biolink {self.biolink_version}")
        canonical_predicates = {self.biolink_lookup_map["predicates"][predicate]["canonical_predicate"]
                                for predicate in valid_predicates}
        canonical_predicates.update(invalid_predicates)  # Go ahead and include those we don't have canonical info for
        return list(canonical_predicates)

    def filter_out_mixins(self, biolink_items: List[str]) -> List[str]:
        """
        Removes any predicate or category mixins in the input list.
        """
        input_item_set = set(biolink_items)
        all_predicate_mixins = set(self.biolink_lookup_map["predicate_mixins"])
        all_category_mixins = set(self.biolink_lookup_map["category_mixins"])
        non_mixin_items = input_item_set.difference(all_predicate_mixins).difference(all_category_mixins)
        return list(non_mixin_items)

    @staticmethod
    def get_current_arax_biolink_version() -> str:
        """
        Returns the current Biolink version that the ARAX system is using, according to the OpenAPI YAML file.
        """
        code_dir = f"{os.path.dirname(os.path.abspath(__file__))}/../.."
        openapi_yaml_path = f"{code_dir}/UI/OpenAPI/python-flask-server/openapi_server/openapi/openapi.yaml"
        with open(openapi_yaml_path) as api_file:
            openapi_yaml = yaml.safe_load(api_file)
        biolink_version = openapi_yaml["info"]["x-translator"]["biolink-version"]
        return biolink_version

    # ------------------------------------- Internal methods -------------------------------------------------- #

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
        biolink_lookup_map = {"predicates": dict(), "categories": dict(),
                              "predicate_mixins": dict(), "category_mixins": dict()}
        # Grab the relevant Biolink yaml file
        response = requests.get(f"https://raw.githubusercontent.com/biolink/biolink-model/{self.biolink_version}/biolink-model.yaml",
                                timeout=10)
        if response.status_code == 200:
            # Build predicate and category trees from the Biolink yaml
            biolink_model = yaml.safe_load(response.text)
            predicate_tree, canonical_predicate_map, predicate_to_mixins_map, predicate_mixin_tree = self._build_predicate_trees(biolink_model)
            category_tree, category_to_mixins_map, category_mixin_tree = self._build_category_trees(biolink_model)
            print(predicate_mixin_tree)
            print(category_mixin_tree)

            # Then flatmap all info we need for easy access
            for predicate_mixin_node in predicate_mixin_tree.all_nodes():
                predicate_mixin = predicate_mixin_node.identifier
                ancestors = self._get_ancestors_from_tree(predicate_mixin, predicate_mixin_tree)
                biolink_lookup_map["predicate_mixins"][predicate_mixin] = {
                    "ancestors": ancestors.difference({"MIXIN"}),  # Our made-up root doesn't count as an ancestor
                    "descendants": self._get_descendants_from_tree(predicate_mixin, predicate_mixin_tree)
                }
            for category_mixin_node in category_mixin_tree.all_nodes():
                category_mixin = category_mixin_node.identifier
                ancestors = self._get_ancestors_from_tree(category_mixin, category_mixin_tree)
                biolink_lookup_map["category_mixins"][category_mixin] = {
                    "ancestors": ancestors.difference({"MIXIN"}),  # Our made-up root doesn't count as an ancestor
                    "descendants": self._get_descendants_from_tree(category_mixin, category_mixin_tree)
                }
            for predicate_node in predicate_tree.all_nodes():
                predicate = predicate_node.identifier
                ancestors = self._get_ancestors_from_tree(predicate, predicate_tree)
                descendants = self._get_descendants_from_tree(predicate, predicate_tree)
                direct_mixins = predicate_to_mixins_map[predicate]
                mixin_ancestors = {mixin_ancestor for mixin in direct_mixins
                                   for mixin_ancestor in biolink_lookup_map["predicate_mixins"][mixin]["ancestors"]}
                mixin_descendants = {mixin_descendant for mixin in direct_mixins
                                     for mixin_descendant in biolink_lookup_map["predicate_mixins"][mixin]["descendants"]}
                biolink_lookup_map["predicates"][predicate] = {
                    "ancestors": ancestors,
                    "descendants": descendants,
                    "ancestors_with_mixins": ancestors.union(mixin_ancestors),
                    "descendants_with_mixins": descendants.union(mixin_descendants),
                    "canonical_predicate": canonical_predicate_map.get(predicate, predicate),
                    "direct_mixins": direct_mixins,
                }
            for category_node in category_tree.all_nodes():
                category = category_node.identifier
                ancestors = self._get_ancestors_from_tree(category, category_tree)
                descendants = self._get_descendants_from_tree(category, category_tree)
                direct_mixins = category_to_mixins_map[category]
                mixin_ancestors = {mixin_ancestor for mixin in direct_mixins
                                   for mixin_ancestor in biolink_lookup_map["category_mixins"][mixin]["ancestors"]}
                mixin_descendants = {mixin_descendant for mixin in direct_mixins
                                     for mixin_descendant in biolink_lookup_map["category_mixins"][mixin]["descendants"]}
                biolink_lookup_map["categories"][category] = {
                    "ancestors": ancestors,
                    "descendants": descendants,
                    "ancestors_with_mixins": ancestors.union(mixin_ancestors),
                    "descendants_with_mixins": descendants.union(mixin_descendants),
                    "direct_mixins": direct_mixins,
                }

            # And cache it (never needs to be refreshed for the given Biolink version)
            with open(self.biolink_lookup_map_path, "wb") as output_file:
                pickle.dump(biolink_lookup_map, output_file)  # Use pickle so we can save Sets
            # Also save a JSON version to help with debugging
            json_file_path = self.biolink_lookup_map_path.replace(".pickle", ".json")
            with open(json_file_path, "w+") as output_json_file:
                json.dump(biolink_lookup_map, output_json_file, default=self.serialize_with_sets, indent=4)
        else:
            self.log.error(f"Unable to load Biolink yaml file.", error_code="BiolinkLoadError")

        return biolink_lookup_map

    def _build_predicate_trees(self, biolink_model: dict) -> Tuple[Tree, Dict[str, str], Dict[str, List[str]], Tree]:
        root_predicate = "biolink:related_to"
        root_mixin = "MIXIN"  # This is made up for easier parsing

        # Build helper maps for predicates and their mixins
        parent_to_child_dict = defaultdict(set)
        canonical_predicate_map = dict()
        predicate_to_mixins_map = dict()
        for slot_name_english, info in biolink_model["slots"].items():
            slot_name = self._convert_english_predicate_to_trapi_format(slot_name_english)
            # Record this node underneath its parent
            parent_name_english = info.get("is_a")
            if parent_name_english:
                parent_name = self._convert_english_predicate_to_trapi_format(parent_name_english)
                parent_to_child_dict[parent_name].add(slot_name)
            # Or if it's a top-level mixin, force it to have the (made-up) root mixin as parent
            elif info.get("mixin"):
                parent_to_child_dict[root_mixin].add(slot_name)
            # Record this node's direct mixins
            mixins_english = info.get("mixins", [])
            mixins = [self._convert_english_predicate_to_trapi_format(mixin_english) for mixin_english in mixins_english]
            predicate_to_mixins_map[slot_name] = mixins
            # Record the canonical form of this predicate
            if info.get("inverse"):
                inverse_predicate_english = info["inverse"]
                inverse_info = biolink_model["slots"][inverse_predicate_english]
                if inverse_info.get("annotations"):
                    # Hack around a bug in the biolink yaml file (blank line causing parse issues)
                    annotations = inverse_info["annotations"][0] if isinstance(inverse_info["annotations"], list) else inverse_info["annotations"]
                    if annotations.get("tag") == "biolink:canonical_predicate" and annotations.get("value"):
                        canonical_predicate = self._convert_english_predicate_to_trapi_format(inverse_predicate_english)
                        canonical_predicate_map[slot_name] = canonical_predicate

        # Recursively build the predicates trees starting with the root
        predicate_tree = Tree()
        predicate_tree.create_node(root_predicate, root_predicate)
        self._create_tree_recursive(root_predicate, parent_to_child_dict, predicate_tree)
        predicate_mixin_tree = Tree()
        predicate_mixin_tree.create_node(root_mixin, root_mixin)
        self._create_tree_recursive(root_mixin, parent_to_child_dict, predicate_mixin_tree)

        return predicate_tree, canonical_predicate_map, predicate_to_mixins_map, predicate_mixin_tree

    def _build_category_trees(self, biolink_model: dict) -> Tuple[Tree, Dict[str, List[str]], Tree]:
        root_category = "biolink:NamedThing"
        root_mixin = "MIXIN"  # This is made up for easier parsing

        # Build helper maps for categories and their mixins
        parent_to_child_dict = defaultdict(set)
        category_to_mixins_map = dict()
        for class_name_english, info in biolink_model["classes"].items():
            class_name = self._convert_english_category_to_trapi_format(class_name_english)
            # Record this node underneath its parent
            parent_name_english = info.get("is_a")
            if parent_name_english:
                parent_name = self._convert_english_category_to_trapi_format(parent_name_english)
                parent_to_child_dict[parent_name].add(class_name)
            # Or if it's a top-level mixin, force it to have the (made-up) root mixin as parent
            elif info.get("mixin"):
                parent_to_child_dict[root_mixin].add(class_name)
            # Record this node's direct mixins
            mixins_english = info.get("mixins", [])
            mixins = [self._convert_english_category_to_trapi_format(mixin_english) for mixin_english in mixins_english]
            category_to_mixins_map[class_name] = mixins

        # Recursively build the category trees starting with the root
        category_tree = Tree()
        category_tree.create_node(root_category, root_category)
        self._create_tree_recursive(root_category, parent_to_child_dict, category_tree)
        category_mixin_tree = Tree()
        category_mixin_tree.create_node(root_mixin, root_mixin)
        self._create_tree_recursive(root_mixin, parent_to_child_dict, category_mixin_tree)

        return category_tree, category_to_mixins_map, category_mixin_tree

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

    @staticmethod
    def serialize_with_sets(obj: any) -> any:
        return list(obj) if isinstance(obj, set) else obj
