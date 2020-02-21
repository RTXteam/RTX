# Domain Specific Langauage (DSL) description
This document describes the features and components of the DSL developed for the ARA Expander team.

Full documentation is given below, but an example can help: in the API specification, there is field called `Query.previous_message_processing_plan.processing_actions:`,
while initially an empty list, a set of processing actions can be applied with something along the lines of:

```
[
"add_qnode(name=hypertension, id=n00)",  # add a new node to the query graph
"add_qnode(type=protein, is_set=True, id=n01)",  # add a new set of nodes of a certain type to the query graph
"add_qedge(source_id=n01, target_id=n00, id=e00)",  # add an edge connecting these two nodes
"expand(edge_id=e00)",  # reach out to knowledge providers to find all subgraphs that satisfy these new query nodes/edges
"overlay(action=compute_ngd)",  # overlay each edge with the normalized Google distance (a metric based on Edge.source_id and Edge.target_id co-occurrence frequency in all PubMed abstracts)
"filter_kg(action=remove_edges_by_attribute, edge_attribute=ngd, direction=above, threshold=0.85, remove_connected_nodes=t, qnode_id=n01)",  # remove all edges with normalized google distance above 0.85 as well as the connected protein
"return(message=true, store=false)"  # return the message to the ARS
]
```
 
# Full documentation of current DSL commands
## ARAX_overlay
### `overlay(action=compute_ngd)`
`compute_ngd` computes a metric (called the normalized Google distance) based on edge soure/target node co-occurrence in abstracts of all PubMed articles.
            This information is then included as an edge attribute.
            You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode id's. If the later, virtual edges are added with the type specified by `virtual_edge_type`.

||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| default_value | virtual_edge_type | source_qnode_id | target_qnode_id |
|_DSL arguments_| {'inf', '0'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

### `overlay(action=add_node_pmids)`
`add_node_pmids` adds PubMed PMID's as node attributes to each node in the knowledge graph.
            This information is obtained from mapping node identifiers to MeSH terms and obtaining which PubMed articles have this MeSH term
            either labeling in the metadata or has the MeSH term occurring in the abstract of the article.

|||
|-----|-----|
|_DSL parameters_| max_num |
|_DSL arguments_| {0, 'all'} |

### `overlay(action=overlay_clinical_info)`
`overlay_clinical_info` overlay edges with information obtained from the knowledge provider (KP) Columbia Open Health Data (COHD).
            This KP has a number of different functionalities, such as `paired_concept_frequenc`, `observed_expected_ratio`, etc. which are mutually exclusive DSL parameters.
            All information is derived from a 5 year hierarchical dataset: Counts for each concept include patients from descendant concepts. 
            This includes clinical data from 2013-2017 and includes 1,731,858 different patients.
            This information is then included as an edge attribute.
            You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode id's. If the later, virtual edges are added with the type specified by `virtual_edge_type`.

||||||||
|-----|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| paired_concept_freq | observed_expected_ratio | chi_square | virtual_edge_type | source_qnode_id | target_qnode_id |
|_DSL arguments_| {'true', 'false'} | {'true', 'false'} | {'true', 'false'} | {'any string label (optional, otherwise applied to all edges)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

### `overlay(action=compute_jaccard)`
`compute_jaccard` creates virtual edges and adds an edge attribute containing the following information:
            The jaccard similarity measures how many `intermediate_node_id`'s are shared in common between each `start_node_id` and `target_node_id`.
            This is used for purposes such as "find me all drugs (`start_node_id`) that have many proteins (`intermediate_node_id`) in common with this disease (`end_node_id`)."
            This can be used for downstream filtering to concentrate on relevant bioentities.
            

||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| start_node_id | intermediate_node_id | end_node_id | virtual_edge_type |
|_DSL arguments_| {'a node id (required)'} | {'a query node id (required)'} | {'a query node id (required)'} | {'any string label (required)'} |

## ARAX_filter_kg
### `filter_kg(action=remove_edges_by_property)`
||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_property | property_value | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge property'} | {'a value for the edge property'} | {'True', 'true', 'False', 'f', 't', 'F', 'T', 'false'} | {'a specific query node id to remove'} |

### `filter_kg(action=remove_edges_by_type)`
|||||
|-----|-----|-----|-----|
|_DSL parameters_| edge_type | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge type'} | {'True', 'true', 'False', 'f', 't', 'F', 'T', 'false'} | {'a specific query node id to remove'} |

### `filter_kg(action=remove_nodes_by_type)`
|||
|-----|-----|
|_DSL parameters_| node_type |
|_DSL arguments_| {'a node type'} |

### `filter_kg(action=remove_edges_by_attribute)`
|||||||
|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_attribute | direction | threshold | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge attribute name'} | {'above', 'below'} | {'a floating point number'} | {'True', 'true', 'False', 'f', 't', 'F', 'T', 'false'} | {'a specific query node id to remove'} |

