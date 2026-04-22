#!/usr/bin/env python3

"""
Build the tier0-info-for-overlay SQLite database from conflated tier0 JSONL files.

This database is intentionally minimal. It is *not* a full ingest of the
Tier0 graph. It only contains what the ARAX Overlay modules need:

    * edge_publications  - per-edge PMID lists, keyed by canonical ARAX edge
                           key. Used by Overlay/NGD-style decoration paths.
    * neighbors          - per-node neighbor counts by expanded biolink
                           category. Used by Overlay/fisher_exact_test.py.
    * category_counts    - node count per expanded biolink category. Also
                           used by Overlay/fisher_exact_test.py.

There are no `nodes` or `edges` tables. Anything that needs full node/edge
properties should query Tier0/Gandalf directly.

The canonical ARAX edge key produced here MUST match
`ARAXQuery/util.get_arax_edge_key(edge)`, otherwise downstream lookups
will silently miss.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "BiolinkHelper")
)
from biolink_helper import get_biolink_helper  # noqa: E402


TIER0_ARRAY_DELIMITER = "ǂ"


# ---------------------------------------------------------------------
# Canonical ARAX edge key (mirror of util.get_arax_edge_key)
# ---------------------------------------------------------------------

def _extract_primary_knowledge_source(sources: Any) -> str:
    if not sources or not isinstance(sources, list):
        return ""
    for source in sources:
        if isinstance(source, dict) and source.get("resource_role") == "primary_knowledge_source":
            return source.get("resource_id") or ""
    return ""


def _get_arax_edge_key(
    subject: str,
    predicate: str,
    object: str,
    primary_knowledge_source: str,
    qualified_predicate: Optional[str],
    object_direction_qualifier: Optional[str],
    object_aspect_qualifier: Optional[str],
) -> str:
    qualified_portion = "--".join([
        qualified_predicate or "",
        object_direction_qualifier or "",
        object_aspect_qualifier or "",
    ])
    return "--".join([
        subject,
        predicate,
        qualified_portion,
        object,
        primary_knowledge_source,
    ])


def _encode_publications(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Iterable):
        cleaned = [str(item) for item in value if item]
        return TIER0_ARRAY_DELIMITER.join(cleaned)
    return str(value)


# ---------------------------------------------------------------------
# Streaming edge pass: drives both edge_publications inserts and
# neighbor accumulation.
# ---------------------------------------------------------------------

def _iter_edge_publication_rows(
    edges_path: Path,
    expanded_labels_by_node: Dict[str, List[str]],
    neighbors_by_label: Dict[str, Dict[str, Set[str]]],
    progress_every: int = 1_000_000,
) -> Iterable[tuple]:
    """
    Yield `(arax_edge_key, publications_str)` rows for edges that have at
    least one publication. As a side effect, populate `neighbors_by_label`
    with `[node_id][expanded_label] -> set(neighbor_ids)` so the caller
    can collapse it into the `neighbors` table after this pass finishes.
    """
    with edges_path.open() as f:
        for index, line in enumerate(f, start=1):
            edge = json.loads(line)

            subject_id = edge["subject"]
            object_id = edge["object"]

            for label in expanded_labels_by_node.get(object_id, ()):
                neighbors_by_label[subject_id][label].add(object_id)
            for label in expanded_labels_by_node.get(subject_id, ()):
                neighbors_by_label[object_id][label].add(subject_id)

            publications = _encode_publications(edge.get("publications"))
            if not publications:
                if index % progress_every == 0:
                    logging.info(f"  ... streamed {index:,} edges")
                continue

            arax_edge_key = _get_arax_edge_key(
                subject=subject_id,
                predicate=edge["predicate"],
                object=object_id,
                primary_knowledge_source=_extract_primary_knowledge_source(edge.get("sources")),
                qualified_predicate=edge.get("qualified_predicate"),
                object_direction_qualifier=edge.get("object_direction_qualifier"),
                object_aspect_qualifier=edge.get("object_aspect_qualifier"),
            )

            yield (arax_edge_key, publications)

            if index % progress_every == 0:
                logging.info(f"  ... streamed {index:,} edges")


# ---------------------------------------------------------------------
# JSONL loader (nodes only — kept in memory for category expansion)
# ---------------------------------------------------------------------

def _load_jsonl_as_dict(path: Path, key_field: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    with path.open() as f:
        for line in f:
            obj = json.loads(line)
            result[obj[key_field]] = obj
    return result


# ---------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------

def create_tier0_overlay_sqlite_db(
    nodes_path: Path,
    edges_path: Path,
    output_db: Path,
    biolink_version: Optional[str] = None,
) -> None:

    if output_db.exists():
        output_db.unlink()

    connection = sqlite3.connect(output_db)

    # -------------------------
    # Expanded biolink labels per node — drives `neighbors` and
    # `category_counts`. Tier0 nodes carry only a singular `category`;
    # we expand to ancestors + mixins so Fisher Exact Test queries by a
    # parent category like biolink:ChemicalEntity still resolve.
    # -------------------------

    logging.info("Loading nodes into memory...")
    nodes_dict = _load_jsonl_as_dict(nodes_path, "id")
    logging.info(f"Loaded {len(nodes_dict):,} nodes")

    logging.info("Expanding biolink category ancestors for each node...")
    bh = get_biolink_helper(biolink_version)
    expanded_labels_by_node: Dict[str, List[str]] = {}
    for node_id, node in nodes_dict.items():
        category = node.get("category")
        if not category:
            expanded_labels_by_node[node_id] = []
            continue
        categories = category if isinstance(category, list) else [category]
        expanded_labels_by_node[node_id] = list(
            bh.get_ancestors(categories, include_mixins=True)
        )

    # -------------------------
    # edge_publications: streamed from the edges JSONL, only rows with
    # at least one publication. Same pass populates the neighbor
    # accumulator (consumed below).
    # -------------------------

    connection.execute(
        "CREATE TABLE edge_publications ("
        "arax_edge_key TEXT PRIMARY KEY, "
        "publications  TEXT"
        ")"
    )

    neighbors_by_label: Dict[str, Dict[str, Set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )

    logging.info("Streaming edges and writing edge_publications rows...")
    changes_before = connection.total_changes
    connection.executemany(
        "INSERT OR IGNORE INTO edge_publications (arax_edge_key, publications) VALUES (?, ?)",
        _iter_edge_publication_rows(edges_path, expanded_labels_by_node, neighbors_by_label),
    )
    inserted = connection.total_changes - changes_before
    logging.info(f"Inserted {inserted:,} edge_publications rows")
    connection.commit()

    # -------------------------
    # neighbors
    # -------------------------

    logging.info(f"Writing neighbors table ({len(neighbors_by_label):,} nodes)...")
    connection.execute(
        "CREATE TABLE neighbors (id TEXT PRIMARY KEY, neighbor_counts TEXT)"
    )
    neighbor_rows = (
        (node_id, json.dumps({label: len(ids) for label, ids in labels.items()}))
        for node_id, labels in neighbors_by_label.items()
    )
    connection.executemany(
        "INSERT INTO neighbors (id, neighbor_counts) VALUES (?, ?)",
        neighbor_rows,
    )
    connection.commit()
    del neighbors_by_label

    # -------------------------
    # category_counts
    # -------------------------

    logging.info("Writing category_counts table...")
    connection.execute(
        "CREATE TABLE category_counts (category TEXT PRIMARY KEY, count INTEGER)"
    )
    nodes_by_label: Dict[str, int] = defaultdict(int)
    for node_id in nodes_dict:
        for label in expanded_labels_by_node.get(node_id, ()):
            nodes_by_label[label] += 1
    connection.executemany(
        "INSERT INTO category_counts (category, count) VALUES (?, ?)",
        nodes_by_label.items(),
    )
    connection.commit()

    del nodes_dict
    del expanded_labels_by_node

    connection.close()


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def _build_output_filename(output_dir: Path, tier0_build_date: str, schema_version: str) -> Path:
    return output_dir / f"tier0-info-for-overlay_v{schema_version}_tier0-{tier0_build_date}.sqlite"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the minimal tier0-info-for-overlay SQLite database "
                    "(edge_publications, neighbors, category_counts) from Tier0 JSONL files."
    )
    parser.add_argument("--nodes", type=Path, required=True,
                        help="Path to the conflated Tier0 nodes JSONL file.")
    parser.add_argument("--edges", type=Path, required=True,
                        help="Path to the conflated Tier0 edges JSONL file.")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Directory to write the resulting sqlite file into.")
    parser.add_argument("--tier0-build-date", required=True,
                        help="Tier0 build date stamp in YYYYMMDD form (used in the filename).")
    parser.add_argument("--schema-version", default="1.0",
                        help="Schema version stamp embedded in the filename. Default: 1.0")
    parser.add_argument(
        "--biolink-version",
        default=None,
        help="Biolink version for category-ancestor expansion. "
             "Defaults to the version ARAX is currently pinned to.",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    output_db = _build_output_filename(args.output_dir, args.tier0_build_date, args.schema_version)
    logging.info(f"Output: {output_db}")

    create_tier0_overlay_sqlite_db(args.nodes, args.edges, output_db, args.biolink_version)

    logging.info("Done.")


if __name__ == "__main__":
    main()
