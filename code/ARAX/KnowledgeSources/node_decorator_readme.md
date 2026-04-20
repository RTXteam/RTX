# `generate_sqlite.py`

Builds the tier0 decoration sqlite that `ARAX_decorator.py` reads at query time to attach node and edge metadata (descriptions, publications, supporting_text, knowledge_level, categories, etc.) onto TRAPI results. The script reproduces the structural features the decorator relies on so it can look up a node by `id`, look up an edge by its triple, or look up all edges between a `(subject, object)` pair without touching Neo4j or rescanning JSONL.

## Requirements

**Software**

| | |
| :--- | :--- |
| Python | 3.10+ |


**Hardware (tier0 scale build: 1.7M nodes, 29M edges)**

| | |
| :--- | :--- |
| RAM | 16 GB minimum. Peak usage is dominated by the nodes dict (~3 to 5 GB) plus sqlite write buffers. The nodes dict is freed before edges are streamed. |
| Cores | 1. Single process, single threaded. sqlite is a single writer. |
| Disk | ~24 GB for the output sqlite. Input JSONL is read sequentially so no additional temp space is needed. Use a local SSD for reasonable build time. |
| Wall clock | ~8 minutes on a typical workstation with fast local disk. Edge streaming is the bulk of it. |

**Filesystem and inputs**

| | |
| :--- | :--- |
| Read access | tier0 `nodes.jsonl`, tier0 `edges.jsonl` |
| Write access | output sqlite path (deleted and rebuilt if it already exists) |
| Env vars | None |

## Inputs

Two canonicalized tier0 JSONL files. One record per line.

* `--nodes` : tier0 nodes JSONL, keyed by `id`
* `--edges` : tier0 edges JSONL, keyed by `id`

## Output

A single sqlite file with two tables and three indices.

All columns are stored as `TEXT`. List fields are joined on the `ǂ` delimiter. Dict and list of dict fields (e.g. `sources`) are JSON serialized. Bools render as `"true"` / `"false"`.

### `nodes` table

One row per canonicalized node. Indexed on `id` (`UNIQUE INDEX node_id_index`).

| Group | Columns |
| :--- | :--- |
| Identity and core | `id`, `name`, `category` |
| Description | `description` |
| Synonyms and cross references | `synonym`, `equivalent_identifiers`, `xref` |
| Labels | `symbol`, `full_name`, `in_taxon_label` |
| Taxonomy | `taxon`, `in_taxon` |
| Structure | `information_content`, `inheritance` |
| ChEMBL specific | `chembl_availability_type`, `chembl_black_box_warning`, `chembl_natural_product`, `chembl_prodrug` |

### `edges` table

One row per edge after duplicate triple collapse. Indexed on `triple` (`UNIQUE INDEX triple_index`) and on `node_pair` (`INDEX node_pair_index`).

| Group | Columns |
| :--- | :--- |
| Generated keys (computed, not in JSONL) | `triple`, `node_pair` |
| Core edge structure | `id`, `subject`, `object`, `predicate` |
| Provenance | `sources`, `agent_type`, `knowledge_level`, `update_date` |
| Content | `description`, `supporting_text`, `publications` |
| Original pre-canonicalization | `original_subject`, `original_predicate`, `original_object` |
| Negation | `negated` |
| Qualifier family | `qualified_predicate`, `qualifier`, `subject_aspect_qualifier`, `subject_direction_qualifier`, `subject_form_or_variant_qualifier`, `object_aspect_qualifier`, `object_direction_qualifier`, `object_form_or_variant_qualifier`, `anatomical_context_qualifier`, `causal_mechanism_qualifier`, `disease_context_qualifier`, `frequency_qualifier`, `onset_qualifier`, `sex_qualifier`, `species_context_qualifier`, `stage_qualifier` |
| Evidence and statistics | `p_value`, `adjusted_p_value`, `evidence_count` |
| Clinical and regulatory | `clinical_approval_status`, `FDA_regulatory_approvals` |

## Key design points

**Deterministic triple key.** Each edge gets a `triple` composed as:

```
{subject}--{predicate}--{qualified_predicate}--{object_direction_qualifier}--{object_aspect_qualifier}--{object}--{primary_knowledge_source}
```

The primary knowledge source is extracted from tier0's structured `sources` list by finding the entry whose `resource_role == "primary_knowledge_source"`. This logic must stay in lockstep with `ARAXDecorator._get_tier0_edge_key` or the decorator's unique triple lookup won't match what is stored. There is a round trip test in the test suite that verifies this.

**Streaming edge inserts.** The edges JSONL is tens of GB, so loading it into memory will OOM a 128 GB box. `_iter_edge_rows()` yields one row per edge line for line from disk straight into `executemany`, keeping memory O(1) per edge. Nodes are small enough (~1.7M rows) to load as a dict first for ease.

**`INSERT OR IGNORE` on triple collisions.** Tier0 has ~260K edges in the JSONL that serialize to an identical triple key (most are MGI `biolink:expressed_in` edges that record the same gene/anatomy relationship from different literature references). The unique triple index is created before the inserts so the constraint is enforced incrementally and first wins behavior silently drops the duplicates at insert time. The final log line prints `Inserted N edges; final table size M rows`, so the duplicate count is visible.

## How to run

```bash
python generate_sqlite.py \
    --nodes  /path/to/nodes.jsonl \
    --edges  /path/to/edges.jsonl \
    --output /path/to/tier0_vX.Y.sqlite
```

## Downstream consumer

`code/ARAX/ARAXQuery/ARAX_decorator.py`. Its `_connect_to_sqlite` method opens `rtxc.tier0_sqlite_path` (configured in `config_dbs.json` as `tier0_sqlite`) out of the `KnowledgeSources/Tier0/` directory. See `decorate_nodes`, `decorate_edges`, and `_decorate_ngd_edges` for the SELECT patterns this sqlite is optimized for.
