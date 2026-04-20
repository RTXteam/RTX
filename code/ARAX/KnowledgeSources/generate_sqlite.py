#!/usr/bin/env python3

"""
Build the tier0 decoration SQLite database from conflated tier0 JSONL files.

This database is the rapid-lookup cache that ARAX_decorator.py reads at
query time to attach node/edge metadata (descriptions, publications,
supporting_text, knowledge_level, etc.) onto TRAPI results without
touching Neo4j or rescanning the full JSONL.

Preserves the structural features the decorator relies on:

    * Delimiter-encoded list fields
    * Deterministic triple key keyed on
        subject, predicate, qualifier tuple, object, primary_knowledge_source
    * node_pair column for NGD-style by-pair lookup
    * Unique triple index and node_id index

Primary knowledge source is derived from tier0's `sources` list (the
entry whose resource_role == "primary_knowledge_source"). This logic
must stay in lockstep with ARAXDecorator._get_tier0_edge_key or the
unique triple index won't match at lookup time.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set


TIER0_ARRAY_DELIMITER = "ǂ"


# ---------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------

def _convert_list_to_string_encoded_format(
    value: Optional[Iterable[str]]
) -> str:
    if not value:
        return ""

    cleaned: list[str] = []
    for item in value:
        if not item:
            continue
        if isinstance(item, str):
            cleaned.append(item)
        else:
            logging.warning("List contains non-str items; excluding them")

    return TIER0_ARRAY_DELIMITER.join(cleaned)


def _prep_for_sqlite(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, dict):
        return json.dumps(value)

    if isinstance(value, Iterable) and not isinstance(value, bytes):
        items = list(value)
        if not items:
            return ""
        if all(isinstance(item, str) for item in items):
            cleaned = [item for item in items if item]
            return TIER0_ARRAY_DELIMITER.join(cleaned) if cleaned else ""
        return json.dumps(items)

    return str(value)


def _extract_primary_knowledge_source(sources: Any) -> str:
    """Pull the primary_knowledge_source resource_id from tier0's `sources` list.

    Tier0 edges carry a structured `sources` field (list of dicts with
    `resource_id` and `resource_role`) rather than a flat
    `primary_knowledge_source` string. Return an empty string when no
    entry is marked as the primary source so the triple key stays
    deterministic.
    """
    if not sources or not isinstance(sources, list):
        return ""
    for source in sources:
        if isinstance(source, dict) and source.get("resource_role") == "primary_knowledge_source":
            return source.get("resource_id") or ""
    return ""


def _get_edge_key(
    subject: str,
    object: str,
    predicate: str,
    primary_knowledge_source: str,
    qualified_predicate: Optional[str],
    object_direction_qualifier: Optional[str],
    object_aspect_qualifier: Optional[str],
) -> str:

    qualified_portion = "--".join(
        [
            qualified_predicate or "",
            object_direction_qualifier or "",
            object_aspect_qualifier or "",
        ]
    )

    return "--".join(
        [
            subject,
            predicate,
            qualified_portion,
            object,
            primary_knowledge_source,
        ]
    )


# ---------------------------------------------------------------------
# Explicit property schema (tier0)
# ---------------------------------------------------------------------

NODE_PROPERTIES: Set[str] = {
    # Shared with KG2
    "id",
    "category",
    "description",
    "name",
    "synonym",
    "taxon",
    "in_taxon",
    # Tier0-only, surfaced for decoration
    "equivalent_identifiers",
    "information_content",
    "xref",
    "symbol",
    "full_name",
    "in_taxon_label",
    "inheritance",
    "chembl_availability_type",
    "chembl_black_box_warning",
    "chembl_natural_product",
    "chembl_prodrug",
}

EDGE_PROPERTIES: Set[str] = {
    # Shared with KG2
    "subject",
    "object",
    "id",
    "predicate",
    "agent_type",
    "knowledge_level",
    "qualified_predicate",
    "object_direction_qualifier",
    "object_aspect_qualifier",
    "publications",
    # Tier0-only: provenance and content
    "sources",
    "description",
    "supporting_text",
    "update_date",
    "negated",
    "original_subject",
    "original_predicate",
    "original_object",
    # Tier0-only: evidence / statistics worth surfacing
    "p_value",
    "adjusted_p_value",
    "evidence_count",
    # Tier0-only: clinical / regulatory
    "clinical_approval_status",
    "FDA_regulatory_approvals",
    # Tier0-only: qualifier family
    "qualifier",
    "anatomical_context_qualifier",
    "causal_mechanism_qualifier",
    "disease_context_qualifier",
    "frequency_qualifier",
    "onset_qualifier",
    "object_form_or_variant_qualifier",
    "sex_qualifier",
    "species_context_qualifier",
    "stage_qualifier",
    "subject_aspect_qualifier",
    "subject_direction_qualifier",
    "subject_form_or_variant_qualifier",
}


# ---------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------

def _iter_edge_rows(
    edges_path: Path,
    sqlite_edge_properties: list[str],
    progress_every: int = 1_000_000,
) -> Iterable[list[str]]:
    """Yield one sqlite row per edge, streaming from JSONL.

    The edges JSONL is tens of GB — materializing it into a dict or list
    pushes memory past what the machine has. This generator keeps memory
    O(1) per edge and lets `executemany` pull rows as it writes.
    """
    with edges_path.open() as f:
        for index, line in enumerate(f, start=1):
            edge = json.loads(line)

            primary_knowledge_source = _extract_primary_knowledge_source(edge.get("sources"))

            triple = _get_edge_key(
                subject=edge["subject"],
                object=edge["object"],
                predicate=edge["predicate"],
                primary_knowledge_source=primary_knowledge_source,
                qualified_predicate=edge.get("qualified_predicate"),
                object_direction_qualifier=edge.get("object_direction_qualifier"),
                object_aspect_qualifier=edge.get("object_aspect_qualifier"),
            )

            node_pair = f"{edge['subject']}--{edge['object']}"

            serialized_props = [
                _prep_for_sqlite(edge.get(prop))
                for prop in sqlite_edge_properties
            ]

            yield [triple, node_pair] + serialized_props

            if index % progress_every == 0:
                logging.info(f"  ... streamed {index:,} edges")


def create_tier0_sqlite_db(
    nodes_path: Path,
    edges_path: Path,
    output_db: Path,
) -> None:

    if output_db.exists():
        output_db.unlink()

    connection = sqlite3.connect(output_db)

    # -------------------------
    # Nodes (~1.7M rows: fits in memory fine)
    # -------------------------

    logging.info("Loading nodes into memory...")
    nodes_dict = load_jsonl_as_dict(nodes_path, "id")

    sqlite_node_properties = sorted(NODE_PROPERTIES)

    cols_with_types = ", ".join(f"{col} TEXT" for col in sqlite_node_properties)
    connection.execute(f"CREATE TABLE nodes ({cols_with_types})")

    question_marks = ", ".join("?" for _ in sqlite_node_properties)

    node_rows = (
        [
            _prep_for_sqlite(node.get(prop))
            for prop in sqlite_node_properties
        ]
        for node in nodes_dict.values()
    )

    logging.info(f"Inserting {len(nodes_dict):,} node rows...")
    connection.executemany(
        f"INSERT INTO nodes VALUES ({question_marks})",
        node_rows,
    )

    connection.execute("CREATE UNIQUE INDEX node_id_index ON nodes (id)")
    connection.commit()

    # Free the node dict before starting on edges so the full RAM budget
    # is available for the sqlite insert pipeline.
    del nodes_dict

    # -------------------------
    # Edges (~29M rows on tier0: streamed from disk)
    # -------------------------

    sqlite_edge_properties = sorted(EDGE_PROPERTIES)

    cols_with_types = ", ".join(f"{col} TEXT" for col in sqlite_edge_properties)

    connection.execute(
        f"CREATE TABLE edges (triple TEXT, node_pair TEXT, {cols_with_types})"
    )
    # Create the unique triple index up front so INSERT OR IGNORE has a
    # constraint to check against. Tier0 data contains a small number of
    # edges that serialize to the same triple key (same subject, predicate,
    # qualifiers, object, primary_knowledge_source); these would fail a
    # post-hoc CREATE UNIQUE INDEX. First-wins matches the 1:1 triple
    # lookup assumption on the decorator side.
    connection.execute("CREATE UNIQUE INDEX triple_index ON edges (triple)")

    question_marks = ", ".join("?" for _ in sqlite_edge_properties)

    logging.info("Streaming edges from JSONL into sqlite...")
    changes_before = connection.total_changes
    connection.executemany(
        f"INSERT OR IGNORE INTO edges (triple, node_pair, {', '.join(sqlite_edge_properties)}) "
        f"VALUES (?, ?, {question_marks})",
        _iter_edge_rows(edges_path, sqlite_edge_properties),
    )
    inserted = connection.total_changes - changes_before

    edge_count_row = connection.execute("SELECT COUNT(*) FROM edges").fetchone()
    final_count = edge_count_row[0] if edge_count_row else 0
    logging.info(f"Inserted {inserted:,} edges; final table size {final_count:,} rows")

    logging.info("Building node_pair_index...")
    connection.execute("CREATE INDEX node_pair_index ON edges (node_pair)")
    connection.commit()

    connection.close()


# ---------------------------------------------------------------------
# JSONL loader
# ---------------------------------------------------------------------

def load_jsonl_as_dict(path: Path, key_field: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    with path.open() as f:
        for line in f:
            obj = json.loads(line)
            result[obj[key_field]] = obj
    return result


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the tier0 decoration SQLite database from conflated JSONL files."
    )
    parser.add_argument("--nodes", type=Path, required=True)
    parser.add_argument("--edges", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    create_tier0_sqlite_db(args.nodes, args.edges, args.output)

    logging.info("Done.")


if __name__ == "__main__":
    main()
