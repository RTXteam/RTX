# ARAX_overlay
| action | start_node_id | intermediate_node_id | end_node_id | virtual_edge_type |
|-----|-----|-----|-----|-----|
| {'compute_jaccard'} | {'a node id'} | {'a node id'} | {'a node id'} | {'any string label'} |

| action | paired_concept_freq | observed_expected_ratio | chi_square | virtual_edge_type | source_qnode_id | target_qnode_id |
|-----|-----|-----|-----|-----|-----|-----|
| {'overlay_clinical_info'} | {'false', 'true'} | {'false', 'true'} | {'false', 'true'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

| action | default_value | virtual_edge_type | source_qnode_id | target_qnode_id |
|-----|-----|-----|-----|-----|
| {'compute_ngd'} | {'inf', '0'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

| action | max_num |
|-----|-----|
| {'add_node_pmids'} | {'all', 0} |

# ARAX_filter_kg
| action | node_type |
|-----|-----|
| {'remove_nodes_by_type'} | {'a node type'} |

| action | edge_type | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|
| {'remove_edges_by_type'} | {'an edge type'} | {'T', 'f', 'True', 'False', 'true', 'false', 't', 'F'} | {'a specific query node id to remove'} |

| action | edge_property | property_value | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|-----|
| {'remove_edges_by_property'} | {'an edge property'} | {'a value for the edge property'} | {'T', 'f', 'True', 'False', 'true', 'false', 't', 'F'} | {'a specific query node id to remove'} |

| action | edge_attribute | direction | threshold | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|-----|-----|
| {'remove_edges_by_attribute'} | {'an edge attribute name'} | {'above', 'below'} | {'a floating point number'} | {'T', 'f', 'True', 'False', 'true', 'false', 't', 'F'} | {'a specific query node id to remove'} |

