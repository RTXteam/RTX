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
    - [expand(kp=NGD)](#expandkpngd)
  - [ARAX_overlay](#arax_overlay)
    - [overlay(action=overlay_exposures_data)](#overlayactionoverlay_exposures_data)
    - [overlay(action=fisher_exact_test)](#overlayactionfisher_exact_test)
    - [overlay(action=overlay_clinical_info)](#overlayactionoverlay_clinical_info)
    - [overlay(action=add_node_pmids)](#overlayactionadd_node_pmids)
    - [overlay(action=compute_ngd)](#overlayactioncompute_ngd)
    - [overlay(action=compute_jaccard)](#overlayactioncompute_jaccard)
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

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {} |

### add_qnode()
The `add_qnode` method adds an additional QNode to the QueryGraph in the Message object. Currently
                when a curie or name is specified, this method will only return success if a matching node is found in the KG1/KG2 KGNodeIndex.

#### parameters: 

* ##### id

    - is_required: False

    - examples: ['n00', 'n01']

    - default: 

    - type: string

    - description: Any string that is unique among all QNode id fields, with recommended format n00, n01, n02, etc.
                        If no value is provided, autoincrementing values beginning for n00 are used.

* ##### curie

    - is_required: False

    - examples: ['DOID:9281', '[UniProtKB:P12345,UniProtKB:Q54321]']

    - type: string

    - description: Any compact URI (CURIE) (e.g. DOID:9281) (May also be a list like [UniProtKB:P12345,UniProtKB:Q54321])

    - default:
  There is no default value. 

* ##### name

    - is_required: False

    - examples: ['hypertension', 'insulin']

    - type: string

    - description: Any name of a bioentity that will be resolved into a CURIE if possible or result in an error if not (e.g. hypertension, insulin)

    - default:
  There is no default value. 

* ##### type

    - is_required: False

    - examples: ['protein', 'chemical_substance', 'disease']

    - type: string

    - description: Any valid Translator bioentity type (e.g. protein, chemical_substance, disease)

    - default:
  There is no default value. 

* ##### is_set

    - is_required: False

    - enum: ['true', 'false']

    - examples: ['true', 'false']

    - default: false

    - type: boolean

    - description: If set to true, this QNode represents a set of nodes that are all in common between the two other linked QNodes

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'id': {'is_required': False, 'examples': ['n00', 'n01'], 'default': '', 'type': 'string', 'description': 'Any string that is unique among all QNode id fields, with recommended format n00, n01, n02, etc.\n                        If no value is provided, autoincrementing values beginning for n00 are used.'}, 'curie': {'is_required': False, 'examples': ['DOID:9281', '[UniProtKB:P12345,UniProtKB:Q54321]'], 'type': 'string', 'description': 'Any compact URI (CURIE) (e.g. DOID:9281) (May also be a list like [UniProtKB:P12345,UniProtKB:Q54321])'}, 'name': {'is_required': False, 'examples': ['hypertension', 'insulin'], 'type': 'string', 'description': 'Any name of a bioentity that will be resolved into a CURIE if possible or result in an error if not (e.g. hypertension, insulin)'}, 'type': {'is_required': False, 'examples': ['protein', 'chemical_substance', 'disease'], 'type': 'string', 'description': 'Any valid Translator bioentity type (e.g. protein, chemical_substance, disease)'}, 'is_set': {'is_required': False, 'enum': ['true', 'false'], 'examples': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'If set to true, this QNode represents a set of nodes that are all in common between the two other linked QNodes'}} |

### add_qedge()
The `add_qedge` command adds an additional QEdge to the QueryGraph in the Message object. Currently
                source_id and target_id QNodes must already be present in the QueryGraph. The specified type is not currently checked that it is a
                valid Translator/BioLink relationship type, but it should be.

#### parameters: 

* ##### id

    - is_required: False

    - examples: ['e00', 'e01']

    - default: 

    - type: string

    - description: Any string that is unique among all QEdge id fields, with recommended format e00, e01, e02, etc.
                        If no value is provided, autoincrementing values beginning for e00 are used.

* ##### source_id

    - is_required: True

    - examples: ['n00', 'n01']

    - type: string

    - description: id of the source QNode already present in the QueryGraph (e.g. n00, n01)

    - default:
  There is no default value. 

* ##### target_id

    - is_required: True

    - examples: ['n01', 'n02']

    - type: string

    - description: id of the target QNode already present in the QueryGraph (e.g. n01, n02)

    - default:
  There is no default value. 

* ##### type

    - is_required: False

    - examples: ['protein', 'physically_interacts_with', 'participates_in']

    - type: string

    - description: Any valid Translator/BioLink relationship type (e.g. physically_interacts_with, participates_in)

    - default:
  There is no default value. 

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'id': {'is_required': False, 'examples': ['e00', 'e01'], 'default': '', 'type': 'string', 'description': 'Any string that is unique among all QEdge id fields, with recommended format e00, e01, e02, etc.\n                        If no value is provided, autoincrementing values beginning for e00 are used.'}, 'source_id': {'is_required': True, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'id of the source QNode already present in the QueryGraph (e.g. n00, n01)'}, 'target_id': {'is_required': True, 'examples': ['n01', 'n02'], 'type': 'string', 'description': 'id of the target QNode already present in the QueryGraph (e.g. n01, n02)'}, 'type': {'is_required': False, 'examples': ['protein', 'physically_interacts_with', 'participates_in'], 'type': 'string', 'description': 'Any valid Translator/BioLink relationship type (e.g. physically_interacts_with, participates_in)'}} |

## ARAX_expander
### expand(kp=ARAX/KG1)
This command reaches out to the RTX KG1 Neo4j instance to find all bioentity subpaths that satisfy the query graph.

#### parameters: 

* ##### edge_id

    - is_required: False

    - examples: ['e00', '[e00, e01]']

    - type: string

    - description: A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### node_id

    - is_required: False

    - examples: ['n00', '[n00, n01]']

    - type: string

    - description: A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### continue_if_no_results

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to continue execution if no paths are found matching the query graph.

* ##### enforce_directionality

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to obey (vs. ignore) edge directions in the query graph.

* ##### use_synonyms

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: true

    - type: boolean

    - description: Whether to consider curie synonyms and merge synonymous nodes.

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_id': {'is_required': False, 'examples': ['e00', '[e00, e01]'], 'type': 'string', 'description': 'A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).'}, 'node_id': {'is_required': False, 'examples': ['n00', '[n00, n01]'], 'type': 'string', 'description': 'A query graph node ID or list of such IDs to expand (default is to expand entire query graph).'}, 'continue_if_no_results': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to continue execution if no paths are found matching the query graph.'}, 'enforce_directionality': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to obey (vs. ignore) edge directions in the query graph.'}, 'use_synonyms': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'true', 'type': 'boolean', 'description': 'Whether to consider curie synonyms and merge synonymous nodes.'}} |

### expand(kp=ARAX/KG2)
This command reaches out to the RTX KG2 knowledge graph to find all bioentity subpaths that satisfy the query graph. If use_synonyms=true, it uses the KG2canonicalized ('KG2c') Neo4j instance; otherwise, the regular KG2 Neo4j instance is used.

#### parameters: 

* ##### edge_id

    - is_required: False

    - examples: ['e00', '[e00, e01]']

    - type: string

    - description: A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### node_id

    - is_required: False

    - examples: ['n00', '[n00, n01]']

    - type: string

    - description: A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### continue_if_no_results

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to continue execution if no paths are found matching the query graph.

* ##### enforce_directionality

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to obey (vs. ignore) edge directions in the query graph.

* ##### use_synonyms

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: true

    - type: boolean

    - description: Whether to consider curie synonyms and merge synonymous nodes.

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_id': {'is_required': False, 'examples': ['e00', '[e00, e01]'], 'type': 'string', 'description': 'A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).'}, 'node_id': {'is_required': False, 'examples': ['n00', '[n00, n01]'], 'type': 'string', 'description': 'A query graph node ID or list of such IDs to expand (default is to expand entire query graph).'}, 'continue_if_no_results': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to continue execution if no paths are found matching the query graph.'}, 'enforce_directionality': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to obey (vs. ignore) edge directions in the query graph.'}, 'use_synonyms': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'true', 'type': 'boolean', 'description': 'Whether to consider curie synonyms and merge synonymous nodes.'}} |

### expand(kp=BTE)
This command uses BioThings Explorer (from the Service Provider) to find all bioentity subpaths that satisfy the query graph. Of note, all query nodes must have a type specified for BTE queries. In addition, bi-directional queries are only partially supported (the ARAX system knows how to ignore edge direction when deciding which query node for a query edge will be the 'input' qnode, but BTE itself returns only answers matching the input edge direction).

#### parameters: 

* ##### edge_id

    - is_required: False

    - examples: ['e00', '[e00, e01]']

    - type: string

    - description: A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### node_id

    - is_required: False

    - examples: ['n00', '[n00, n01]']

    - type: string

    - description: A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### continue_if_no_results

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to continue execution if no paths are found matching the query graph.

* ##### enforce_directionality

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to obey (vs. ignore) edge directions in the query graph.

* ##### use_synonyms

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: true

    - type: boolean

    - description: Whether to consider curie synonyms and merge synonymous nodes.

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_id': {'is_required': False, 'examples': ['e00', '[e00, e01]'], 'type': 'string', 'description': 'A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).'}, 'node_id': {'is_required': False, 'examples': ['n00', '[n00, n01]'], 'type': 'string', 'description': 'A query graph node ID or list of such IDs to expand (default is to expand entire query graph).'}, 'continue_if_no_results': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to continue execution if no paths are found matching the query graph.'}, 'enforce_directionality': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to obey (vs. ignore) edge directions in the query graph.'}, 'use_synonyms': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'true', 'type': 'boolean', 'description': 'Whether to consider curie synonyms and merge synonymous nodes.'}} |

