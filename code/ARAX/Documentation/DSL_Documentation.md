# Table of contents

- [Domain Specific Langauage (DSL) description](#domain-specific-langauage-dsl-description)
- [Full documentation of current DSL commands](#full-documentation-of-current-dsl-commands)
  - [ARAX_messenger](#arax_messenger)
    - [`create_message()`](#create_message)
    - [`add_qnode()`](#add_qnode)
    - [`add_qedge()`](#add_qedge)
  - [ARAX_expander](#arax_expander)
    - [`expand()`](#expand)
  - [ARAX_overlay](#arax_overlay)
    - [`overlay(action=compute_ngd)`](#overlayactioncompute_ngd)
    - [`overlay(action=overlay_clinical_info)`](#overlayactionoverlay_clinical_info)
    - [`overlay(action=fisher_exact_test)`](#overlayactionfisher_exact_test)
    - [`overlay(action=add_node_pmids)`](#overlayactionadd_node_pmids)
    - [`overlay(action=predict_drug_treats_disease)`](#overlayactionpredict_drug_treats_disease)
    - [`overlay(action=compute_jaccard)`](#overlayactioncompute_jaccard)
  - [ARAX_filter_kg](#arax_filter_kg)
    - [`filter_kg(action=remove_edges_by_property)`](#filter_kgactionremove_edges_by_property)
    - [`filter_kg(action=remove_edges_by_stats)`](#filter_kgactionremove_edges_by_stats)
    - [`filter_kg(action=remove_nodes_by_property)`](#filter_kgactionremove_nodes_by_property)
    - [`filter_kg(action=remove_nodes_by_type)`](#filter_kgactionremove_nodes_by_type)
    - [`filter_kg(action=remove_orphaned_nodes)`](#filter_kgactionremove_orphaned_nodes)
    - [`filter_kg(action=remove_edges_by_attribute)`](#filter_kgactionremove_edges_by_attribute)
    - [`filter_kg(action=remove_edges_by_type)`](#filter_kgactionremove_edges_by_type)
  - [ARAX_filter_results](#arax_filter_results)
    - [`filter_results(action=limit_number_of_results)`](#filter_resultsactionlimit_number_of_results)
    - [`filter_results(action=sort_by_edge_attribute)`](#filter_resultsactionsort_by_edge_attribute)
    - [`filter_results(action=sort_by_edge_count)`](#filter_resultsactionsort_by_edge_count)
    - [`filter_results(action=sort_by_node_count)`](#filter_resultsactionsort_by_node_count)
    - [`filter_results(action=sort_by_node_attribute)`](#filter_resultsactionsort_by_node_attribute)
  - [ARAX_resultify](#arax_resultify)
    - [`resultify()`](#resultify)

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
## ARAX_messenger
### `create_message()`
The `create_message` method creates a basic empty Message object with basic boilerplate metadata
            such as reasoner_id, schema_version, etc. filled in. This DSL command takes no arguments


### `add_qnode()`
The `add_qnode` method adds an additional QNode to the QueryGraph in the Message object. Currently
                when a curie or name is specified, this method will only return success if a matching node is found in the KG1/KG2 KGNodeIndex.

|||||||
|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| id | curie | name | type | is_set |
|_DSL arguments_| {'Any string that is unique among all QNode id fields, with recommended format n00, n01, n02, etc.'} | {'Any compact URI (CURIE) (e.g. DOID:9281) (May also be a list like [UniProtKB:P12345,UniProtKB:Q54321])'} | {'Any name of a bioentity that will be resolved into a CURIE if possible or result in an error if not (e.g. hypertension, insulin)'} | {'Any valid Translator bioentity type (e.g. protein, chemical_substance, disease)'} | {'If set to true, this QNode represents a set of nodes that are all in common between the two other linked QNodes'} |

### `add_qedge()`
The `add_qedge` method adds an additional QEdge to the QueryGraph in the Message object. Currently
                source_id and target_id QNodes must already be present in the QueryGraph. The specified type is not currently checked that it is a
                valid Translator/BioLink relationship type, but it should be.

||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| id | source_id | target_id | type |
|_DSL arguments_| {'Any string that is unique among all QEdge id fields, with recommended format e00, e01, e02, etc.'} | {'id of the source QNode already present in the QueryGraph (e.g. n01, n02)'} | {'id of the target QNode already present in the QueryGraph (e.g. n01, n02)'} | {'Any valid Translator/BioLink relationship type (e.g. physically_interacts_with, participates_in)'} |

## ARAX_expander
### `expand()`

        `expand` effectively takes a query graph (QG) and reaches out to various knowledge providers (KP's) to find 
        all bioentity subgraphs that satisfy that QG and augments the knowledge graph (KG) with them. As currently 
        implemented, `expand` can utilize the ARA Expander team KG1 and KG2 Neo4j instances as well as BioThings 
        Explorer to fulfill QG's, with functionality built in to reach out to other KP's as they are rolled out.
        

|||||||||
|-----|-----|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_id | node_id | kp | enforce_directionality | use_synonyms | synonym_handling | continue_if_no_results |
|_DSL arguments_| {'a query graph edge ID or list of such IDs to expand (optional, default is to expand entire query graph)'} | {'a query graph node ID to expand (optional, default is to expand entire query graph)'} | {'the knowledge provider to use - current options are `ARAX/KG1`, `ARAX/KG2`, or `BTE` (optional, default is `ARAX/KG1`)'} | {'whether to obey (vs. ignore) edge directions in query graph - options are `true` or `false` (optional, default is `false`)'} | {'whether to consider synonym curies for query nodes with a curie specified - options are `true` or `false` (optional, default is `true`)'} | {'how to handle synonyms in the answer - options are `map_back` (default; map edges using a synonym back to the original curie) or `add_all` (add synonym nodes as they are - no mapping/merging)'} | {'whether to continue execution if no paths are found matching the query graph - options are `true` or `false` (optional, default is `false`)'} |

## ARAX_overlay
### `overlay(action=compute_ngd)`

`compute_ngd` computes a metric (called the normalized Google distance) based on edge soure/target node co-occurrence in abstracts of all PubMed articles.
This information is then included as an edge attribute with the name `normalized_google_distance`.
You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode id's. If the later, virtual edges are added with the type specified by `virtual_relation_label`.

Use cases include:

* focusing in on edges that are well represented in the literature
* focusing in on edges that are under-represented in the literature

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| default_value | virtual_relation_label | source_qnode_id | target_qnode_id |
|_DSL arguments_| {'0', 'inf'} | {'any string label identifying the virtual edge label (optional, otherwise applied to all existing edges in the KG)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

### `overlay(action=overlay_clinical_info)`

`overlay_clinical_info` overlay edges with information obtained from the knowledge provider (KP) Columbia Open Health Data (COHD).
This KP has a number of different functionalities, such as `paired_concept_frequency`, `observed_expected_ratio`, etc. which are mutually exclusive DSL parameters.
All information is derived from a 5 year hierarchical dataset: Counts for each concept include patients from descendant concepts. 
This includes clinical data from 2013-2017 and includes 1,731,858 different patients.
This information is then included as an edge attribute.
You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode id's. If the later, virtual edges are added with the relation specified by `virtual_relation_label`.
These virtual edges have the following types:

* `paired_concept_frequency` has the virtual edge type `has_paired_concept_frequency_with`
* `observed_expected_ratio` has the virtual edge type `has_observed_expected_ratio_with`
* `chi_square` has the virtual edge type `has_chi_square_with`

Note that this DSL command has quite a bit of functionality, so a brief description of the DSL parameters is given here:

* `paired_concept_frequency`: If set to `true`, retrieves observed clinical frequencies of a pair of concepts indicated by edge source and target nodes and adds these values as edge attributes.
* `observed_expected_ratio`: If set to `true`, returns the natural logarithm of the ratio between the observed count and expected count of edge source and target nodes. Expected count is calculated from the single concept frequencies and assuming independence between the concepts. This information is added as an edge attribute.
* `chi_square`: If set to `true`, returns the chi-square statistic and p-value between pairs of concepts indicated by edge source/target nodes and adds these values as edge attributes. The expected frequencies for the chi-square analysis are calculated based on the single concept frequencies and assuming independence between concepts. P-value is calculated with 1 DOF.
* `virtual_edge_type`: Overlays the requested information on virtual edges (ones that don't exist in the query graph).

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


||||||||
|-----|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| paired_concept_frequency | observed_expected_ratio | chi_square | virtual_relation_label | source_qnode_id | target_qnode_id |
|_DSL arguments_| {'true', 'false'} | {'true', 'false'} | {'true', 'false'} | {'any string label used to identify the virtual edge (optional, otherwise information is added as an attribute to all existing edges in the KG)'} | {'a specific source query node id (optional, otherwise applied to all edges)'} | {'a specific target query node id (optional, otherwise applied to all edges)'} |

### `overlay(action=fisher_exact_test)`

`fisher_exact_test` computes the the Fisher's Exact Test p-values of the connection between a list of given nodes with specified query id (source_qnode_id eg. 'n01') to their adjacent nodes with specified query id (e.g. target_qnode_id 'n02') in the message knowledge graph. 
This information is then added as an edge attribute to a virtual edge which is then added to the query graph and knowledge graph.
It can also allow you filter out the user-defined insignificance of connections based on a specified p-value cutoff or return the top n smallest p-value of connections and only add their corresponding virtual edges to the knowledge graph.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).

Use cases include:

* Given an input list (or a single) bioentities with specified query id in message KG, find connected bioentities  that are most "representative" of the input list of bioentities
* Find biological pathways that are enriched for an input list of proteins (specified with a query id)
* Make long query graph expansions in a targeted fashion to reduce the combinatorial explosion experienced with long query graphs 

This p-value is calculated from fisher's exact test based on the contingency table with following format:

|||||
|-----|-----|-----|-----|
|                                  | in query node list | not in query node list | row total |
| connect to certain adjacent node |         a          |           b            |   a+b     |
| not connect to adjacent node     |         c          |           d            |   c+d     |
|         column total             |        a+c         |          b+d           |  a+b+c+d  |
    
The p-value is calculated by applying fisher_exact method of scipy.stats module in scipy package to the contingency table.
The code is as follows:

```
 _, pvalue = stats.fisher_exact([[a, b], [c, d]])
```



||||||||
|-----|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| source_qnode_id | virtual_relation_label | target_qnode_id | rel_edge_id | top_n | cutoff |
|_DSL arguments_| {"a specific QNode id of source nodes in message KG (required), eg. 'n00'"} | {"any string to label the relation and query edge id of virtual edge with fisher's exact test p-value (required) eg. 'FET'"} | {"a specific QNode id of target nodes in message KG. This will specify which node in KG to consider for calculating the Fisher Exact Test (required), eg. 'n01'"} | {"a specific QEdge id of edges connected to both source nodes and target nodes in message KG (optional, otherwise all edges connected to both source nodes and target nodes in message KG are considered), eg. 'e01'"} | {'an int indicating the top number (the smallest) of p-values to return (optional,otherwise all results returned), eg. 10'} | {'a float indicating the p-value cutoff to return the results (optional, otherwise all results returned), eg. 0.05'} |

### `overlay(action=add_node_pmids)`

`add_node_pmids` adds PubMed PMID's as node attributes to each node in the knowledge graph.
This information is obtained from mapping node identifiers to MeSH terms and obtaining which PubMed articles have this MeSH term
either labeling in the metadata or has the MeSH term occurring in the abstract of the article.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


|||
|-----|-----|
|_DSL parameters_| max_num |
|_DSL arguments_| {'any integer', 'all'} |

### `overlay(action=predict_drug_treats_disease)`

`predict_drug_treats_disease` utilizes a machine learning model (trained on KP ARAX/KG1) to assign a probability that a given drug/chemical_substanct treats a disease/phenotypic feature.
For more information about how this model was trained and how it performs, please see [this publication](https://doi.org/10.1101/765305).
The drug-disease treatment prediction probability is included as an edge attribute (with the attribute name `probability_treats`).
You have the choice of applying this to all appropriate edges in the knowledge graph, or only between specified source/target qnode id's (make sure one is a chemical_substance, and the other is a disease or phenotypic_feature). 
If the later, virtual edges are added with the relation specified by `virtual_edge_type` and the type `probably_treats`.
Use cases include:

* Overlay drug the probability of any drug in your knowledge graph treating any disease via `overlay(action=predict_drug_treats_disease)`
* For specific drugs and diseases/phenotypes in your graph, add the probability that the drug treats them with something like `overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)`
* Subsequently remove low-probability treating drugs with `overlay(action=predict_drug_treats_disease)` followed by `filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=.6, remove_connected_nodes=t, qnode_id=n02)`

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


|||||
|-----|-----|-----|-----|
|_DSL parameters_| virtual_relation_label | source_qnode_id | target_qnode_id |
|_DSL arguments_| {'optional: any string label that identifies the virtual edges added (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'} | {'optional: a specific source query node id corresponding to a disease query node (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'} | {'optional: a specific target query node id corresponding to a disease or phenotypic_feature query node (otherwise applied to all drug->disease and drug->phenotypic_feature edges)'} |

### `overlay(action=compute_jaccard)`

`compute_jaccard` creates virtual edges and adds an edge attribute (with the property name `jaccard_index`) containing the following information:
The jaccard similarity measures how many `intermediate_node_id`'s are shared in common between each `start_node_id` and `target_node_id`.
This is used for purposes such as "find me all drugs (`start_node_id`) that have many proteins (`intermediate_node_id`) in common with this disease (`end_node_id`)."
This can be used for downstream filtering to concentrate on relevant bioentities.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| start_node_id | intermediate_node_id | end_node_id | virtual_relation_label |
|_DSL arguments_| {'a node id (required)'} | {'a query node id (required)'} | {'a query node id (required)'} | {'any string label (required) that will be used to identify the virtual edge added'} |

## ARAX_filter_kg
### `filter_kg(action=remove_edges_by_property)`

`remove_edges_by_property` removes edges from the knowledge graph (KG) based on a given edge property.
Use cases include:
                
* removing all edges that were provided by a certain knowledge provider (KP) via `edge_property=provided, property_value=Pharos` to remove all edges provided by the KP Pharos.
* removing all edges that connect to a certain node via `edge_property=source_id, property_value=DOID:8398`
* removing all edges with a certain relation via `edge_property=relation, property_value=upregulates`
* removing all edges provided by another ARA via `edge_property=is_defined_by, property_value=ARAX/RTX`
* etc. etc.
                
You have the option to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`
                
This can be applied to an arbitrary knowledge graph as possible edge properties are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_property | property_value | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge property'} | {'a value for the edge property'} | {'f', 'T', 'True', 'true', 'F', 'false', 't', 'False'} | {'a specific query node id to remove'} |

### `filter_kg(action=remove_edges_by_stats)`

`remove_edges_by_stats` removes edges from the knowledge graph (KG) based on a certain edge attribute using default heuristics.
Edge attributes are a list of additional attributes for an edge.
This action interacts particularly well with `overlay()` as `overlay()` frequently adds additional edge attributes.
there are two heuristic options: `n` for removing all but the 50 best results, `std`/`std_dev` for removing all but 
the best results more than 1 standard deviation from the mean, or `percentile` to remove all but the best 
5% of results. (if not supplied this defaults to `n`)
Use cases include:

* removing all edges with normalized google distance scores but the top 50 `edge_attribute=ngd, type=n` (i.e. remove edges that aren't represented well in the literature)
* removing all edges that Jaccard index leass than 1 standard deviation above the mean. `edge_attribute=jaccard_index, type=std` (i.e. all edges that have less than 20% of intermediate nodes in common)
* etc. etc.
                
You have the option (this defaults to false) to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`

You also have the option of specifying the direction to remove and location of the split by using the options 
* `direction` with options `above`,`below`
* `threshold` specified by a floating point number
* `top` which is boolean specified by `t`, `true`, `T`, `True` and `f`, `false`, `F`, `False`
e.g. to remove all the edges with jaccard_index values greater than 0.25 standard deviations below the mean you can run the following:
`filter_kg(action=remove_edges_by_stats, edge_attribute=jaccard_index, type=std, remove_connected_nodes=f, threshold=0.25, top=f, direction=above)`


|||||||||
|-----|-----|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_attribute | type | direction | threshold | top | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge attribute name'} | {'std', 'top_n', 'n', 'top_std'} | {'above', 'below'} | {'a floating point number'} | {'f', 'T', 'True', 'true', 'F', 'false', 't', 'False'} | {'f', 'T', 'True', 'true', 'F', 'false', 't', 'False'} | {'a specific query node id to remove'} |

### `filter_kg(action=remove_nodes_by_property)`

`remove_nodes_by_property` removes nodes from the knowledge graph (KG) based on a given node property.
Use cases include:
                
* removing all nodes that were provided by a certain knowledge provider (KP) via `node_property=provided, property_value=Pharos` to remove all nodes provided by the KP Pharos.
* removing all nodes provided by another ARA via `node_property=is_defined_by, property_value=ARAX/RTX`
* etc. etc.
                
This can be applied to an arbitrary knowledge graph as possible node properties are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


||||
|-----|-----|-----|
|_DSL parameters_| node_property | property_value |
|_DSL arguments_| {'an node property'} | {'a value for the node property'} |

### `filter_kg(action=remove_nodes_by_type)`

`remove_node_by_type` removes nodes from the knowledge graph (KG) based on a given node type.
Use cases include:
* removing all nodes that have `node_type=protein`.
* removing all nodes that have `node_type=chemical_substance`.
* etc.
This can be applied to an arbitrary knowledge graph as possible node types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


|||
|-----|-----|
|_DSL parameters_| node_type |
|_DSL arguments_| {'a node type'} |

### `filter_kg(action=remove_orphaned_nodes)`

`remove_orphaned_nodes` removes nodes from the knowledge graph (KG) that are not connected via any edges.
Specifying a `node_type` will restrict this to only remove orphaned nodes of a certain type
This can be applied to an arbitrary knowledge graph as possible node types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


|||
|-----|-----|
|_DSL parameters_| node_type |
|_DSL arguments_| {'a node type (optional)'} |

### `filter_kg(action=remove_edges_by_attribute)`

`remove_edges_by_attribute` removes edges from the knowledge graph (KG) based on a a certain edge attribute.
Edge attributes are a list of additional attributes for an edge.
This action interacts particularly well with `overlay()` as `overlay()` frequently adds additional edge attributes.
Use cases include:

* removing all edges that have a normalized google distance above/below a certain value `edge_attribute=ngd, direction=above, threshold=0.85` (i.e. remove edges that aren't represented well in the literature)
* removing all edges that Jaccard index above/below a certain value `edge_attribute=jaccard_index, direction=below, threshold=0.2` (i.e. all edges that have less than 20% of intermediate nodes in common)
* removing all edges with clinical information satisfying some condition `edge_attribute=chi_square, direction=above, threshold=.005` (i.e. all edges that have a chi square p-value above .005)
* etc. etc.
                
You have the option to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`
                
This can be applied to an arbitrary knowledge graph as possible edge attributes are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


|||||||
|-----|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_attribute | direction | threshold | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge attribute name'} | {'above', 'below'} | {'a floating point number'} | {'f', 'T', 'True', 'true', 'F', 'false', 't', 'False'} | {'a specific query node id to remove'} |

### `filter_kg(action=remove_edges_by_type)`

`remove_edges_by_type` removes edges from the knowledge graph (KG) based on a given edge type.
Use cases include:
             
* removing all edges that have `edge_type=contraindicated_for`. 
* if virtual edges have been introduced with `overlay()` DSL commands, this action can remove all of them.
* etc.
            
You have the option to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`
            
This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).


|||||
|-----|-----|-----|-----|
|_DSL parameters_| edge_type | remove_connected_nodes | qnode_id |
|_DSL arguments_| {'an edge type'} | {'f', 'T', 'True', 'true', 'F', 'false', 't', 'False'} | {'a specific query node id to remove'} |

## ARAX_filter_results
### `filter_results(action=limit_number_of_results)`

`limit_number_of_results` removes excess results over the specified maximum.

Use cases include:

* limiting the number of results to 100 `filter_results(action=limit_number_of_results, max_results=100)`
* etc. etc.


|||
|-----|-----|
|_DSL parameters_| max_results |
|_DSL arguments_| {'a non-negative integer'} |

### `filter_results(action=sort_by_edge_attribute)`

`sort_by_edge_attribute` sorts the results by the edges based on a a certain edge attribute.
Edge attributes are a list of additional attributes for an edge.
Use cases include:

* sorting the results by the value of the jaccard index and take the top ten `filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=d, max_results=10)`
* etc. etc.
                
You have the option to specify the edge type (e.g. via `edge_relation=<an edge relation>`)
Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`


||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| edge_attribute | edge_relation | direction | max_results |
|_DSL arguments_| {'an edge attribute'} | {'an edge relation'} | {'ascending', 'descending', 'a', 'd'} | {'the maximum number of results to return'} |

### `filter_results(action=sort_by_edge_count)`

`sort_by_edge_count` sorts the results by the number of edges in the results.
Use cases include:

* return the results with the 10 fewest edges. `filter_results(action=sort_by_edge_count, direction=ascending, max_results=10)`
* etc. etc.
                
You have the option to specify the direction (e.g. `direction=descending`)
Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`


||||
|-----|-----|-----|
|_DSL parameters_| direction | max_results |
|_DSL arguments_| {'ascending', 'descending', 'a', 'd'} | {'the maximum number of results to return'} |

### `filter_results(action=sort_by_node_count)`

`sort_by_node_count` sorts the results by the number of nodes in the results.
Use cases include:

* return the results with the 10 most nodes. `filter_results(action=sort_by_node_count, direction=descending, max_results=10)`
* etc. etc.
                
You have the option to specify the direction (e.g. `direction=descending`)
Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`


||||
|-----|-----|-----|
|_DSL parameters_| direction | max_results |
|_DSL arguments_| {'ascending', 'descending', 'a', 'd'} | {'the maximum number of results to return'} |

### `filter_results(action=sort_by_node_attribute)`

`sort_by_node_attribute` sorts the results by the nodes based on a a certain node attribute.
node attributes are a list of additional attributes for an node.
Use cases include:

* sorting the rsults by the number of pubmed ids returning the top 20. `"filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=d, max_results=20)"`
* etc. etc.
                
You have the option to specify the node type (e.g. via `node_type=<an node type>`)
Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`


||||||
|-----|-----|-----|-----|-----|
|_DSL parameters_| node_attribute | node_type | direction | max_results |
|_DSL arguments_| {'an node attribute'} | {'an node type'} | {'ascending', 'descending', 'a', 'd'} | {'the maximum number of results to return'} |

## ARAX_resultify
### `resultify()`
 Creates a list of results from the input query graph (QG) based on the the
information contained in the message knowledge graph (KG). Every subgraph
through the KG that satisfies the GQ is returned. Such use cases include:
- `resultify()` Returns all subgraphs in the knowledge graph that satisfy the
  query graph
- `resultiy(ignore_edge_direction=false)` This mode checks edge directions in
the QG to ensure that matching an edge in the KG to an edge in the QG is only
allowed if the two edges point in the same direction. The default is to not
check edge direction. For example, you may want to include results that include
relationships like `(protein)-[involved_in]->(pathway)` even though the
underlying KG only contains directional edges of the form
`(protein)<-[involved_in]-(pathway)`.  Note that this command will successfully
execute given an arbitrary query graph and knowledge graph provided by the
automated reasoning system, not just ones generated by Team ARA Expander.

|||
|-----|-----|
|_DSL parameters_| ignore_edge_direction |
|_DSL arguments_| {'`true` or `false`. Optional; default is `true`.'} |

