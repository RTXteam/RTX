# ARAX_overlay
| action | paired_concept_freq | observed_expected_ratio | virtual_edge_type | source_qnode_id | target_qnode_id |
|-----|-----|-----|-----|-----|-----|
| {'overlay_clinical_info'} | {'true', 'false'} | {'true', 'false'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

| action | default_value | virtual_edge_type | source_qnode_id | target_qnode_id |
|-----|-----|-----|-----|-----|
| {'compute_ngd'} | {'inf', '0'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

| action | start_node_id | intermediate_node_id | end_node_id | virtual_edge_type |
|-----|-----|-----|-----|-----|
| {'compute_jaccard'} | {'a node id'} | {'a node id'} | {'a node id'} | {'any string label'} |

| action | max_num |
|-----|-----|
| {'add_node_pmids'} | {0, 'all'} |

# ARAX_filter_kg
| action | edge_type | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|
| {'remove_edges_by_type'} | {'an edge type'} | {'False', 'T', 'true', 't', 'f', 'F', 'false', 'True'} | {'a specific query node id to remove'} |

| action | edge_property | property_value | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|-----|
| {'remove_edges_by_property'} | {'an edge property'} | {'a value for the edge property'} | {'False', 'T', 'true', 't', 'f', 'F', 'false', 'True'} | {'a specific query node id to remove'} |

| action | node_type |
|-----|-----|
| {'remove_nodes_by_type'} | {'a node type'} |

| action | edge_attribute | direction | threshold | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|-----|-----|
| {'remove_edges_by_attribute'} | {'an edge attribute name'} | {'above', 'below'} | {'a floating point number'} | {'False', 'T', 'true', 't', 'f', 'F', 'false', 'True'} | {'a specific query node id to remove'} |