### expand(kp=COHD)
This command uses the Clinical Data Provider (COHD) to find all bioentity subpaths that satisfy the query graph.

#### parameters: 

* ##### edge_id

    - is_required: False

    - examples: ['e00', '[e00, e01]']

    - type: string

    - description: A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### node_id

    - is_required: False

    - examples: ['n00', '[n00, n01]']

    - type: string

    - description: A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### continue_if_no_results

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to continue execution if no paths are found matching the query graph.

* ##### use_synonyms

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: true

    - type: boolean

    - description: Whether to consider curie synonyms and merge synonymous nodes.

* ##### COHD_method

    - is_required: False

    - examples: ['paired_concept_freq', 'chi_square']

    - enum: ['paired_concept_freq', 'observed_expected_ratio', 'chi_square']

    - default: paired_concept_freq

    - type: string

    - description: Which measure from COHD should be considered.

* ##### COHD_method_percentile

    - is_required: False

    - examples: [95, 80]

    - min: 0

    - max: 100

    - default: 99

    - type: integer

    - description: What percentile to use as a cut-off/threshold for the specified COHD method.

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_id': {'is_required': False, 'examples': ['e00', '[e00, e01]'], 'type': 'string', 'description': 'A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).'}, 'node_id': {'is_required': False, 'examples': ['n00', '[n00, n01]'], 'type': 'string', 'description': 'A query graph node ID or list of such IDs to expand (default is to expand entire query graph).'}, 'continue_if_no_results': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to continue execution if no paths are found matching the query graph.'}, 'use_synonyms': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'true', 'type': 'boolean', 'description': 'Whether to consider curie synonyms and merge synonymous nodes.'}, 'COHD_method': {'is_required': False, 'examples': ['paired_concept_freq', 'chi_square'], 'enum': ['paired_concept_freq', 'observed_expected_ratio', 'chi_square'], 'default': 'paired_concept_freq', 'type': 'string', 'description': 'Which measure from COHD should be considered.'}, 'COHD_method_percentile': {'is_required': False, 'examples': [95, 80], 'min': 0, 'max': 100, 'default': 99, 'type': 'integer', 'description': 'What percentile to use as a cut-off/threshold for the specified COHD method.'}} |

