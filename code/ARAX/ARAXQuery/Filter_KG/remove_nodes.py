# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
import os
import traceback
import json
import numpy as np
import re

class RemoveNodes:

    #### Constructor
    def __init__(self, response, message, params):
        self.response = response
        self.message = message
        self.node_parameters = params

    def remove_nodes_by_category(self):
        """
        Iterate over all the edges in the knowledge graph, remove any edges matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Nodes")
        self.response.info(f"Removing nodes from the knowledge graph matching the specified category")

        try:
            nodes_to_remove = set()
            #node_keys_to_remove = set()
            # iterate over the edges find the edges to remove
            for key, node in self.message.knowledge_graph.nodes.items():
                if self.node_parameters['node_category'] in node.categories:
                    nodes_to_remove.add(key)
                    #node_keys_to_remove.add(key)
            #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for key, edge in self.message.knowledge_graph.edges.items():
                if edge.subject in nodes_to_remove or edge.object in nodes_to_remove:
                    edges_to_remove.add(key)
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response

    def remove_nodes_by_property(self):
        """
        Iterate over all the nodes in the knowledge graph, remove any nodes matching the discription provided.
        :return: response
        """
        self.response.debug(f"Removing Nodes")
        self.response.info(f"Removing nodes from the knowledge graph matching the specified property")
        node_params = self.node_parameters
        try:
            nodes_to_remove = set()
            #node_keys_to_remove = set()
            # iterate over the nodes find the nodes to remove
            for key, node in self.message.knowledge_graph.nodes.items():
                node_dict = node.to_dict()
                if node_params['node_property'] in node_dict:
                    if isinstance(node_dict[node_params['node_property']], list):
                        if node_params['property_value'] in node_dict[node_params['node_property']]:
                            nodes_to_remove.add(key)
                        elif node_dict[node_params['node_property']] == node_params['property_value']:
                            nodes_to_remove.add(key)
                    else:
                        if node_dict[node_params['node_property']] == node_params['property_value']:
                            nodes_to_remove.add(key)
            #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in nodes_to_remove]
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
            edges_to_remove = set()
            # iterate over edges find edges connected to the nodes
            for key, edge in self.message.knowledge_graph.edges.items():
                if edge.subject in nodes_to_remove or edge.object in nodes_to_remove:
                    edges_to_remove.add(key)
            # remove edges
            #self.message.knowledge_graph.edges = [val for idx, val in enumerate(self.message.knowledge_graph.edges) if idx not in edges_to_remove]
            for key in edges_to_remove:
                del self.message.knowledge_graph.edges[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response

    def remove_orphaned_nodes(self):
        """
        Iterate over all the nodes/edges in the knowledge graph, remove any nodes not connected to edges (optionally matching the type provided)
        :return: response
        """
        self.response.debug(f"Removing orphaned nodes")
        self.response.info(f"Removing orphaned nodes")
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
                if 'node_category' in node_parameters and node_parameters['node_category'] in node.categories:
                    if key not in connected_node_keys:
                        nodes_to_remove.add(key)
                else:
                    if key not in connected_node_keys:
                        nodes_to_remove.add(key)

            # Determine which nodes are supposed to be orphans (if any)
            qg = self.message.query_graph
            all_qnode_ids = set(qg.nodes)
            connected_qnode_ids = {qnode_key for qedge in qg.edges.values()
                                   for qnode_key in {qedge.subject, qedge.object}}
            orphan_qnode_ids = all_qnode_ids.difference(connected_qnode_ids)
            orphan_node_keys = set()
            # Don't filter out nodes that are supposed to be orphans #2306
            for node_key in nodes_to_remove:
                node = self.message.knowledge_graph.nodes[node_key]
                if set(node.qnode_keys).intersection(orphan_qnode_ids):
                    orphan_node_keys.add(node_key)
            if orphan_node_keys:
                self.response.debug(f"Leaving {len(orphan_node_keys)} orphan nodes in the KG because they fulfill an "
                                    f"orphan qnode ({orphan_qnode_ids})")
            nodes_to_remove = nodes_to_remove.difference(orphan_node_keys)

            # remove the orphaned nodes
            #self.message.knowledge_graph.nodes = [val for idx, val in enumerate(self.message.knowledge_graph.nodes) if idx not in node_indexes_to_remove]
            self.response.debug(f"Identified {len(nodes_to_remove)} orphan nodes to remove")
            for key in nodes_to_remove:
                del self.message.knowledge_graph.nodes[key]
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing orphaned nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response
    
    def _is_general_concept(self, node):
        curies = set()
        synonyms = set()
        if not node['attributes']:
            return False
        for attribute in node['attributes']:
            if attribute['attribute_type_id'] == 'biolink:xref':
                curies.update(map(str.lower, attribute.get('value', [])))
            if attribute['attribute_type_id'] == 'biolink:synonym':
                synonyms.update(map(str.lower, attribute.get('value', [])))
        if node['name']:
                synonyms.add(node['name'].lower())
        if self.block_list_curies.intersection(curies) or self.block_list_synonyms.intersection(synonyms):
            return True
        
        for synonym in synonyms:
            if not isinstance(synonym,str):
                continue 
            if any(p.match(synonym) for p in self.block_list_patterns):
                return True
        return False
    
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
        self.response.debug(f"Removing Nodes")
        self.response.info(f"Removing nodes from the knowledge graph which are general concepts")
        
        
        try:
            path_list = os.path.realpath(__file__).split(os.path.sep)
            rtx_index = path_list.index("RTX")
            blocklist_file_path = os.path.sep.join([*path_list[:(rtx_index + 1)], 'code', 'ARAX', 'KnowledgeSources','general_concepts.json'])
            file_name = 'general_concepts.json'
            with open(blocklist_file_path) as fp:
                block_list_dict = json.loads(fp.read())
            self.block_list_synonyms = set(block_list_dict["synonyms"])
            self.block_list_curies = set(block_list_dict["curies"])
            node_to_remove = set()
            self.block_list_patterns = [re.compile(pattern,re.IGNORECASE) for pattern in block_list_dict["patterns"]]
            # iterate over edges find edges connected to the nodes
            edges_to_remove = []
            for key, edge in self.message.knowledge_graph.edges.items():
                if set({edge.subject, edge.object}).intersection(node_to_remove):
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
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(tb, error_code=error_type.__name__)
            self.response.error(f"Something went wrong removing nodes from the knowledge graph")
        else:
            self.response.info(f"Nodes successfully removed")

        return self.response
