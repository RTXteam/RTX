# ruff: noqa: E402
"""
Utilities for removing nodes from an ARAX knowledge graph based on a variety
of filtering criteria.

This module defines the `RemoveNodes` class, which provides methods to modify
a Translator Reasoner API (TRAPI) `KnowledgeGraph` by removing nodes (and their
associated edges) according to user-specified parameters or predefined rules.

Supported removal strategies include:
- Removing nodes by Biolink category (`remove_nodes_by_category`)
- Removing nodes by property/value match (`remove_nodes_by_property`)
- Removing orphaned nodes (nodes not connected to any edges)
  (`remove_orphaned_nodes`)
- Removing "general concept" nodes based on a configurable block list of CURIEs,
  synonyms, and regex patterns (`remove_general_concept_nodes`)

Key behaviors:
- When nodes are removed, all incident edges are also removed to maintain
  graph consistency.
- After certain operations (e.g., general concept filtering), orphaned nodes
  are optionally pruned.
- Nodes that correspond to orphan query graph nodes (QNodes) are preserved,
  even if they are otherwise disconnected.
- All operations are wrapped in error handling that logs structured errors
  via the ARAXResponse object rather than raising exceptions.

External dependencies:
- Relies on ARAX message/response objects and TRAPI-compliant knowledge graph
  structures.
- Loads a JSON "block list" file (`general_concepts.json`) from the ARAX
  repository to identify overly general or non-informative nodes.

Implementation notes:
- Uses defensive programming to handle heterogeneous node/edge structures
  (e.g., dict-based attributes, optional fields).
- Performs in-place mutation of the knowledge graph.
- Designed for use within ARAX query processing pipelines rather than as a
  standalone utility.

Limitations:
- Assumes a Unix-like filesystem layout for locating the ARAX repository.
- Block-list matching is heuristic and may not capture all general concepts.
- Some operations rely on `node.to_dict()` representations, which may incur
  overhead for large graphs.

Static code checks:
- ruff check Filter_KG/remove_nodes.py
- mypy --ignore-missing-imports/remove_nodes.py
- pylint Filter_KG.remove_nodes

This module is intended for internal use within ARAX and related Translator
Reasoner workflows.
"""
import traceback
import json
import re
import sys
from pathlib import Path
from typing import Any, ClassVar

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE / ".."))
from ARAX_response import ARAXResponse  # pylint: disable=wrong-import-position
from ARAX_messenger import ARAXMessenger  # pylint: disable=wrong-import-position

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class RemoveNodes:

    # the first ARAX query loads the blocklist file, but ever after, just use the
    # blocklist data that has been cached as a class attribute `block_list_dict`
    block_list_dict: ClassVar[dict[str, Any] | None] = None

    def __init__(self,
                 response: ARAXResponse,
                 message: ARAXMessenger,
                 params: dict[str, Any]):
        self.response = response
        self.message = message
        self.node_parameters = params
        if RemoveNodes.block_list_dict is None:
            # we should only get here if we are running outside of the Flask app
            response.info("loading blocklist file of overly general concept nodes")
            RemoveNodes.load_block_list_file()
        if RemoveNodes.block_list_dict is None:
            raise RuntimeError("RemoveNodes: unable to load block_list dictionary")
        self.block_list_synonyms = None
        self.block_list_curies = None
        self.block_list_patterns = None

    @classmethod
    def load_block_list_file(cls):
        if cls.block_list_dict is not None:
            return
        block_list_file = HERE / ".." / ".." / "KnowledgeSources" / "general_concepts.json"
        try:
            eprint(f"Loading overly general concepts node file: {block_list_file}")
            with block_list_file.open(encoding="utf-8") as fp:
                cls.block_list_dict = json.load(fp)
            eprint("Successfully loaded the blocklist file")
        except (OSError, json.JSONDecodeError) as e:
            eprint(f"Unable to read ARAX node block_list file: {block_list_file}; {e}")

    def remove_nodes_by_category(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching
        the discription provided.
        :return: response
        """
        self.response.debug("Removing Nodes")
        self.response.info("Removing nodes from the knowledge graph matching the specified "
                           "category")
        try:
            nodes_to_remove = set()
            # iterate over the edges find the edges to remove
            for key, node in self.message.knowledge_graph.nodes.items():
                if self.node_parameters['node_category'] in node.categories:
                    nodes_to_remove.add(key)

            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for key, edge in self.message.knowledge_graph.edges.items():
                if edge.subject in nodes_to_remove or edge.object in nodes_to_remove:
                    edges_to_remove.add(key)
            # remove edges
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except (AttributeError, KeyError, TypeError) as e:
            tb = traceback.format_exc()
            self.response.error(tb, error_code=type(e).__name__)
            self.response.error("Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info("Nodes successfully removed")

        return self.response

    def remove_nodes_by_property(self):
        """
        Iterate over all the nodes in the knowledge graph, remove any nodes matching the
        discription provided.
        :return: response
        """
        self.response.debug("Removing Nodes")
        self.response.info("Removing nodes from the knowledge graph matching the specified "
                           "property")
        node_params = self.node_parameters
        try:
            nodes_to_remove = set()
            # iterate over the nodes find the nodes to remove
            for key, node in self.message.knowledge_graph.nodes.items():
                node_dict = node.to_dict()
                if node_params['node_property'] in node_dict:
                    if isinstance(node_dict[node_params['node_property']], list):
                        if node_params['property_value'] in node_dict[node_params['node_property']]:
                            nodes_to_remove.add(key)
                        elif node_dict[node_params['node_property']] == \
                             node_params['property_value']:
                            nodes_to_remove.add(key)
                    else:
                        if node_dict[node_params['node_property']] == node_params['property_value']:
                            nodes_to_remove.add(key)
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for key, edge in self.message.knowledge_graph.edges.items():
                if edge.subject in nodes_to_remove or edge.object in nodes_to_remove:
                    edges_to_remove.add(key)
            # remove edges
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except (AttributeError, KeyError, TypeError) as e:
            tb = traceback.format_exc()
            self.response.error(tb, error_code=type(e).__name__)
            self.response.error("Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info("Nodes successfully removed")

        return self.response

    def remove_orphaned_nodes(self):
        """
        Iterate over all the nodes/edges in the knowledge graph, remove any nodes not connected
        to edges (optionally matching the type provided)
        :return: response
        """
        self.response.debug("Removing orphaned nodes")
        self.response.info("Removing orphaned nodes")
        node_parameters = self.node_parameters

        try:
            # iterate over edges in KG to find all id's that connect the edges
            connected_node_keys = set()
            for edge in self.message.knowledge_graph.edges.values():
                connected_node_keys.add(edge.subject)
                connected_node_keys.add(edge.object)

            # Identify all orphan nodes in the KG
            nodes_to_remove = set()
            for key, node in self.message.knowledge_graph.nodes.items():
                if 'node_category' in node_parameters \
                   and node_parameters['node_category'] in node.categories:
                    if key not in connected_node_keys:
                        nodes_to_remove.add(key)
                else:
                    if key not in connected_node_keys:
                        nodes_to_remove.add(key)

            # Determine which nodes are supposed to be orphans (if any)
            qg = self.message.query_graph
            all_qnode_ids = set(qg.nodes)
            connected_qnode_ids = {node_id \
                                   for qedge in qg.edges.values() \
                                   for node_id in (qedge.subject, qedge.object)}
            orphan_qnode_ids = all_qnode_ids.difference(connected_qnode_ids)
            orphan_node_keys = set()
            # Don't filter out nodes that are supposed to be orphans #2306
            for node_key in nodes_to_remove:
                node = self.message.knowledge_graph.nodes[node_key]
                if set(node.qnode_keys).intersection(orphan_qnode_ids):
                    orphan_node_keys.add(node_key)
            if orphan_node_keys:
                self.response.debug(f"Leaving {len(orphan_node_keys)} orphan nodes "
                                    "in the KG because they fulfill an "
                                    f"orphan qnode ({orphan_qnode_ids})")
            nodes_to_remove = nodes_to_remove.difference(orphan_node_keys)

            # remove the orphaned nodes
            self.response.debug(f"Identified {len(nodes_to_remove)} orphan nodes to remove")
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
        except (AttributeError, KeyError, TypeError) as e:
            tb = traceback.format_exc()
            self.response.error(tb, error_code=type(e).__name__)
            self.response.error("Something went wrong removing orphaned nodes from the "
                                "knowledge graph")
        else:
            self.response.info("Nodes successfully removed")

        return self.response

    def _is_general_concept(self, node):
        curies = set()
        synonyms = set()
        if not node['attributes']:
            return False
        for attribute in node['attributes']:
            if attribute['attribute_type_id'] == 'biolink:xref' \
               and isinstance(attribute.get('value', []),list):
                curies.update(map(str.lower, attribute.get('value', [])))
            if attribute['attribute_type_id'] == 'biolink:synonym' \
               and  isinstance(attribute.get('value', []),list):
                synonyms.update(map(str.lower, attribute.get('value', [])))
        if node['name']:
            synonyms.add(node['name'].lower())
        if self.block_list_curies.intersection(curies) \
           or self.block_list_synonyms.intersection(synonyms):
            return True

        for synonym in synonyms:
            if not isinstance(synonym,str):
                continue
            if any(p.match(synonym) for p in self.block_list_patterns):
                return True
        return False

    @classmethod
    def _get_block_list_dict(cls) -> dict[str, Any]:
        if not isinstance(cls.block_list_dict, dict):
            raise RuntimeError("block_list_dict not initialized")
        return cls.block_list_dict

    def remove_general_concept_nodes(self):
        node_params = self.node_parameters
        if 'perform_action' not in node_params:
            node_params['perform_action'] = True
        elif node_params['perform_action'] in {'true', 'True', 't', 'T'}:
            node_params['perform_action'] = True
        elif node_params['perform_action'] in {'false', 'False', 'f', 'F'}:
            node_params['perform_action'] = False
        if not node_params['perform_action']:
            return self.response
        self.response.info("Removing nodes from the knowledge graph which are blocklisted (overly general) concepts")
        block_list_dict = RemoveNodes._get_block_list_dict()
        try:
            self.block_list_synonyms = set(block_list_dict["synonyms"])  # pylint: disable=unsubscriptable-object
            self.block_list_curies = set(block_list_dict["curies"])  # pylint: disable=unsubscriptable-object
            node_to_remove = set()
            self.block_list_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in block_list_dict["patterns"]  # pylint: disable=unsubscriptable-object
            ]
            edges_to_remove = []
            for key, edge in self.message.knowledge_graph.edges.items():
                if {edge.subject, edge.object}.intersection(node_to_remove):
                    edges_to_remove.append(key)
                    continue
                subject_node = self.message.knowledge_graph.nodes[edge.subject].to_dict()
                object_node = self.message.knowledge_graph.nodes[edge.object].to_dict()

                if self._is_general_concept(subject_node):
                    node_to_remove.add(edge.subject)
                    edges_to_remove.append(key)
                    continue

                if self._is_general_concept(object_node):
                    node_to_remove.add(edge.object)
                    edges_to_remove.append(key)
                    continue
            for edge_id in edges_to_remove:
                del self.message.knowledge_graph.edges[edge_id]
            self.remove_orphaned_nodes()
        except (KeyError, TypeError, AttributeError, re.error) as e:
            tb = traceback.format_exc()
            self.response.error(tb, error_code=type(e).__name__)
            self.response.error("Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info("Nodes successfully removed")

        return self.response