### expand(kp=GeneticsKP)
This command reaches out to the Genetics Provider to find all bioentity subpaths that satisfy the query graph. It currently can answers questions involving the following node types: gene, protein, disease, phenotypic_feature, pathway. Temporarily (while the integration is under development), it can only be used as the first hop in a query.

#### parameters: 

* ##### edge_id

    - is_required: False

    - examples: ['e00', '[e00, e01]']

    - type: string

    - description: A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### node_id

    - is_required: False

    - examples: ['n00', '[n00, n01]']

    - type: string

    - description: A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### continue_if_no_results

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to continue execution if no paths are found matching the query graph.

* ##### use_synonyms

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: true

    - type: boolean

    - description: Whether to consider curie synonyms and merge synonymous nodes.

* ##### include_integrated_score

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to add genetics-quantile edges (in addition to MAGMA edges) from the Genetics KP.

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_id': {'is_required': False, 'examples': ['e00', '[e00, e01]'], 'type': 'string', 'description': 'A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).'}, 'node_id': {'is_required': False, 'examples': ['n00', '[n00, n01]'], 'type': 'string', 'description': 'A query graph node ID or list of such IDs to expand (default is to expand entire query graph).'}, 'continue_if_no_results': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to continue execution if no paths are found matching the query graph.'}, 'use_synonyms': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'true', 'type': 'boolean', 'description': 'Whether to consider curie synonyms and merge synonymous nodes.'}, 'include_integrated_score': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to add genetics-quantile edges (in addition to MAGMA edges) from the Genetics KP.'}} |

### expand(kp=NGD)
This command uses ARAX's in-house normalized google distance (NGD) database to expand a query graph; it returns edges between nodes with an NGD value below a certain threshold. This threshold is currently hardcoded as 0.5, though this will be made configurable/smarter in the future.

#### parameters: 

* ##### edge_id

    - is_required: False

    - examples: ['e00', '[e00, e01]']

    - type: string

    - description: A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### node_id

    - is_required: False

    - examples: ['n00', '[n00, n01]']

    - type: string

    - description: A query graph node ID or list of such IDs to expand (default is to expand entire query graph).

    - default:
  There is no default value. 

* ##### continue_if_no_results

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: false

    - type: boolean

    - description: Whether to continue execution if no paths are found matching the query graph.

* ##### use_synonyms

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: true

    - type: boolean

    - description: Whether to consider curie synonyms and merge synonymous nodes.

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_id': {'is_required': False, 'examples': ['e00', '[e00, e01]'], 'type': 'string', 'description': 'A query graph edge ID or list of such IDs to expand (default is to expand entire query graph).'}, 'node_id': {'is_required': False, 'examples': ['n00', '[n00, n01]'], 'type': 'string', 'description': 'A query graph node ID or list of such IDs to expand (default is to expand entire query graph).'}, 'continue_if_no_results': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'false', 'type': 'boolean', 'description': 'Whether to continue execution if no paths are found matching the query graph.'}, 'use_synonyms': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'true', 'type': 'boolean', 'description': 'Whether to consider curie synonyms and merge synonymous nodes.'}} |

## ARAX_overlay
### overlay(action=overlay_exposures_data)

                    `overlay_exposures_data` overlays edges with p-values obtained from the ICEES+ (Integrated Clinical and Environmental Exposures Service) knowledge provider.
                    This information is included in edge attributes with the name `icees_p-value`.
                    You have the choice of applying this to all edges in the knowledge graph, or only between specified source/target qnode IDs. If the latter, the data is added in 'virtual' edges with the type `has_icees_p-value_with`.

                    This can be applied to an arbitrary knowledge graph (i.e. not just those created/recognized by Expander Agent).
                    

#### parameters: 

* ##### virtual_relation_label

    - is_required: False

    - examples: ['N1', 'J2']

    - type: string

    - description: An optional label to help identify the virtual edge in the relation field.

    - default:
  There is no default value. 

* ##### source_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

