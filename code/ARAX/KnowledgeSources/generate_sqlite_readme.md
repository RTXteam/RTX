# `generate_sqlite.py`

Builds the **`tier0-info-for-overlay`** SQLite database. This is intentionally a **minimal** SQLite, not a full ingest of the Tier0 graph. Anything that needs full node or edge properties should query Tier0/Gandalf directly.

The file is consumed only by ARAX's `Overlay/` modules:

* `Overlay/fisher_exact_test.py` — uses `neighbors` and `category_counts`.
* `Overlay/` NGD-style decoration paths — use `edge_publications`.

## Requirements

**Software**

| | |
| :--- | :--- |
| Python | 3.10+ |

**Hardware (tier0 scale build: ~1.7M nodes, ~29M edges)**

| | |
| :--- | :--- |
| RAM | 16 GB minimum, 32 GB comfortable. Peak is dominated by the in-memory nodes dict, the per-node expanded biolink labels, and the neighbor accumulator (`{node_id: {label: set(neighbor_ids)}}`). 128 GB is plenty. |
| Cores | 1. Single process, single threaded. SQLite is a single writer. |
| Disk | A few GB for the output sqlite — most rows in the source `edges.jsonl` are dropped because they have no `publications`. |
| Wall clock | Edge streaming dominates. Plan on minutes, not hours, on a fast local disk. |

**Filesystem and inputs**

| | |
| :--- | :--- |
| Read access | tier0 `nodes.jsonl`, tier0 `edges.jsonl` |
| Write access | `--output-dir` (the script overwrites the target file if it already exists) |
| Env vars | None |

## Inputs

Two canonicalized Tier0 JSONL files. One record per line.

* `--nodes` : Tier0 nodes JSONL, keyed by `id`
* `--edges` : Tier0 edges JSONL, keyed by `id`

## Output

A single SQLite file with three tables. The filename is assembled by the script:

```
tier0-info-for-overlay_v{schema-version}_tier0-{tier0-build-date}.sqlite
```

For example: `tier0-info-for-overlay_v1.0_tier0-20260408.sqlite`.

### `edge_publications` table

One row per edge that has at least one publication. Edges with no publications are skipped — there is no point storing tens of millions of empty rows.

| Column | Type | Notes |
| :--- | :--- | :--- |
| `arax_edge_key` | `TEXT PRIMARY KEY` | Canonical ARAX edge key (see below) |
| `publications`  | `TEXT` | Delimiter-encoded PMID list (delimiter is `ǂ`) |

### `neighbors` table

One row per node that has at least one neighbor. Used by `fisher_exact_test.py` to look up neighbor counts by category.

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | `TEXT PRIMARY KEY` | Node ID |
| `neighbor_counts` | `TEXT` | JSON-encoded `{biolink_category: count}` |

The category keys are **expanded biolink labels**: each neighbor is credited under every ancestor of its `category` (plus mixins), via `biolink_helper.get_ancestors([category], include_mixins=True)`. This is what lets a Fisher Exact Test query for a parent category like `biolink:ChemicalEntity` resolve correctly.

### `category_counts` table

One row per expanded biolink category. Used by `fisher_exact_test.py` for population-size denominators.

| Column | Type |
| :--- | :--- |
| `category` | `TEXT PRIMARY KEY` |
| `count`    | `INTEGER` |

## Key design points

**Canonical ARAX edge key.** Each row in `edge_publications` is keyed on the string returned by:

```python
from util import get_arax_edge_key
get_arax_edge_key(edge)
```

which is byte-equivalent to:

```
{subject}--{predicate}--{qualified_predicate}--{object_direction_qualifier}--{object_aspect_qualifier}--{object}--{primary_knowledge_source}
```

The `primary_knowledge_source` is extracted from Tier0's structured `sources` list by finding the entry whose `resource_role == "primary_knowledge_source"`. Both this script and `code/ARAX/ARAXQuery/util.py` derive the key the same way; they must stay in lockstep.

**Streaming edges, in-memory nodes.** The edges JSONL is tens of GB and is streamed line by line into `executemany`, with the neighbor accumulator updated as a side effect. The nodes JSONL is small enough (~1.7M rows) to load into a dict so we can resolve each edge endpoint's expanded biolink labels in O(1).

**Skipping publication-less edges.** Edges with an empty `publications` field are dropped from the `edge_publications` insert stream entirely. They still contribute to neighbor counts (because the neighbor table cares about graph topology, not content).

**INSERT OR IGNORE on `arax_edge_key` collisions.** If two Tier0 edges serialize to the same canonical key (same subject, predicate, qualifiers, object, primary_knowledge_source), the first one wins. This matches the 1:1 lookup assumption on the ARAX side.

## How to run

```bash
python generate_sqlite.py \
    --nodes            /path/to/nodes.jsonl \
    --edges            /path/to/edges.jsonl \
    --output-dir       /path/to/output_dir \
    --tier0-build-date 20260408
```

Optional:

| Flag | Default | Notes |
| :--- | :--- | :--- |
| `--schema-version` | `1.0` | Stamped into the filename. |
| `--biolink-version` | Currently-pinned ARAX version | Drives the category-ancestor expansion. |

## Downstream consumers

| Consumer | Tables read |
| :--- | :--- |
| `code/ARAX/ARAXQuery/Overlay/fisher_exact_test.py` | `neighbors`, `category_counts` |
| `code/ARAX/ARAXQuery/Overlay/` (NGD-style decoration) | `edge_publications` |

The path to the SQLite file is configured in `code/config_dbs.json` under `database_downloads.tier0_sqlite`.
