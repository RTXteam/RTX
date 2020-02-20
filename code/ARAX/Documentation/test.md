#ARAX_overlay
| action | max_num |
|-----|-----|
| {'add_node_pmids'} | {0, 'all'} |

| action | paired_concept_freq | observed_expected_ratio | virtual_edge_type | source_qnode_id | target_qnode_id |
|-----|-----|-----|-----|-----|-----|
| {'overlay_clinical_info'} | {'true', 'false'} | {'true', 'false'} | {'any string label (optional)'} | {'a specific source query node id (optional)'} | {'a specific target query node id (optional)'} |

| action | start_node_id | intermediate_node_id | end_node_id | virtual_edge_type |
|-----|-----|-----|-----|-----|
| {'compute_jaccard'} | {'a node id'} | {'a node id'} | {'a node id'} | {'any string label'} |

| action | default_value |
|-----|-----|
| {'compute_ngd'} | {'inf', '0'} |

#ARAX_filter_kg
| action | edge_attribute | direction | threshold | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|-----|-----|
| {'remove_edges_by_attribute'} | {'an edge attribute name'} | {'below', 'above'} | {'a floating point number'} | {'False', 't', 'True', 'true', 'T', 'false', 'f', 'F'} | {'a specific query node id to remove'} |

| action | node_type |
|-----|-----|
| {'remove_nodes_by_type'} | {'a node type'} |

| action | edge_property | property_value | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|-----|
| {'remove_edges_by_property'} | {'an edge property'} | {'a value for the edge property'} | {'False', 't', 'True', 'true', 'T', 'false', 'f', 'F'} | {'a specific query node id to remove'} |

| action | edge_type | remove_connected_nodes | qnode_id |
|-----|-----|-----|-----|
| {'remove_edges_by_type'} | {'an edge type'} | {'False', 't', 'True', 'true', 'T', 'false', 'f', 'F'} | {'a specific query node id to remove'} |