* ##### target_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'virtual_relation_label': {'is_required': False, 'examples': ['N1', 'J2'], 'type': 'string', 'description': 'An optional label to help identify the virtual edge in the relation field.'}, 'source_qnode_id': {'is_required': False, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'}, 'target_qnode_id': {'is_required': False, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'}} |

### overlay(action=fisher_exact_test)

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

                    

#### parameters: 

* ##### source_qnode_id

    - is_required: True

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific source query node id (required)

    - default:
  There is no default value. 

* ##### virtual_relation_label

    - is_required: True

    - examples: ['N1', 'J2', 'FET']

    - type: string

    - description: An optional label to help identify the virtual edge in the relation field.

    - default:
  There is no default value. 

* ##### target_qnode_id

    - is_required: True

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific target query node id (required)

    - default:
  There is no default value. 

* ##### rel_edge_id

    - is_required: False

    - examples: ['e00', 'e01']

    - type: string

    - description: a specific QEdge id of edges connected to both source nodes and target nodes in message KG (optional, otherwise all edges connected to both source nodes and target nodes in message KG are considered), eg. 'e01'

    - default:
  There is no default value. 

* ##### top_n

    - is_required: False

    - examples: ['all', 5, 50]

    - type: int or None

    - description: an int indicating the top number (the smallest) of p-values to return (optional,otherwise all results returned)

    - default: None

* ##### cutoff

    - is_required: False

    - examples: ['all', 0.05, 0.95]

    - type: float or None

    - description: a float indicating the p-value cutoff to return the results (optional, otherwise all results returned), eg. 0.05

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'source_qnode_id': {'is_required': True, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific source query node id (required)'}, 'virtual_relation_label': {'is_required': True, 'examples': ['N1', 'J2', 'FET'], 'type': 'string', 'description': 'An optional label to help identify the virtual edge in the relation field.'}, 'target_qnode_id': {'is_required': True, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific target query node id (required)'}, 'rel_edge_id': {'is_required': False, 'examples': ['e00', 'e01'], 'type': 'string', 'description': "a specific QEdge id of edges connected to both source nodes and target nodes in message KG (optional, otherwise all edges connected to both source nodes and target nodes in message KG are considered), eg. 'e01'"}, 'top_n': {'is_required': False, 'examples': ['all', 5, 50], 'type': 'int or None', 'description': 'an int indicating the top number (the smallest) of p-values to return (optional,otherwise all results returned)', 'default': None}, 'cutoff': {'is_required': False, 'examples': ['all', 0.05, 0.95], 'type': 'float or None', 'description': 'a float indicating the p-value cutoff to return the results (optional, otherwise all results returned), eg. 0.05', 'default': None}} |

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
                    

#### parameters: 

* ##### paired_concept_frequency

    - is_required: False

    - examples: ['true', 'false']

    - type: string

    - description: Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.

    - default:
  There is no default value. 

* ##### observed_expected_ratio

    - is_required: False

    - examples: ['true', 'false']

    - type: string

    - description: Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.

    - default:
  There is no default value. 

* ##### chi_square

    - is_required: False

    - examples: ['true', 'false']

    - type: string

    - description: Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.

    - default:
  There is no default value. 

* ##### virtual_relation_label

    - is_required: False

    - examples: ['N1', 'J2']

    - type: string

    - description: An optional label to help identify the virtual edge in the relation field.

    - default:
  There is no default value. 

* ##### source_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

* ##### target_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'paired_concept_frequency': {'is_required': False, 'examples': ['true', 'false'], 'type': 'string', 'description': 'Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.'}, 'observed_expected_ratio': {'is_required': False, 'examples': ['true', 'false'], 'type': 'string', 'description': 'Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.'}, 'chi_square': {'is_required': False, 'examples': ['true', 'false'], 'type': 'string', 'description': 'Indicates if you want to use the paired concept frequency option. Mutually exlisive with: `paired_concept_frequency`, `observed_expected_ratio`, and `chi_square` if any of the oters are set to true while this is there will be an error.'}, 'virtual_relation_label': {'is_required': False, 'examples': ['N1', 'J2'], 'type': 'string', 'description': 'An optional label to help identify the virtual edge in the relation field.'}, 'source_qnode_id': {'is_required': False, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'}, 'target_qnode_id': {'is_required': False, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'}} |

### overlay(action=add_node_pmids)

                    `add_node_pmids` adds PubMed PMID's as node attributes to each node in the knowledge graph.
                    This information is obtained from mapping node identifiers to MeSH terms and obtaining which PubMed articles have this MeSH term
                    either labeling in the metadata or has the MeSH term occurring in the abstract of the article.

                    This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### max_num

    - is_required: False

    - examples: ['all', 5, 50]

    - type: int or string

    - description: The maximum number of values to return. Enter 'all' to return everything

    - default: 100

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'max_num': {'is_required': False, 'examples': ['all', 5, 50], 'type': 'int or string', 'description': "The maximum number of values to return. Enter 'all' to return everything", 'default': 100}} |

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

    - is_required: False

    - examples: ['0', 'inf']

    - default: inf

    - type: string

    - description: The default value of the normalized Google distance (if its value cannot be determined)

* ##### virtual_relation_label

    - is_required: False

    - examples: ['N1', 'J2']

    - type: string

    - description: An optional label to help identify the virtual edge in the relation field.

    - default:
  There is no default value. 

* ##### source_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

* ##### target_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

