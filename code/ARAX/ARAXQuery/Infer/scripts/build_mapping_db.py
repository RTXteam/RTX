"""
xDTD (Explainable Drug-Treat-Disease) Node/Edge Mapping Database Interface
================================

SQLite interface for mapping nodes and edges from Translator KG JSONL files
(nodes.jsonl, edges.jsonl) used by the xDTD prediction model.

Tables:
  NODE_MAPPING_TABLE:
    id, name, category (JSON list), equivalent_identifiers, description,
    synonym, xref, chembl_natural_product, chembl_availability_type, chembl_black_box_warning
  EDGE_MAPPING_TABLE:
    subject, predicate, object, id, category, qualifier, publications, sources,
    resource_id (pipe-delimited), resource_role (pipe-delimited), knowledge_level,
    agent_type, stage_qualifier, original_subject, original_object

Author: Chunyu Ma
"""

import os
import sys
import json
import argparse
import collections
import sqlite3
from typing import Optional, List
from tqdm import tqdm


# Named tuples returned by get_node_info / get_edge_info
NodeInfo = collections.namedtuple('NodeInfo', [
    'id', 'name', 'category', 'equivalent_identifiers', 'description',
    'synonym', 'xref', 'chembl_natural_product', 'chembl_availability_type',
    'chembl_black_box_warning'
])

EdgeInfo = collections.namedtuple('EdgeInfo', [
    'subject', 'predicate', 'object', 'id', 'category', 'qualifier',
    'publications', 'sources', 'resource_id', 'resource_role',
    'knowledge_level', 'agent_type', 'stage_qualifier',
    'original_subject', 'original_object'
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
                equivalent_identifiers TEXT,
                description TEXT,
                synonym TEXT,
                xref TEXT,
                chembl_natural_product TEXT,
                chembl_availability_type TEXT,
                chembl_black_box_warning TEXT
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
                qualifier TEXT,
                publications TEXT,
                sources TEXT,
                resource_id TEXT,
                resource_role TEXT,
                knowledge_level TEXT,
                agent_type TEXT,
                stage_qualifier TEXT,
                original_subject TEXT,
                original_object TEXT
            )
        """)
        self.conn.commit()
        print("INFO: Tables created successfully", flush=True)

    def populate_tables(self, nodes_jsonl_path: str, edges_jsonl_path: str):
        """Read JSONL node/edge files and batch-insert into the database.

        Uses WAL journal mode and disabled synchronous writes for bulk-load performance.
        """
        BATCH_SIZE = 50000
        NODE_INSERT = "INSERT INTO NODE_MAPPING_TABLE VALUES (?,?,?,?,?,?,?,?,?,?)"
        EDGE_INSERT = "INSERT INTO EDGE_MAPPING_TABLE VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"

        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = OFF")
        self.conn.execute("PRAGMA cache_size = -2000000")

        self._insert_nodes(nodes_jsonl_path, NODE_INSERT, BATCH_SIZE)
        self._insert_edges(edges_jsonl_path, EDGE_INSERT, BATCH_SIZE)

        self.conn.execute("PRAGMA synchronous = NORMAL")
        print("INFO: Table population completed", flush=True)

    def _insert_nodes(self, jsonl_path: str, insert_sql: str, batch_size: int):
        """Parse nodes.jsonl and batch-insert rows."""
        batch: list = []
        count = 0
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="Inserting nodes"):
                d = json.loads(line)
                row = (
                    d['id'],
                    d.get('name'),
                    json.dumps(d['category']) if 'category' in d else None,
                    json.dumps(d['equivalent_identifiers']) if 'equivalent_identifiers' in d else None,
                    d.get('description'),
                    json.dumps(d['synonym']) if 'synonym' in d else None,
                    json.dumps(d['xref']) if 'xref' in d else None,
                    str(d['chembl_natural_product']) if 'chembl_natural_product' in d else None,
                    d.get('chembl_availability_type'),
                    d.get('chembl_black_box_warning'),
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

    def _insert_edges(self, jsonl_path: str, insert_sql: str, batch_size: int):
        """Parse edges.jsonl and batch-insert rows.

        Flattens the 'sources' array into pipe-delimited resource_id and resource_role strings
        for efficient querying of primary knowledge sources.
        """
        batch: list = []
        count = 0
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="Inserting edges"):
                d = json.loads(line)
                sources = d.get('sources', [])
                resource_ids = '|'.join(s.get('resource_id', '') for s in sources)
                resource_roles = '|'.join(s.get('resource_role', '') for s in sources)
                row = (
                    d['subject'],
                    d['predicate'],
                    d['object'],
                    d.get('id'),
                    json.dumps(d['category']) if 'category' in d else None,
                    d.get('qualifier'),
                    json.dumps(d['publications']) if 'publications' in d else None,
                    json.dumps(sources) if sources else None,
                    resource_ids or None,
                    resource_roles or None,
                    d.get('knowledge_level'),
                    d.get('agent_type'),
                    d.get('stage_qualifier'),
                    d.get('original_subject'),
                    d.get('original_object'),
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
        return NodeInfo._make(result) if result else None

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
                None, None, None, None, None, None, None, None, None, None, None, None
            ))]

        cursor.execute(
            "SELECT * FROM EDGE_MAPPING_TABLE WHERE subject = ? AND predicate = ? AND object = ?",
            (subject, predicate, object_id)
        )
        return [EdgeInfo._make(record) for record in cursor.fetchall()]


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
