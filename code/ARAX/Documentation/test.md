# ARAX_overlay
|`overlay(action=overlay_clinical_info)`|||||||
|-----|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| paired_concept_freq | observed_expected_ratio | chi_square | virtual_edge_type | source_qnode_id | target_qnode_id |
|_DSL arguments_| {'false', 'true'} | {'false', 'true'} | {'false', 'true'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

|`overlay(action=compute_jaccard)`|||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| start_node_id | intermediate_node_id | end_node_id | virtual_edge_type |
|_DSL arguments_| {'a node id'} | {'a node id'} | {'a node id'} | {'any string label'} |

|`overlay(action=add_node_pmids)`||
|-----|-----|
|_DSL parameters_| max_num |
|_DSL arguments_| {'all', 0} |

|`overlay(action=compute_ngd)`|||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| default_value | virtual_edge_type | source_qnode_id | target_qnode_id |
|_DSL arguments_| {'inf', '0'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

# ARAX_filter_kg
|`filter_kg(action=remove_edges_by_property)`|||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_property | property_value | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge property'} | {'a value for the edge property'} | {'F', 'False', 'T', 'false', 'true', 'f', 'True', 't'} | {'a specific query node id to remove'} |

|`filter_kg(action=remove_nodes_by_type)`||
|-----|-----|
|_DSL parameters_| node_type |
|_DSL arguments_| {'a node type'} |

|`filter_kg(action=remove_edges_by_attribute)`||||||
|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_attribute | direction | threshold | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge attribute name'} | {'above', 'below'} | {'a floating point number'} | {'F', 'False', 'T', 'false', 'true', 'f', 'True', 't'} | {'a specific query node id to remove'} |

|`filter_kg(action=remove_edges_by_type)`||||
|-----|-----|-----|-----|
|_DSL parameters_| edge_type | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge type'} | {'F', 'False', 'T', 'false', 'true', 'f', 'True', 't'} | {'a specific query node id to remove'} |