||||
|-----|-----|-----|
|_DSL parameters_| brief_description | parameters |
|_DSL arguments_| 

### overlay(action=compute_jaccard)

                    `compute_jaccard` creates virtual edges and adds an edge attribute (with the property name `jaccard_index`) containing the following information:
                    The jaccard similarity measures how many `intermediate_node_id`'s are shared in common between each `start_node_id` and `target_node_id`.
                    This is used for purposes such as "find me all drugs (`start_node_id`) that have many proteins (`intermediate_node_id`) in common with this disease (`end_node_id`)."
                    This can be used for downstream filtering to concentrate on relevant bioentities.

                    This can be applied to an arbitrary knowledge graph as possible edge types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### start_node_id

    - is_required: True

    - examples: ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836']

    - type: string

    - description: A curie id specifying the starting node

    - default:
  There is no default value. 

* ##### intermediate_node_id

    - is_required: True

    - examples: ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836']

    - type: string

    - description: A curie id specifying the intermediate node

    - default:
  There is no default value. 

* ##### end_node_id

    - is_required: True

    - examples: ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836']

    - type: string

    - description: A curie id specifying the ending node

    - default:
  There is no default value. 

* ##### virtual_relation_label

    - is_required: True

    - examples: ['N1', 'J2', 'FET']

    - type: string

    - description: An optional label to help identify the virtual edge in the relation field.

    - default:
  There is no default value. 

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'start_node_id': {'is_required': True, 'examples': ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836'], 'type': 'string', 'description': 'A curie id specifying the starting node'}, 'intermediate_node_id': {'is_required': True, 'examples': ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836'], 'type': 'string', 'description': 'A curie id specifying the intermediate node'}, 'end_node_id': {'is_required': True, 'examples': ['DOID:1872', 'CHEBI:7476', 'UMLS:C1764836'], 'type': 'string', 'description': 'A curie id specifying the ending node'}, 'virtual_relation_label': {'is_required': True, 'examples': ['N1', 'J2', 'FET'], 'type': 'string', 'description': 'An optional label to help identify the virtual edge in the relation field.'}} |

### overlay(action=predict_drug_treats_disease)

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
                    

#### parameters: 

* ##### virtual_relation_label

    - is_required: False

    - examples: ['N1', 'J2']

    - type: string

    - description: An optional label to help identify the virtual edge in the relation field.

    - default:
  There is no default value. 

* ##### source_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

* ##### target_qnode_id

    - is_required: False

    - examples: ['n00', 'n01']

    - type: string

    - description: a specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)

    - default:
  There is no default value. 

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'virtual_relation_label': {'is_required': False, 'examples': ['N1', 'J2'], 'type': 'string', 'description': 'An optional label to help identify the virtual edge in the relation field.'}, 'source_qnode_id': {'is_required': False, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific source query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'}, 'target_qnode_id': {'is_required': False, 'examples': ['n00', 'n01'], 'type': 'string', 'description': 'a specific target query node id (optional, otherwise applied to all edges, must have a virtual_relation_label to use this parameter)'}} |

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

    - is_required: True

    - examples: ['contraindicated_for', 'affects', 'expressed_in']

    - type: string

    - description: The name of the edge type to filter by.

    - default: None

* ##### remove_connected_nodes

    - is_required: False

    - examples: ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F']

    - type: string

    - description: Indicates whether or not to remove the nodes connected to the edge.

    - default: False

* ##### qnode_id

    - is_required: False

    - examples: ['n01', 'n02']

    - type: string

    - description: If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_type': {'is_required': True, 'examples': ['contraindicated_for', 'affects', 'expressed_in'], 'type': 'string', 'description': 'The name of the edge type to filter by.', 'default': None}, 'remove_connected_nodes': {'is_required': False, 'examples': ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'], 'type': 'string', 'description': 'Indicates whether or not to remove the nodes connected to the edge.', 'default': 'False'}, 'qnode_id': {'is_required': False, 'examples': ['n01', 'n02'], 'type': 'string', 'description': 'If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.', 'default': None}} |

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

    - is_required: True

    - examples: ['jaccard_index', 'observed_expected_ratio', 'normalized_google_distance']

    - type: string

    - description: The name of the edge attribute to filter on.

    - default: None

* ##### direction

    - is_required: True

    - examples: ['above', 'below']

    - type: string

    - description: Indictes whether to remove above or below the given threshold.

    - default: None

* ##### threshold

    - is_required: True

    - examples: [5, 0.45]

    - type: float

    - description: The threshold to filter with.

    - default: None

* ##### remove_connected_nodes

    - is_required: False

    - examples: ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F']

    - type: string

    - description: Indicates whether or not to remove the nodes connected to the edge.

    - default: False

* ##### qnode_id

    - is_required: False

    - examples: ['n01', 'n02']

    - type: string

    - description: If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_attribute': {'is_required': True, 'examples': ['jaccard_index', 'observed_expected_ratio', 'normalized_google_distance'], 'type': 'string', 'description': 'The name of the edge attribute to filter on.', 'default': None}, 'direction': {'is_required': True, 'examples': ['above', 'below'], 'type': 'string', 'description': 'Indictes whether to remove above or below the given threshold.', 'default': None}, 'threshold': {'is_required': True, 'examples': [5, 0.45], 'type': 'float', 'description': 'The threshold to filter with.', 'default': None}, 'remove_connected_nodes': {'is_required': False, 'examples': ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'], 'type': 'string', 'description': 'Indicates whether or not to remove the nodes connected to the edge.', 'default': 'False'}, 'qnode_id': {'is_required': False, 'examples': ['n01', 'n02'], 'type': 'string', 'description': 'If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.', 'default': None}} |

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

    - is_required: True

    - examples: ['source_id', 'provided_by', 'is_defined_by']

    - type: string

    - description: The name of the edge property to filter on.

    - default: None

