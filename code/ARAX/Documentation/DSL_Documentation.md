# Table of contents

- [Domain Specific Langauage (DSL) description](#domain-specific-langauage-dsl-description)
- [Full documentation of current DSL commands](#full-documentation-of-current-dsl-commands)
  - [ARAX_messenger](#arax_messenger)
    - [create_message()](#create_message)
    - [add_qnode()](#add_qnode)
    - [add_qedge()](#add_qedge)
  - [ARAX_expander](#arax_expander)
    - [expand(kp=ARAX/KG1)](#expandkparaxkg1)
    - [expand(kp=ARAX/KG2)](#expandkparaxkg2)
    - [expand(kp=BTE)](#expandkpbte)
    - [expand(kp=COHD)](#expandkpcohd)
    - [expand(kp=GeneticsKP)](#expandkpgeneticskp)
    - [expand(kp=MolePro)](#expandkpmolepro)
    - [expand(kp=NGD)](#expandkpngd)
  - [ARAX_overlay](#arax_overlay)
    - [overlay(action=fisher_exact_test)](#overlayactionfisher_exact_test)
    - [overlay(action=compute_ngd)](#overlayactioncompute_ngd)
    - [overlay(action=overlay_clinical_info)](#overlayactionoverlay_clinical_info)
    - [overlay(action=compute_jaccard)](#overlayactioncompute_jaccard)
    - [overlay(action=overlay_exposures_data)](#overlayactionoverlay_exposures_data)
    - [overlay(action=add_node_pmids)](#overlayactionadd_node_pmids)
    - [overlay(action=predict_drug_treats_disease)](#overlayactionpredict_drug_treats_disease)
  - [ARAX_filter_kg](#arax_filter_kg)
    - [filter_kg(action=remove_edges_by_type)](#filter_kgactionremove_edges_by_type)
    - [filter_kg(action=remove_edges_by_attribute)](#filter_kgactionremove_edges_by_attribute)
    - [filter_kg(action=remove_edges_by_property)](#filter_kgactionremove_edges_by_property)
    - [filter_kg(action=remove_edges_by_stats)](#filter_kgactionremove_edges_by_stats)
    - [filter_kg(action=remove_nodes_by_type)](#filter_kgactionremove_nodes_by_type)
    - [filter_kg(action=remove_nodes_by_property)](#filter_kgactionremove_nodes_by_property)
    - [filter_kg(action=remove_orphaned_nodes)](#filter_kgactionremove_orphaned_nodes)
  - [ARAX_filter_results](#arax_filter_results)
    - [filter_results(action=sort_by_edge_attribute)](#filter_resultsactionsort_by_edge_attribute)
    - [filter_results(action=sort_by_node_attribute)](#filter_resultsactionsort_by_node_attribute)
    - [filter_results(action=limit_number_of_results)](#filter_resultsactionlimit_number_of_results)
    - [filter_results(action=sort_by_edge_count)](#filter_resultsactionsort_by_edge_count)
    - [filter_results(action=sort_by_node_count)](#filter_resultsactionsort_by_node_count)
  - [ARAX_resultify](#arax_resultify)
    - [resultify()](#resultify)
  - [ARAX_ranker](#arax_ranker)
    - [rank_results()](#rank_results)

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
### create_message()
The `create_message` command creates a basic empty Message object with basic boilerplate metadata
                such as reasoner_id, schema_version, etc. filled in. This DSL command takes no arguments. This command is not explicitly
                necessary, as it is called implicitly when needed. e.g. If a DSL program begins with add_qnode(), the
                create_message() will be executed automatically if there is not yet a Message. If there is already Message in memory,
                then this command will destroy the previous one (in memory) and begin a new message.

#### parameters: 

### add_qnode()
The `add_qnode` method adds an additional QNode to the QueryGraph in the Message object. Currently
                when a curie or name is specified, this method will only return success if a matching node is found in the KG1/KG2 KGNodeIndex.

#### parameters: 

* ##### id

    - Any string that is unique among all QNode id fields, with recommended format n00, n01, n02, etc.
                        If no value is provided, autoincrementing values beginning for n00 are used.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

    - If not specified the default input will be . 

* ##### curie

    - Any compact URI (CURIE) (e.g. DOID:9281) (May also be a list like [UniProtKB:P12345,UniProtKB:Q54321])

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `DOID:9281` and `[UniProtKB:P12345,UniProtKB:Q54321]` are examples of valid inputs.

* ##### name

    - Any name of a bioentity that will be resolved into a CURIE if possible or result in an error if not (e.g. hypertension, insulin)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `hypertension` and `insulin` are examples of valid inputs.

* ##### type

    - Any valid Translator bioentity type (e.g. protein, chemical_substance, disease)

    - Acceptable input types: ARAXnode.

    - This is not a required parameter and may be omitted.

    - `protein`, `chemical_substance`, and `disease` are examples of valid inputs.

* ##### is_set

    - If set to true, this QNode represents a set of nodes that are all in common between the two other linked QNodes (assumed to be false if not specified)

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

### add_qedge()
The `add_qedge` command adds an additional QEdge to the QueryGraph in the Message object. Currently
                source_id and target_id QNodes must already be present in the QueryGraph. The specified type is not currently checked that it is a
                valid Translator/BioLink relationship type, but it should be.

#### parameters: 

* ##### id

    - Any string that is unique among all QEdge id fields, with recommended format e00, e01, e02, etc.
                        If no value is provided, autoincrementing values beginning for e00 are used.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `e01` are examples of valid inputs.

    - If not specified the default input will be . 

* ##### source_id

    - id of the source QNode already present in the QueryGraph (e.g. n00, n01)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `n00` and `n01` are examples of valid inputs.

* ##### target_id

    - id of the target QNode already present in the QueryGraph (e.g. n01, n02)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `n01` and `n02` are examples of valid inputs.

* ##### type

    - Any valid Translator/BioLink relationship type (e.g. physically_interacts_with, participates_in)

    - Acceptable input types: ARAXedge.

    - This is not a required parameter and may be omitted.

    - `protein`, `physically_interacts_with`, and `participates_in` are examples of valid inputs.

## ARAX_expander
### expand(kp=ARAX/KG1)
This command reaches out to the RTX KG1 Neo4j instance to find all bioentity subpaths that satisfy the query graph.

#### parameters: 

* ##### edge_id

    - A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `[e00, e01]` are examples of valid inputs.

* ##### node_id

    - A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `[n00, n01]` are examples of valid inputs.

* ##### continue_if_no_results

    - Whether to continue execution if no paths are found matching the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### enforce_directionality

    - Whether to obey (vs. ignore) edge directions in the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### use_synonyms

    - Whether to consider curie synonyms and merge synonymous nodes.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

### expand(kp=ARAX/KG2)
This command reaches out to the RTX KG2 knowledge graph to find all bioentity subpaths that satisfy the query graph. If use_synonyms=true, it uses the KG2canonicalized ('KG2c') Neo4j instance; otherwise, the regular KG2 Neo4j instance is used.

#### parameters: 

* ##### edge_id

    - A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `[e00, e01]` are examples of valid inputs.

* ##### node_id

    - A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `[n00, n01]` are examples of valid inputs.

* ##### continue_if_no_results

    - Whether to continue execution if no paths are found matching the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### enforce_directionality

    - Whether to obey (vs. ignore) edge directions in the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### use_synonyms

    - Whether to consider curie synonyms and merge synonymous nodes.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

### expand(kp=BTE)
This command uses BioThings Explorer (from the Service Provider) to find all bioentity subpaths that satisfy the query graph. Of note, all query nodes must have a type specified for BTE queries. In addition, bi-directional queries are only partially supported (the ARAX system knows how to ignore edge direction when deciding which query node for a query edge will be the 'input' qnode, but BTE itself returns only answers matching the input edge direction).

#### parameters: 

* ##### edge_id

    - A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `[e00, e01]` are examples of valid inputs.

* ##### node_id

    - A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `[n00, n01]` are examples of valid inputs.

* ##### continue_if_no_results

    - Whether to continue execution if no paths are found matching the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### enforce_directionality

    - Whether to obey (vs. ignore) edge directions in the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### use_synonyms

    - Whether to consider curie synonyms and merge synonymous nodes.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

### expand(kp=COHD)
This command uses the Clinical Data Provider (COHD) to find all bioentity subpaths that satisfy the query graph.

#### parameters: 

* ##### edge_id

    - A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `[e00, e01]` are examples of valid inputs.

* ##### node_id

    - A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `[n00, n01]` are examples of valid inputs.

* ##### continue_if_no_results

    - Whether to continue execution if no paths are found matching the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### use_synonyms

    - Whether to consider curie synonyms and merge synonymous nodes.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

* ##### COHD_method

    - Which measure from COHD should be considered.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `paired_concept_freq` and `chi_square` are examples of valid inputs.

    - `paired_concept_freq`, `observed_expected_ratio`, and `chi_square` are all possible valid inputs.

    - If not specified the default input will be paired_concept_freq. 

* ##### COHD_method_percentile

    - What percentile to use as a cut-off/threshold for the specified COHD method.

    - Acceptable input types: integer.

    - This is not a required parameter and may be omitted.

    - `95` and `80` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of 0 to a maximum value of 100.

    - If not specified the default input will be 99. 

### expand(kp=GeneticsKP)
This command reaches out to the Genetics Provider to find all bioentity subpaths that satisfy the query graph. It currently can answer questions involving the following node types: gene, protein, disease, phenotypic_feature, pathway. QNode types are required for GeneticsKP queries. Temporarily (while the integration is under development), it can only be used as the first hop in a query. Note that QEdge types are irrelevant for GeneticsKP queries, since GeneticsKP only outputs edges with a type of 'associated' (so Expand always uses that as the QEdge type behind the scenes).

#### parameters: 

* ##### edge_id

    - A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `[e00, e01]` are examples of valid inputs.

* ##### node_id

    - A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `[n00, n01]` are examples of valid inputs.

* ##### continue_if_no_results

    - Whether to continue execution if no paths are found matching the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### use_synonyms

    - Whether to consider curie synonyms and merge synonymous nodes.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

* ##### include_integrated_score

    - Whether to add genetics-quantile edges (in addition to MAGMA edges) from the Genetics KP.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

### expand(kp=MolePro)
This command reaches out to MolePro (the Molecular Provider) to find all bioentity subpaths that satisfy the query graph. It currently can answer questions involving the following node types: gene, protein, disease, chemical_substance. QNode types are required for MolePro queries. Generally you should not specify a QEdge type for MolePro queries (Expand uses 'correlated_with' by default behind the scenes, which is the primary edge type of interest for ARAX in MolePro).

#### parameters: 

* ##### edge_id

    - A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `[e00, e01]` are examples of valid inputs.

* ##### node_id

    - A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `[n00, n01]` are examples of valid inputs.

* ##### continue_if_no_results

    - Whether to continue execution if no paths are found matching the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### use_synonyms

    - Whether to consider curie synonyms and merge synonymous nodes.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

### expand(kp=NGD)
This command uses ARAX's in-house normalized google distance (NGD) database to expand a query graph; it returns edges between nodes with an NGD value below a certain threshold. This threshold is currently hardcoded as 0.5, though this will be made configurable/smarter in the future.

#### parameters: 

* ##### edge_id

    - A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `[e00, e01]` are examples of valid inputs.

* ##### node_id

    - A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `[n00, n01]` are examples of valid inputs.

* ##### continue_if_no_results

    - Whether to continue execution if no paths are found matching the query graph.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### use_synonyms

    - Whether to consider curie synonyms and merge synonymous nodes.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

## ARAX_overlay
### overlay(action=fisher_exact_test)

`fisher_exact_test` computes the Fisher's Exact Test p-values of the connection between a list of given nodes with specified query id (source_qnode_id eg. 'n01') to their adjacent nodes with specified query id (e.g. target_qnode_id 'n02') in the message knowledge graph. 
This information is then added as an edge attribute to a virtual edge which is then added to the query graph and knowledge graph.
It can also allow you to filter out the user-defined insignificance of connections based on a specified p-value cutoff or return the top n smallest p-value of connections and only add their corresponding virtual edges to the knowledge graph.

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
                    

#### parameters: 

* ##### source_qnode_id

    - A specific source query node id (required)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `n00` and `n01` are examples of valid inputs.

* ##### virtual_relation_label

    - An optional label to help identify the virtual edge in the relation field.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `N1`, `J2`, and `FET` are examples of valid inputs.

* ##### target_qnode_id

    - A specific target query node id (required)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `n00` and `n01` are examples of valid inputs.

* ##### rel_edge_id

    - A specific QEdge id of edges connected to both source nodes and target nodes in message KG (optional, otherwise all edges connected to both source nodes and target nodes in message KG are considered), eg. 'e01'

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `e00` and `e01` are examples of valid inputs.

* ##### top_n

    - An int indicating the top number (the smallest) of p-values to return (optional, otherwise all results returned)

    - Acceptable input types: int or None.

    - This is not a required parameter and may be omitted.

    - `all`, `5`, and `50` are examples of valid inputs.

    - If not specified the default input will be None. 

* ##### cutoff

    - A float indicating the p-value cutoff to return the results (optional, otherwise all results returned), eg. 0.05

    - Acceptable input types: float or None.

    - This is not a required parameter and may be omitted.

    - `all`, `0.05`, and `0.95` are examples of valid inputs.

    - If not specified the default input will be None. 

### overlay(action=compute_ngd)

`compute_ngd` computes a metric (called the normalized Google distance) based on edge soure/target node co-occurrence in abstracts of all PubMed articles.
This information is then included as an edge attribute with the name `normalized_google_distance`.
You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode id's. If the later, virtual edges are added with the type specified by `virtual_relation_label`.

Use cases include:

* focusing in on edges that are well represented in the literature
* focusing in on edges that are under-represented in the literature

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### default_value

    - The default value of the normalized Google distance (if its value cannot be determined)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `0` and `inf` are examples of valid inputs.

    - If not specified the default input will be inf. 

* ##### virtual_relation_label

    - An optional label to help identify the virtual edge in the relation field.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `N1` and `J2` are examples of valid inputs.

* ##### source_qnode_id

    - A specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

* ##### target_qnode_id

    - A specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

### overlay(action=overlay_clinical_info)

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
                    

**NOTE:** The parameters `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` are mutually exclusive and thus will cause an error when more than one is included.

#### parameters: 

* ##### paired_concept_frequency

    - Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

* ##### observed_expected_ratio

    - Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

* ##### chi_square

    - Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

* ##### virtual_relation_label

    - An optional label to help identify the virtual edge in the relation field.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `N1` and `J2` are examples of valid inputs.

* ##### source_qnode_id

    - A specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

* ##### target_qnode_id

    - A specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

### overlay(action=compute_jaccard)

`compute_jaccard` creates virtual edges and adds an edge attribute (with the property name `jaccard_index`) containing the following information:
The jaccard similarity measures how many `intermediate_node_id`'s are shared in common between each `start_node_id` and `target_node_id`.
This is used for purposes such as "find me all drugs (`start_node_id`) that have many proteins (`intermediate_node_id`) in common with this disease (`end_node_id`)."
This can be used for downstream filtering to concentrate on relevant bioentities.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### start_node_id

    - A curie id specifying the starting node

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `DOID:1872`, `CHEBI:7476`, and `UMLS:C1764836` are examples of valid inputs.

* ##### intermediate_node_id

    - A curie id specifying the intermediate node

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `DOID:1872`, `CHEBI:7476`, and `UMLS:C1764836` are examples of valid inputs.

* ##### end_node_id

    - A curie id specifying the ending node

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `DOID:1872`, `CHEBI:7476`, and `UMLS:C1764836` are examples of valid inputs.

* ##### virtual_relation_label

    - An optional label to help identify the virtual edge in the relation field.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `N1`, `J2`, and `FET` are examples of valid inputs.

### overlay(action=overlay_exposures_data)

`overlay_exposures_data` overlays edges with p-values obtained from the ICEES+ (Integrated Clinical and Environmental Exposures Service) knowledge provider.
This information is included in edge attributes with the name `icees_p-value`.
You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode IDs. If the latter, the data is added in 'virtual' edges with the type `has_icees_p-value_with`.

This can be applied to an arbitrary knowledge graph (i.e. not just those created/recognized by Expander Agent).
                    

#### parameters: 

* ##### virtual_relation_label

    - An optional label to help identify the virtual edge in the relation field.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `N1` and `J2` are examples of valid inputs.

* ##### source_qnode_id

    - A specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

* ##### target_qnode_id

    - A specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

### overlay(action=add_node_pmids)

`add_node_pmids` adds PubMed PMID's as node attributes to each node in the knowledge graph.
This information is obtained from mapping node identifiers to MeSH terms and obtaining which PubMed articles have this MeSH term
either labeling in the metadata or has the MeSH term occurring in the abstract of the article.

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### max_num

    - The maximum number of values to return. Enter 'all' to return everything

    - Acceptable input types: int or string.

    - This is not a required parameter and may be omitted.

    - `all`, `5`, and `50` are examples of valid inputs.

    - If not specified the default input will be 100. 

### overlay(action=predict_drug_treats_disease)

`predict_drug_treats_disease` utilizes a machine learning model (trained on KP ARAX/KG1) to assign a probability that a given drug/chemical_substance treats a disease/phenotypic feature.
For more information about how this model was trained and how it performs, please see [this publication](https://doi.org/10.1101/765305).
The drug-disease treatment prediction probability is included as an edge attribute (with the attribute name `probability_treats`).
You have the choice of applying this to all appropriate edges in the knowledge graph, or only between specified source/target qnode id's (make sure one is a chemical_substance, and the other is a disease or phenotypic_feature). 
If the later, virtual edges are added with the relation specified by `virtual_edge_type` and the type `probably_treats`.
Use cases include:

* Overlay drug the probability of any drug in your knowledge graph treating any disease via `overlay(action=predict_drug_treats_disease)`
* For specific drugs and diseases/phenotypes in your graph, add the probability that the drug treats them with something like `overlay(action=predict_drug_treats_disease, source_qnode_id=n02, target_qnode_id=n00, virtual_relation_label=P1)`
* Subsequently remove low-probability treating drugs with `overlay(action=predict_drug_treats_disease)` followed by `filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=.6, remove_connected_nodes=t, qnode_id=n02)`

This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### virtual_relation_label

    - An optional label to help identify the virtual edge in the relation field.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `N1` and `J2` are examples of valid inputs.

* ##### source_qnode_id

    - A specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

* ##### target_qnode_id

    - A specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n00` and `n01` are examples of valid inputs.

## ARAX_filter_kg
### filter_kg(action=remove_edges_by_type)

`remove_edges_by_type` removes edges from the knowledge graph (KG) based on a given edge type.
Use cases include:
             
* removing all edges that have `edge_type=contraindicated_for`. 
* if virtual edges have been introduced with `overlay()` DSL commands, this action can remove all of them.
* etc.
            
You have the option to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`
            
This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### edge_type

    - The name of the edge type to filter by.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `contraindicated_for`, `affects`, and `expressed_in` are examples of valid inputs.

* ##### remove_connected_nodes

    - Indicates whether or not to remove the nodes connected to the edge.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### qnode_id

    - If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n01` and `n02` are examples of valid inputs.

### filter_kg(action=remove_edges_by_attribute)

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
                    

#### parameters: 

* ##### edge_attribute

    - The name of the edge attribute to filter on.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `jaccard_index`, `observed_expected_ratio`, and `normalized_google_distance` are examples of valid inputs.

* ##### direction

    - Indictes whether to remove above or below the given threshold.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `above` and `below` are all possible valid inputs.

* ##### threshold

    - The threshold to filter with.

    - Acceptable input types: float.

    - This is a required parameter and must be included.

    - `5` and `0.45` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of -inf to a maximum value of inf.

* ##### remove_connected_nodes

    - Indicates whether or not to remove the nodes connected to the edge.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### qnode_id

    - If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n01` and `n02` are examples of valid inputs.

### filter_kg(action=remove_edges_by_property)

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
                    

#### parameters: 

* ##### edge_property

    - The name of the edge property to filter on.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `source_id`, `provided_by`, and `is_defined_by` are examples of valid inputs.

* ##### property_value

    - The edge property value to indicate which edges to remove.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `DOID:8398`, `Pharos`, and `ARAX/RTX` are examples of valid inputs.

* ##### remove_connected_nodes

    - Indicates whether or not to remove the nodes connected to the edge.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### qnode_id

    - If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n01` and `n02` are examples of valid inputs.

### filter_kg(action=remove_edges_by_stats)

`remove_edges_by_stats` removes edges from the knowledge graph (KG) based on a certain edge attribute using default heuristics.
Edge attributes are a list of additional attributes for an edge.
This action interacts particularly well with `overlay()` as `overlay()` frequently adds additional edge attributes.
there are two heuristic options: `n` for removing all but the 50 best results, `std`/`std_dev` for removing all but 
the best results more than 1 standard deviation from the mean, or `percentile` to remove all but the best 
5% of results. (if not supplied this defaults to `n`)
Use cases include:

* removing all edges with normalized google distance scores but the top 50 `edge_attribute=ngd, type=n` (i.e. remove edges that aren't represented well in the literature)
* removing all edges that Jaccard index less than 1 standard deviation above the mean. `edge_attribute=jaccard_index, type=std` (i.e. all edges that have less than 20% of intermediate nodes in common)
* etc. etc.
                
You have the option (this defaults to false) to either remove all connected nodes to such edges (via `remove_connected_nodes=t`), or
else, only remove a single source/target node based on a query node id (via `remove_connected_nodes=t, qnode_id=<a query node id.>`

You also have the option of specifying the direction to remove and location of the split by using the options 
* `direction` with options `above`,`below`
* `threshold` specified by a floating point number
* `top` which is boolean specified by `t`, `true`, `T`, `True` and `f`, `false`, `F`, `False`
e.g. to remove all the edges with jaccard_index values greater than 0.25 standard deviations below the mean you can run the following:
`filter_kg(action=remove_edges_by_stats, edge_attribute=jaccard_index, type=std, remove_connected_nodes=f, threshold=0.25, top=f, direction=above)`
                    

#### parameters: 

* ##### edge_attribute

    - The name of the edge attribute to filter on.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `jaccard_index`, `observed_expected_ratio`, and `normalized_google_distance` are examples of valid inputs.

* ##### type

    - The statistic to use for filtering.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n`, `std`, `std_dev`, `percentile`, and `p` are all possible valid inputs.

    - If not specified the default input will be n. 

* ##### direction

    - Indictes whether to remove above or below the given threshold.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `above` and `below` are all possible valid inputs.

    - If not specified the default input will be a value dictated by the `edge_attribute` parameter. If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `direction` defaults to above. If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `direction` defaults to below.. 

* ##### threshold

    - The threshold to filter with.

    - Acceptable input types: float.

    - This is not a required parameter and may be omitted.

    - `5` and `0.45` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of 0 to a maximum value of inf (or 100 if type=percentile or p).

    - If not specified the default input will be a value dictated by the `type` parameter. If `type` is 'n' then `threshold` will default to 50. If `type` is 'std_dev' or 'std' then `threshold` will default to 1.If `type` is 'percentile' or 'p' then `threshold` will default to 95 unless `edge_attribute` is also 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `threshold` will default to 5.. 

* ##### top

    - Indicate whether or not the threshold should be placed in top of the list. E.g. top set as True with type set as std_dev will set the cutoff for filtering as the mean + threshold * std_dev while setting top to False will set the cutoff as the mean - std_dev * threshold.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be a value dictated by the `edge_attribute` parameter. If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `top` defaults to False. If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `top` defaults to True.. 

* ##### remove_connected_nodes

    - Indicates whether or not to remove the nodes connected to the edge.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be false. 

* ##### qnode_id

    - If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `n01` and `n02` are examples of valid inputs.

### filter_kg(action=remove_nodes_by_type)

`remove_node_by_type` removes nodes from the knowledge graph (KG) based on a given node type.
Use cases include:
* removing all nodes that have `node_type=protein`.
* removing all nodes that have `node_type=chemical_substance`.
* etc.
This can be applied to an arbitrary knowledge graph as possible node types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### node_type

    - The name of the node type to filter by.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `chemical_substance` and `disease` are examples of valid inputs.

### filter_kg(action=remove_nodes_by_property)

`remove_nodes_by_property` removes nodes from the knowledge graph (KG) based on a given node property.
Use cases include:
                
* removing all nodes that were provided by a certain knowledge provider (KP) via `node_property=provided, property_value=Pharos` to remove all nodes provided by the KP Pharos.
* removing all nodes provided by another ARA via `node_property=is_defined_by, property_value=ARAX/RTX`
* etc. etc.
                
This can be applied to an arbitrary knowledge graph as possible node properties are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### node_property

    - The name of the node property to filter on.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `provided_by` and `is_defined_by` are examples of valid inputs.

* ##### property_value

    - The node property vaue to indicate which nodes to remove.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `Pharos` and `ARAX/RTX` are examples of valid inputs.

### filter_kg(action=remove_orphaned_nodes)

`remove_orphaned_nodes` removes nodes from the knowledge graph (KG) that are not connected via any edges.
Specifying a `node_type` will restrict this to only remove orphaned nodes of a certain type.
This can be applied to an arbitrary knowledge graph as possible node types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### node_type

    - The name of the node type to filter by. If no value provided node type will not be considered.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `chemical_substance` and `disease` are examples of valid inputs.

## ARAX_filter_results
### filter_results(action=sort_by_edge_attribute)

`sort_by_edge_attribute` sorts the results by the edges based on a a certain edge attribute.
Edge attributes are a list of additional attributes for an edge.
Use cases include:

* sorting the results by the value of the jaccard index and take the top ten `filter_results(action=sort_by_edge_attribute, edge_attribute=jaccard_index, direction=d, max_results=10)`
* etc. etc.
                
You have the option to specify the edge type (e.g. via `edge_relation=<an edge relation>`)
Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`
                    

#### parameters: 

* ##### edge_attribute

    - The name of the attribute to filter by.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `jaccard_index`, `observed_expected_ratio`, and `normalized_google_distance` are examples of valid inputs.

* ##### edge_relation

    - The name of unique identifier to only filter on edges with matching relation field. (stored in the relation neo4j edge property) If not provided the edge relation will not be considered when filtering.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `N1` and `C1` are examples of valid inputs.

* ##### direction

    - The direction in which to order results. (ascending or descending)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `descending`, `d`, `ascending`, and `a` are examples of valid inputs.

* ##### max_results

    - The maximum number of results to return. If not provided all results will be returned.

    - Acceptable input types: int.

    - This is not a required parameter and may be omitted.

    - `5`, `10`, and `50` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of 0 to a maximum value of inf.

* ##### prune_kg

    - This indicates if the Knowledge Graph (KG) should be pruned so that any nodes or edges not appearing in the results are removed from the KG.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be true. 

### filter_results(action=sort_by_node_attribute)

`sort_by_node_attribute` sorts the results by the nodes based on a a certain node attribute.
Node attributes are a list of additional attributes for an node.
Use cases include:

* Sorting the results by the number of pubmed ids and returning the top 20. `"filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=d, max_results=20)"`
* etc. etc.
                
You have the option to specify the node type. (e.g. via `node_type=<an node type>`)
Also, you have the option of limiting the number of results returned. (e.g. via `max_results=<a non-negative integer>`
                    

#### parameters: 

* ##### node_attribute

    - The name of the attribute to filter by.

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `pubmed_ids` are examples of valid inputs.

* ##### node_type

    - The name of the node type to only filter on nodes of the matching type. If not provided the node type will not be considered when filtering.

    - Acceptable input types: string.

    - This is not a required parameter and may be omitted.

    - `chemical_substance` and `disease` are examples of valid inputs.

* ##### direction

    - The direction in which to order results. (ascending or descending)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `descending`, `d`, `ascending`, and `a` are examples of valid inputs.

* ##### max_results

    - The maximum number of results to return. If not provided all results will be returned.

    - Acceptable input types: int.

    - This is not a required parameter and may be omitted.

    - `5`, `10`, and `50` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of 0 to a maximum value of inf.

* ##### prune_kg

    - This indicates if the Knowledge Graph (KG) should be pruned so that any nodes or edges not appearing in the results are removed from the KG.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be true. 

### filter_results(action=limit_number_of_results)

`limit_number_of_results` removes excess results over the specified maximum.

Use cases include:

* limiting the number of results to 100 `filter_results(action=limit_number_of_results, max_results=100)`
* etc. etc.
                    

#### parameters: 

* ##### max_results

    - The maximum number of results to return. If not provided all results will be returned.

    - Acceptable input types: int.

    - This is a required parameter and must be included.

    - `5`, `10`, and `50` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of 0 to a maximum value of inf.

* ##### prune_kg

    - This indicates if the Knowledge Graph (KG) should be pruned so that any nodes or edges not appearing in the results are removed from the KG.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be true. 

### filter_results(action=sort_by_edge_count)

`sort_by_edge_count` sorts the results by the number of edges in the results.
Use cases include:

* return the results with the 10 fewest edges. `filter_results(action=sort_by_edge_count, direction=ascending, max_results=10)`
* etc. etc.
                
You have the option to specify the direction. (e.g. `direction=descending`)
Also, you have the option of limiting the number of results returned. (e.g. via `max_results=<a non-negative integer>`
                    

#### parameters: 

* ##### direction

    - The direction in which to order results. (ascending or descending)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `descending`, `d`, `ascending`, and `a` are examples of valid inputs.

* ##### max_results

    - The maximum number of results to return. If not provided all results will be returned.

    - Acceptable input types: int.

    - This is not a required parameter and may be omitted.

    - `5`, `10`, and `50` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of 0 to a maximum value of inf.

* ##### prune_kg

    - This indicates if the Knowledge Graph (KG) should be pruned so that any nodes or edges not appearing in the results are removed from the KG.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be true. 

### filter_results(action=sort_by_node_count)

`sort_by_node_count` sorts the results by the number of nodes in the results.
Use cases include:

* return the results with the 10 most nodes. `filter_results(action=sort_by_node_count, direction=descending, max_results=10)`
* etc. etc.
                
You have the option to specify the direction. (e.g. `direction=descending`)
Also, you have the option of limiting the number of results returned. (e.g. via `max_results=<a non-negative integer>`
                    

#### parameters: 

* ##### direction

    - The direction in which to order results. (ascending or descending)

    - Acceptable input types: string.

    - This is a required parameter and must be included.

    - `descending`, `d`, `ascending`, and `a` are examples of valid inputs.

* ##### max_results

    - The maximum number of results to return. If not provided all results will be returned.

    - Acceptable input types: int.

    - This is not a required parameter and may be omitted.

    - `5`, `10`, and `50` are examples of valid inputs.

    - The values for this parameter can range from a minimum value of 0 to a maximum value of inf.

* ##### prune_kg

    - This indicates if the Knowledge Graph (KG) should be pruned so that any nodes or edges not appearing in the results are removed from the KG.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true`, `false`, `True`, `False`, `t`, `f`, `T`, and `F` are all possible valid inputs.

    - If not specified the default input will be true. 

## ARAX_resultify
### resultify()
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

#### parameters: 

* ##### ignore_edge_direction

    - Whether to ignore (vs. obey) edge directions in the query graph when identifying paths that fulfill it.

    - Acceptable input types: boolean.

    - This is not a required parameter and may be omitted.

    - `true` and `false` are examples of valid inputs.

    - `true` and `false` are all possible valid inputs.

    - If not specified the default input will be true. 

## ARAX_ranker
### rank_results()

`rank_results` iterates through all edges in the results list aggrigating and 
normalizing the scores stored within the `edge_attributes` property. After combining these scores into 
one score the ranker then scores each result through a combination of 
[max flow](https://en.wikipedia.org/wiki/Maximum_flow_problem), 
[longest path](https://en.wikipedia.org/wiki/Longest_path_problem), 
and [frobenius norm](https://en.wikipedia.org/wiki/Matrix_norm#Frobenius_norm).
        


