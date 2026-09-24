"""
xDTD (Explainable Drug-Treat-Disease) Node/Edge Mapping Database Interface
================================

SQLite interface for mapping nodes and edges from Translator KG JSONL files
(nodes.jsonl, edges.jsonl) used by the xDTD prediction model.

Tables:
  NODE_MAPPING_TABLE:
    id, name, category (JSON list), extra_attributes (JSON dict of all
    remaining properties discovered in the JSONL)
  EDGE_MAPPING_TABLE:
    subject, predicate, object, id, category, extra_attributes (JSON dict of
    all remaining properties discovered in the JSONL)

Author: Chunyu Ma
"""

import os
import sys
import json
import argparse
import collections
import sqlite3
from typing import Optional, List, Dict
from tqdm import tqdm


# Named tuples returned by get_node_info / get_edge_info
# Only core fields are separate columns; all other node properties are stored
# in a single extra_attributes JSON column, so the schema adapts automatically
# when the upstream KG adds or removes node properties.
NodeInfo = collections.namedtuple('NodeInfo', [
    'id', 'name', 'category', 'extra_attributes'
])

EdgeInfo = collections.namedtuple('EdgeInfo', [
    'subject', 'predicate', 'object', 'id', 'category', 'extra_attributes'
])


class xDTDMappingDB:
    """SQLite interface for the xDTD node/edge mapping database.

    Attributes:
        database_name: Filename of the SQLite database.
        conn: Active sqlite3.Connection (set after construction).
    """

    def __init__(self, database_name: str = 'ExplainableDTD.db', outdir: Optional[str] = None,
                 mode: str = 'build', db_loc: Optional[str] = None):
        """
        Args:
            database_name: Database filename (default: ExplainableDTD.db).
            outdir: Output directory for build mode (default: ./).
            mode: 'build' to create from scratch, 'run' to open existing.
            db_loc: Directory of an existing database (required for mode='run').
        """
        self.database_name = database_name

        if mode == 'build':
            outdir = outdir or './'
            os.makedirs(outdir, exist_ok=True)
            db_path = os.path.join(outdir, self.database_name)
        elif mode == 'run':
            if db_loc is None:
                raise ValueError("db_loc is required for mode='run'")
            db_path = os.path.join(db_loc, database_name)
        else:
            raise ValueError(f"Unknown mode '{mode}'. Use 'build' or 'run'.")

        self.conn = sqlite3.connect(db_path)
        print(f"INFO: Connected to database: {db_path}", flush=True)

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.commit()
                self.conn.close()
                print("INFO: Disconnected from database", flush=True)
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────
    #  Build mode: table creation, population, and indexing
    # ──────────────────────────────────────────────────────────────────────

    def create_tables(self):
        """Drop and recreate the NODE_MAPPING_TABLE and EDGE_MAPPING_TABLE."""
        print(f"INFO: Creating tables in {self.database_name}", flush=True)

        self.conn.execute("DROP TABLE IF EXISTS NODE_MAPPING_TABLE")
        self.conn.execute("""
            CREATE TABLE NODE_MAPPING_TABLE (
                id TEXT NOT NULL,
                name TEXT,
                category TEXT,
                extra_attributes TEXT
            )
        """)

        self.conn.execute("DROP TABLE IF EXISTS EDGE_MAPPING_TABLE")
        self.conn.execute("""
            CREATE TABLE EDGE_MAPPING_TABLE (
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                id TEXT,
                category TEXT,
                extra_attributes TEXT
            )
        """)
        self.conn.commit()
        print("INFO: Tables created successfully", flush=True)

    def populate_tables(self, nodes_jsonl_path: str, edges_jsonl_path: str):
        """Read JSONL node/edge files and batch-insert into the database.

        Uses WAL journal mode and disabled synchronous writes for bulk-load performance.
        """
        BATCH_SIZE = 50000
        NODE_INSERT = "INSERT INTO NODE_MAPPING_TABLE VALUES (?,?,?,?)"
        EDGE_INSERT = "INSERT INTO EDGE_MAPPING_TABLE VALUES (?,?,?,?,?,?)"

        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = OFF")
        self.conn.execute("PRAGMA cache_size = -2000000")

        self._insert_nodes(nodes_jsonl_path, NODE_INSERT, BATCH_SIZE)
        self._insert_edges(edges_jsonl_path, EDGE_INSERT, BATCH_SIZE)

        self.conn.execute("PRAGMA synchronous = NORMAL")
        print("INFO: Table population completed", flush=True)

    _NODE_CORE_KEYS = frozenset({'id', 'name', 'category'})

    def _insert_nodes(self, jsonl_path: str, insert_sql: str, batch_size: int):
        """Parse nodes.jsonl and batch-insert rows.

        Core fields (id, name, category) become dedicated columns.  Every
        other key found in the JSON line is collected into an
        ``extra_attributes`` JSON column, so the schema automatically adapts
        when upstream adds or removes node properties.  Lists, dicts, and
        other non-scalar values are preserved natively in the JSON blob.
        """
        batch: list = []
        count = 0
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="Inserting nodes"):
                d = json.loads(line)
                extra = {k: v for k, v in d.items() if k not in self._NODE_CORE_KEYS}
                row = (
                    d['id'],
                    d.get('name'),
                    json.dumps(d['category']) if 'category' in d else None,
                    json.dumps(extra) if extra else None,
                )
                batch.append(row)
                count += 1
                if len(batch) >= batch_size:
                    self.conn.executemany(insert_sql, batch)
                    self.conn.commit()
                    batch = []
        if batch:
            self.conn.executemany(insert_sql, batch)
            self.conn.commit()
        print(f"INFO: Inserted {count} rows into NODE_MAPPING_TABLE", flush=True)

    _EDGE_CORE_KEYS = frozenset({'subject', 'predicate', 'object', 'id', 'category'})

    def _insert_edges(self, jsonl_path: str, insert_sql: str, batch_size: int):
        """Parse edges.jsonl and batch-insert rows.

        Core fields (subject, predicate, object, id, category) become dedicated
        columns.  Every other key found in the JSON line is collected into an
        ``extra_attributes`` JSON column, so the schema automatically adapts
        when upstream adds or removes edge properties.
        """
        batch: list = []
        count = 0
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="Inserting edges"):
                d = json.loads(line)
                extra = {k: v for k, v in d.items() if k not in self._EDGE_CORE_KEYS}
                row = (
                    d['subject'],
                    d['predicate'],
                    d['object'],
                    d.get('id'),
                    json.dumps(d['category']) if 'category' in d else None,
                    json.dumps(extra) if extra else None,
                )
                batch.append(row)
                count += 1
                if len(batch) >= batch_size:
                    self.conn.executemany(insert_sql, batch)
                    self.conn.commit()
                    batch = []
        if batch:
            self.conn.executemany(insert_sql, batch)
            self.conn.commit()
        print(f"INFO: Inserted {count} rows into EDGE_MAPPING_TABLE", flush=True)

    def create_indexes(self):
        """Create indexes for efficient node/edge lookups."""
        print("INFO: Creating indexes", flush=True)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_NODE_MAPPING_TABLE_id ON NODE_MAPPING_TABLE(id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_NODE_MAPPING_TABLE_name ON NODE_MAPPING_TABLE(name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_EDGE_MAPPING_TABLE_triple ON EDGE_MAPPING_TABLE(subject, predicate, object)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_EDGE_MAPPING_TABLE_subject ON EDGE_MAPPING_TABLE(subject)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_EDGE_MAPPING_TABLE_object ON EDGE_MAPPING_TABLE(object)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_EDGE_MAPPING_TABLE_predicate ON EDGE_MAPPING_TABLE(predicate)")
        self.conn.commit()
        print("INFO: Index creation completed", flush=True)

    # ──────────────────────────────────────────────────────────────────────
    #  Run mode: query methods
    # ──────────────────────────────────────────────────────────────────────

    def get_node_info(self, node_id: Optional[str] = None, node_name: Optional[str] = None) -> Optional[NodeInfo]:
        """Look up a node by ID or name.

        Args:
            node_id: Exact node CURIE, e.g. "CHEBI:10".
            node_name: Case-insensitive name match, e.g. "Nalidixic acid".
        Returns:
            NodeInfo namedtuple, or None if not found.
        """
        cursor = self.conn.cursor()
        if node_id is not None:
            cursor.execute("SELECT * FROM NODE_MAPPING_TABLE WHERE id = ?", (node_id,))
        elif node_name is not None:
            cursor.execute("SELECT * FROM NODE_MAPPING_TABLE WHERE name = ? COLLATE NOCASE", (node_name,))
        else:
            return None
        result = cursor.fetchone()
        if not result:
            return None
        # `category` is stored as a JSON-encoded list string by _insert_nodes;
        # decode it back to a list so callers (Node.categories expects a list)
        # don't have to handle the encoding themselves.
        values = list(result)
        cat_idx = NodeInfo._fields.index('category')
        if values[cat_idx]:
            try:
                values[cat_idx] = json.loads(values[cat_idx])
            except (json.JSONDecodeError, TypeError):
                pass
        return NodeInfo._make(values)

    def get_edge_info(self, subject: Optional[str] = None, predicate: Optional[str] = None,
                      object_id: Optional[str] = None, triple_id: Optional[tuple] = None) -> List[EdgeInfo]:
        """Look up edges by (subject, predicate, object) triple.

        Supports both explicit arguments and a legacy triple_id=(s, p, o) tuple
        for backward compatibility with infer_utilities.py.

        Args:
            subject: Subject node CURIE.
            predicate: Biolink predicate string.
            object_id: Object node CURIE.
            triple_id: Legacy (subject, predicate, object) tuple.
        Returns:
            List of EdgeInfo namedtuples. Empty list if not found.
        """
        cursor = self.conn.cursor()

        if triple_id is not None and isinstance(triple_id, tuple):
            subject, predicate, object_id = triple_id

        if subject is None or predicate is None or object_id is None:
            return []

        # SELF_LOOP_RELATION is a synthetic edge used by the xDTD model for flexible path lengths
        if predicate == 'SELF_LOOP_RELATION':
            return [EdgeInfo._make((
                subject, predicate, object_id,
                None, None, None
            ))]

        cursor.execute(
            "SELECT * FROM EDGE_MAPPING_TABLE WHERE subject = ? AND predicate = ? AND object = ?",
            (subject, predicate, object_id)
        )
        return [self._make_edge_info(record) for record in cursor.fetchall()]

    # ──────────────────────────────────────────────────────────────────────
    #  Batch query methods (performance optimization for xDTD path lookups)
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _decode_category(raw_value):
        """Decode a JSON-encoded category string back to a list."""
        if raw_value is None:
            return None
        try:
            return json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            return raw_value

    _EDGE_CAT_IDX = EdgeInfo._fields.index('category')

    def _make_edge_info(self, row: tuple) -> EdgeInfo:
        """Construct an EdgeInfo from a raw SQL row, decoding the category JSON."""
        values = list(row)
        values[self._EDGE_CAT_IDX] = self._decode_category(values[self._EDGE_CAT_IDX])
        return EdgeInfo._make(values)

    def get_nodes_info_batch(self, node_ids: List[str]) -> Dict[str, NodeInfo]:
        """Look up multiple nodes by ID in a single query.

        Args:
            node_ids: List of node CURIEs to look up.
        Returns:
            Dict mapping node_id -> NodeInfo. Missing IDs are omitted.
        """
        if not node_ids:
            return {}

        unique_ids = list(set(node_ids))
        result_map: Dict[str, NodeInfo] = {}
        cat_idx = NodeInfo._fields.index('category')

        CHUNK = 500
        cursor = self.conn.cursor()
        for start in range(0, len(unique_ids), CHUNK):
            chunk = unique_ids[start:start + CHUNK]
            placeholders = ','.join('?' * len(chunk))
            cursor.execute(
                f"SELECT * FROM NODE_MAPPING_TABLE WHERE id IN ({placeholders})", chunk
            )
            for row in cursor.fetchall():
                values = list(row)
                values[cat_idx] = self._decode_category(values[cat_idx])
                info = NodeInfo._make(values)
                result_map[info.id] = info

        return result_map

    def get_edges_info_batch(self, triples: List[tuple]) -> Dict[tuple, List[EdgeInfo]]:
        """Look up multiple edges by (subject, predicate, object) triples in a single query.

        Args:
            triples: List of (subject, predicate, object) tuples.
        Returns:
            Dict mapping (subject, predicate, object) -> list of EdgeInfo.
            Missing triples map to an empty list.
        """
        if not triples:
            return {}

        unique_triples = list(set(triples))
        result_map: Dict[tuple, List[EdgeInfo]] = {t: [] for t in unique_triples}

        db_triples = []
        for t in unique_triples:
            if t[1] == 'SELF_LOOP_RELATION':
                result_map[t] = [EdgeInfo._make((
                    t[0], t[1], t[2],
                    None, None, None
                ))]
            else:
                db_triples.append(t)

        if not db_triples:
            return result_map

        CHUNK = 200
        cursor = self.conn.cursor()
        for start in range(0, len(db_triples), CHUNK):
            chunk = db_triples[start:start + CHUNK]
            parts = []
            params = []
            for s, p, o in chunk:
                parts.append("SELECT * FROM EDGE_MAPPING_TABLE WHERE subject = ? AND predicate = ? AND object = ?")
                params.extend([s, p, o])
            sql = " UNION ALL ".join(parts)
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                edge = self._make_edge_info(row)
                key = (edge.subject, edge.predicate, edge.object)
                result_map[key].append(edge)

        return result_map


# ══════════════════════════════════════════════════════════════════════════
#  CLI entry point
# ══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Build or query the xDTD Mapping Database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--build', action="store_true", default=False,
                        help="Build the database from JSONL files")
    parser.add_argument('--test', action="store_true", default=False,
                        help="Run a quick test of the database")
    parser.add_argument('--nodes_jsonl', type=str, default=None,
                        help="Path to nodes.jsonl file (required for --build)")
    parser.add_argument('--edges_jsonl', type=str, default=None,
                        help="Path to edges.jsonl file (required for --build)")
    parser.add_argument('--database_name', type=str, default="xdtd_mapping.db",
                        help="Name of the database file")
    parser.add_argument('--outdir', type=str, default=".",
                        help="Path to the output directory")
    args = parser.parse_args()

    if not args.build and not args.test:
        parser.print_help()
        sys.exit(2)

    if args.build:
        if not args.nodes_jsonl or not args.edges_jsonl:
            parser.error("--nodes_jsonl and --edges_jsonl are required for --build")
        db = xDTDMappingDB(database_name=args.database_name, outdir=args.outdir, mode='build')
        db.create_tables()
        db.populate_tables(args.nodes_jsonl, args.edges_jsonl)
        db.create_indexes()

    if args.test:
        db = xDTDMappingDB(database_name=args.database_name, mode='run', db_loc=args.outdir)
        print("==== Testing node lookup ====", flush=True)
        print(db.get_node_info(node_id='CHEBI:10'), flush=True)
        print(db.get_node_info(node_name='Nalidixic acid'), flush=True)
        print("==== Testing edge lookup (new API) ====", flush=True)
        print(db.get_edge_info(subject='NCBIGene:18993', predicate='biolink:expressed_in', object_id='UBERON:0001016'), flush=True)
        print("==== Testing edge lookup (legacy triple_id) ====", flush=True)
        print(db.get_edge_info(triple_id=('NCBIGene:18993', 'biolink:expressed_in', 'UBERON:0001016')), flush=True)


if __name__ == "__main__":
    main()