* ##### property_value

    - is_required: True

    - examples: ['DOID:8398', 'Pharos', 'ARAX/RTX']

    - type: string

    - description: The edge property vaue to indicate which edges to remove.

    - default: None

* ##### remove_connected_nodes

    - is_required: False

    - examples: ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F']

    - type: string

    - description: Indicates whether or not to remove the nodes connected to the edge.

    - default: False

* ##### qnode_id

    - is_required: False

    - examples: ['n01', 'n02']

    - type: string

    - description: If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_property': {'is_required': True, 'examples': ['source_id', 'provided_by', 'is_defined_by'], 'type': 'string', 'description': 'The name of the edge property to filter on.', 'default': None}, 'property_value': {'is_required': True, 'examples': ['DOID:8398', 'Pharos', 'ARAX/RTX'], 'type': 'string', 'description': 'The edge property vaue to indicate which edges to remove.', 'default': None}, 'remove_connected_nodes': {'is_required': False, 'examples': ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'], 'type': 'string', 'description': 'Indicates whether or not to remove the nodes connected to the edge.', 'default': 'False'}, 'qnode_id': {'is_required': False, 'examples': ['n01', 'n02'], 'type': 'string', 'description': 'If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.', 'default': None}} |

### filter_kg(action=remove_edges_by_stats)

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
                    

#### parameters: 

* ##### edge_attribute

    - is_required: True

    - examples: ['jaccard_index', 'observed_expected_ratio', 'normalized_google_distance']

    - type: string

    - description: The name of the edge attribute to filter on.

    - default: None

* ##### type

    - is_required: False

    - examples: ['n', 'std', 'std_dev', 'percentile', 'p']

    - type: string

    - description: The statistic to use for filtering.

    - default: n

* ##### direction

    - is_required: False

    - examples: ['above', 'below']

    - type: string

    - description: Indictes whether to remove above or below the given threshold.

    - default: a value dictated by the `edge_attribute` parameter. If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `direction` defaults to above. If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `direction` defaults to below.

* ##### threshold

    - is_required: False

    - examples: [5, 0.45]

    - type: float

    - description: The threshold to filter with.

    - default: a value dictated by the `type` parameter. If `type` is 'n' then will default to 50. If `type` is 'std_dev' or 'std' then it will default to 1.If `type` is 'percentile' or 'p' then it will default to 95 unless `edge_attribute` is also 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then it will default to 5.

* ##### top

    - is_required: False

    - examples: ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F']

    - type: string

    - description: Indicate whether or not the threshold should be placed in top of the list. E.g. top set as True with type set as std_dev will set the cutoff for filtering as the mean + threshold * std_dev while setting top to False will set the cutoff as the mean - std_dev * threshold.

    - default: a value dictated by the `edge_attribute` parameter. If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `top` defaults to False. If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `top` defaults to True.

* ##### remove_connected_nodes

    - is_required: False

    - examples: ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F']

    - type: string

    - description: Indicates whether or not to remove the nodes connected to the edge.

    - default: False

* ##### qnode_id

    - is_required: False

    - examples: ['n01', 'n02']

    - type: string

    - description: If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_attribute': {'is_required': True, 'examples': ['jaccard_index', 'observed_expected_ratio', 'normalized_google_distance'], 'type': 'string', 'description': 'The name of the edge attribute to filter on.', 'default': None}, 'type': {'is_required': False, 'examples': ['n', 'std', 'std_dev', 'percentile', 'p'], 'type': 'string', 'description': 'The statistic to use for filtering.', 'default': 'n'}, 'direction': {'is_required': False, 'examples': ['above', 'below'], 'type': 'string', 'description': 'Indictes whether to remove above or below the given threshold.', 'default': "a value dictated by the `edge_attribute` parameter. If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `direction` defaults to above. If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `direction` defaults to below."}, 'threshold': {'is_required': False, 'examples': [5, 0.45], 'type': 'float', 'description': 'The threshold to filter with.', 'default': "a value dictated by the `type` parameter. If `type` is 'n' then will default to 50. If `type` is 'std_dev' or 'std' then it will default to 1.If `type` is 'percentile' or 'p' then it will default to 95 unless `edge_attribute` is also 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then it will default to 5."}, 'top': {'is_required': False, 'examples': ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'], 'type': 'string', 'description': 'Indicate whether or not the threshold should be placed in top of the list. E.g. top set as True with type set as std_dev will set the cutoff for filtering as the mean + threshold * std_dev while setting top to False will set the cutoff as the mean - std_dev * threshold.', 'default': "a value dictated by the `edge_attribute` parameter. If `edge attribute` is 'ngd', 'chi_square', 'fisher_exact', or 'normalized_google_distance' then `top` defaults to False. If `edge_attribute` is 'jaccard_index', 'observed_expected_ratio', 'probability_treats' or anything else not listed then `top` defaults to True."}, 'remove_connected_nodes': {'is_required': False, 'examples': ['true', 'false', 'True', 'False', 't', 'f', 'T', 'F'], 'type': 'string', 'description': 'Indicates whether or not to remove the nodes connected to the edge.', 'default': 'False'}, 'qnode_id': {'is_required': False, 'examples': ['n01', 'n02'], 'type': 'string', 'description': 'If remove_connected_nodes is set to True this indicates if you only want nodes corresponding to a specific qnode_id to be removed.If not provided the qnode_id will not be considered when filtering.', 'default': None}} |

### filter_kg(action=remove_nodes_by_type)

                    `remove_node_by_type` removes nodes from the knowledge graph (KG) based on a given node type.
                    Use cases include:
                    * removing all nodes that have `node_type=protein`.
                    * removing all nodes that have `node_type=chemical_substance`.
                    * etc.
                    This can be applied to an arbitrary knowledge graph as possible node types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### node_type

    - is_required: True

    - examples: ['chemical_substance', 'disease']

    - type: string

    - description: The name of the node type to filter by.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'node_type': {'is_required': True, 'examples': ['chemical_substance', 'disease'], 'type': 'string', 'description': 'The name of the node type to filter by.', 'default': None}} |

### filter_kg(action=remove_nodes_by_property)

                    `remove_nodes_by_property` removes nodes from the knowledge graph (KG) based on a given node property.
                    Use cases include:
                                    
                    * removing all nodes that were provided by a certain knowledge provider (KP) via `node_property=provided, property_value=Pharos` to remove all nodes provided by the KP Pharos.
                    * removing all nodes provided by another ARA via `node_property=is_defined_by, property_value=ARAX/RTX`
                    * etc. etc.
                                    
                    This can be applied to an arbitrary knowledge graph as possible node properties are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### node_property

    - is_required: True

    - examples: ['provided_by', 'is_defined_by']

    - type: string

    - description: The name of the node property to filter on.

    - default: None

* ##### property_value

    - is_required: True

    - examples: ['Pharos', 'ARAX/RTX']

    - type: string

    - description: The node property vaue to indicate which nodes to remove.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'node_property': {'is_required': True, 'examples': ['provided_by', 'is_defined_by'], 'type': 'string', 'description': 'The name of the node property to filter on.', 'default': None}, 'property_value': {'is_required': True, 'examples': ['Pharos', 'ARAX/RTX'], 'type': 'string', 'description': 'The node property vaue to indicate which nodes to remove.', 'default': None}} |

### filter_kg(action=remove_orphaned_nodes)

                    `remove_orphaned_nodes` removes nodes from the knowledge graph (KG) that are not connected via any edges.
                    Specifying a `node_type` will restrict this to only remove orphaned nodes of a certain type
                    This can be applied to an arbitrary knowledge graph as possible node types are computed dynamically (i.e. not just those created/recognized by the ARA Expander team).
                    

#### parameters: 

* ##### node_type

    - is_required: False

    - examples: ['chemical_substance', 'disease']

    - type: string

    - description: The name of the node type to filter by. If no value provided node type will not be considered.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'node_type': {'is_required': False, 'examples': ['chemical_substance', 'disease'], 'type': 'string', 'description': 'The name of the node type to filter by. If no value provided node type will not be considered.', 'default': None}} |

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

    - is_required: True

    - examples: ['jaccard_index', 'observed_expected_ratio', 'normalized_google_distance']

    - type: string

    - description: The name of the attribute to filter by.

    - default: None

* ##### edge_relation

    - is_required: False

    - examples: ['N1', 'C1']

    - type: string

    - description: The name of unique identifier to only filter on edges with matching relation field. (stored in the relation neo4j edge property) If not provided the edge relation will not be considered when filtering.

    - default: None

* ##### direction

    - is_required: True

    - examples: ['descending', 'd', 'ascending', 'a']

    - type: string

    - description: The direction in which to order results. (ascending or descending)

    - default: None

* ##### max_results

    - is_required: False

    - examples: [5, 10, 50]

    - type: integer

    - description: The maximum number of results to return. If not provided all results will be returned.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'edge_attribute': {'is_required': True, 'examples': ['jaccard_index', 'observed_expected_ratio', 'normalized_google_distance'], 'type': 'string', 'description': 'The name of the attribute to filter by.', 'default': None}, 'edge_relation': {'is_required': False, 'examples': ['N1', 'C1'], 'type': 'string', 'description': 'The name of unique identifier to only filter on edges with matching relation field. (stored in the relation neo4j edge property) If not provided the edge relation will not be considered when filtering.', 'default': None}, 'direction': {'is_required': True, 'examples': ['descending', 'd', 'ascending', 'a'], 'type': 'string', 'description': 'The direction in which to order results. (ascending or descending)', 'default': None}, 'max_results': {'is_required': False, 'examples': [5, 10, 50], 'type': 'integer', 'description': 'The maximum number of results to return. If not provided all results will be returned.', 'default': None}} |

### filter_results(action=sort_by_node_attribute)

                    `sort_by_node_attribute` sorts the results by the nodes based on a a certain node attribute.
                    node attributes are a list of additional attributes for an node.
                    Use cases include:

                    * sorting the rsults by the number of pubmed ids returning the top 20. `"filter_results(action=sort_by_node_attribute, node_attribute=pubmed_ids, direction=d, max_results=20)"`
                    * etc. etc.
                                    
                    You have the option to specify the node type (e.g. via `node_type=<an node type>`)
                    Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`
                    

#### parameters: 

* ##### node_attribute

    - is_required: True

    - examples: ['pubmed_ids']

    - type: string

    - description: The name of the attribute to filter by.

    - default: None

* ##### node_type

    - is_required: False

    - examples: ['chemical_substance', 'disease']

    - type: string

    - description: The name of the node type to only filter on nodes of the matching type.If not provided the node type will not be cinsidered when filtering.

    - default: None

* ##### direction

    - is_required: True

    - examples: ['descending', 'd', 'ascending', 'a']

    - type: string

    - description: The direction in which to order results. (ascending or descending)

    - default: None

* ##### max_results

    - is_required: False

    - examples: [5, 10, 50]

    - type: integer

    - description: The maximum number of results to return. If not provided all results will be returned.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'node_attribute': {'is_required': True, 'examples': ['pubmed_ids'], 'type': 'string', 'description': 'The name of the attribute to filter by.', 'default': None}, 'node_type': {'is_required': False, 'examples': ['chemical_substance', 'disease'], 'type': 'string', 'description': 'The name of the node type to only filter on nodes of the matching type.If not provided the node type will not be cinsidered when filtering.', 'default': None}, 'direction': {'is_required': True, 'examples': ['descending', 'd', 'ascending', 'a'], 'type': 'string', 'description': 'The direction in which to order results. (ascending or descending)', 'default': None}, 'max_results': {'is_required': False, 'examples': [5, 10, 50], 'type': 'integer', 'description': 'The maximum number of results to return. If not provided all results will be returned.', 'default': None}} |

### filter_results(action=limit_number_of_results)

                    `limit_number_of_results` removes excess results over the specified maximum.

                    Use cases include:

                    * limiting the number of results to 100 `filter_results(action=limit_number_of_results, max_results=100)`
                    * etc. etc.
                    

#### parameters: 

* ##### max_results

    - is_required: True

    - examples: [5, 10, 50]

    - type: integer

    - description: The maximum number of results to return. Default is to return all results.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'max_results': {'is_required': True, 'examples': [5, 10, 50], 'type': 'integer', 'description': 'The maximum number of results to return. Default is to return all results.', 'default': None}} |

### filter_results(action=sort_by_edge_count)

                    `sort_by_edge_count` sorts the results by the number of edges in the results.
                    Use cases include:

                    * return the results with the 10 fewest edges. `filter_results(action=sort_by_edge_count, direction=ascending, max_results=10)`
                    * etc. etc.
                                    
                    You have the option to specify the direction (e.g. `direction=descending`)
                    Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`
                    

#### parameters: 

* ##### direction

    - is_required: True

    - examples: ['descending', 'd', 'ascending', 'a']

    - type: string

    - description: The direction in which to order results. (ascending or descending)

    - default: None

* ##### max_results

    - is_required: False

    - examples: [5, 10, 50]

    - type: integer

    - description: The maximum number of results to return. If not provided all results will be returned.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'direction': {'is_required': True, 'examples': ['descending', 'd', 'ascending', 'a'], 'type': 'string', 'description': 'The direction in which to order results. (ascending or descending)', 'default': None}, 'max_results': {'is_required': False, 'examples': [5, 10, 50], 'type': 'integer', 'description': 'The maximum number of results to return. If not provided all results will be returned.', 'default': None}} |

### filter_results(action=sort_by_node_count)

                    `sort_by_node_count` sorts the results by the number of nodes in the results.
                    Use cases include:

                    * return the results with the 10 most nodes. `filter_results(action=sort_by_node_count, direction=descending, max_results=10)`
                    * etc. etc.
                                    
                    You have the option to specify the direction (e.g. `direction=descending`)
                    Also, you have the option of limiting the number of results returned (e.g. via `max_results=<a non-negative integer>`
                    

#### parameters: 

* ##### direction

    - is_required: True

    - examples: ['descending', 'd', 'ascending', 'a']

    - type: string

    - description: The direction in which to order results. (ascending or descending)

    - default: None

* ##### max_results

    - is_required: False

    - examples: [5, 10, 50]

    - type: integer

    - description: The maximum number of results to return. If not provided all results will be returned.

    - default: None

|||
|-----|-----|
|_DSL parameters_| parameters |
|_DSL arguments_| {'direction': {'is_required': True, 'examples': ['descending', 'd', 'ascending', 'a'], 'type': 'string', 'description': 'The direction in which to order results. (ascending or descending)', 'default': None}, 'max_results': {'is_required': False, 'examples': [5, 10, 50], 'type': 'integer', 'description': 'The maximum number of results to return. If not provided all results will be returned.', 'default': None}} |

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

    - is_required: False

    - examples: ['true', 'false']

    - enum: ['true', 'false']

    - default: true

    - type: boolean

    - description: Whether to ignore (vs. obey) edge directions in the query graph when identifying paths that fulfill it.

||||
|-----|-----|-----|
|_DSL parameters_| brief_description | parameters |
|_DSL arguments_| Creates a list of results consisting of subgraphs from the message knowledge graph that satisfy the query graph. | {'ignore_edge_direction': {'is_required': False, 'examples': ['true', 'false'], 'enum': ['true', 'false'], 'default': 'true', 'type': 'boolean', 'description': 'Whether to ignore (vs. obey) edge directions in the query graph when identifying paths that fulfill it.'}} |

