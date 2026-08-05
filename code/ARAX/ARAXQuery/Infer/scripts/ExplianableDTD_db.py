"""
xDTD (Explainable Drug-Treat-Disease) Prediction Database Interface
=================================

SQLite interface for operating the pre-computed xDTD prediction results.

Tables:
  PREDICTION_SCORE_TABLE:
    drug_id, drug_name, disease_id, disease_name, tn_score, tp_score, unknown_score
  PATH_RESULT_TABLE:
    drug_id, drug_name, disease_id, disease_name, path, path_score

Author: Chunyu Ma
"""

import os
import sys
import argparse
import sqlite3
from typing import Optional, Union, List, Dict, Tuple

import pandas as pd
import numpy as np
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")  # ARAXQuery directory

# import internal modules
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration #noqa: E402
RTXConfig = RTXConfiguration()
from ARAX_database_manager import ARAXDatabaseManager #noqa: E402

# Default output directory for the database
_DEFAULT_OUTDIR = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])

# Column definitions for the two tables
_SCORE_COLUMNS = ["drug_id", "drug_name", "disease_id", "disease_name", "tn_score", "tp_score", "unknown_score"]
_PATH_COLUMNS = ["drug_id", "drug_name", "disease_id", "disease_name", "path", "path_score"]


class ExplainableDTD:
    """SQLite interface for the xDTD prediction score and path result database.

    Attributes:
        database_name: Filename of the SQLite database.
        outdir: Directory containing the database file.
        conn: Active sqlite3.Connection (set after connect()).
        is_connected: Whether a live connection exists.
    """

    # ──────────────────────────────────────────────────────────────────────
    #  Initialization
    # ──────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        path_to_score_results: Optional[str] = None,
        path_to_path_results: Optional[str] = None,
        database_name: Optional[str] = None,
        outdir: Optional[str] = _DEFAULT_OUTDIR,
        build: bool = False
    ):
        """
        Args:
            path_to_score_results: Directory of TSV score files (required when build=True).
            path_to_path_results: Directory of TSV path files (required when build=True).
            database_name: SQLite filename. Defaults to the RTXConfig value in run mode,
                           or "ExplainableDTD.db" in build mode.
            outdir: Directory for the database file.
            build: True = create/populate mode; False = read-only query mode.
        """
        self.is_connected = False
        self.conn: Optional[sqlite3.Connection] = None

        if build:
            self._init_build_mode(path_to_score_results, path_to_path_results, database_name, outdir)
        else:
            self._init_run_mode(database_name, outdir)

        self.connect()

    def _init_build_mode(self, score_dir, path_dir, database_name, outdir):
        """Validate input directories and set attributes for build mode."""
        self._validate_input_dir(score_dir, "path_to_score_results")
        self._validate_input_dir(path_dir, "path_to_path_results")
        self.path_to_score_results = score_dir
        self.path_to_path_results = path_dir
        self.database_name = database_name or "ExplainableDTD.db"
        self.outdir = outdir or "./"
        os.makedirs(self.outdir, exist_ok=True)

    def _init_run_mode(self, database_name, outdir):
        """Set attributes for query/run mode using RTXConfig defaults."""
        self.database_name = database_name or RTXConfig.explainable_dtd_db_path.split("/")[-1]
        self.outdir = outdir or "./"
        os.makedirs(self.outdir, exist_ok=True)

    @staticmethod
    def _validate_input_dir(path: Optional[str], param_name: str):
        """Raise ValueError if a required input directory is missing or empty."""
        if path is None:
            raise ValueError(f"'{param_name}' is required in build mode")
        if not os.path.exists(path) or len(os.listdir(path)) == 0:
            raise ValueError(f"'{param_name}' path '{path}' does not exist or is empty")

    # ──────────────────────────────────────────────────────────────────────
    #  Connection management
    # ──────────────────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Return the active connection, raising RuntimeError if not connected."""
        if self.conn is None:
            raise RuntimeError("Not connected to the database. Call connect() first.")
        return self.conn

    def connect(self) -> bool:
        """Open a connection to the SQLite database. Downloads via ARAXDatabaseManager if needed.

        Returns True on success.
        """
        if self.is_connected:
            return True

        db_path = os.path.join(self.outdir, self.database_name)

        if not os.path.exists(db_path):
            # In run mode the DB may need to be fetched by the ARAX database manager
            dbm = ARAXDatabaseManager()
            if dbm.check_versions():
                raise FileNotFoundError(
                    f"Database '{db_path}' not found and ARAX database manager reports missing databases"
                )

        self.conn = sqlite3.connect(db_path)
        self.is_connected = True
        print(f"INFO: Connected to database: {db_path}", flush=True)
        return True

    def disconnect(self):
        """Commit pending changes and close the database connection."""
        if not self.is_connected or self.conn is None:
            print("INFO: No active database connection to close", flush=True)
            return
        try:
            self.conn.commit()
            self.conn.close()
        except sqlite3.ProgrammingError:
            print("INFO: Database connection was already closed", flush=True)
        self.is_connected = False

    # ──────────────────────────────────────────────────────────────────────
    #  Build mode: table creation, population, and indexing
    # ──────────────────────────────────────────────────────────────────────

    def create_tables(self):
        """Drop and recreate the PREDICTION_SCORE_TABLE and PATH_RESULT_TABLE."""
        print(f"INFO: Creating tables in {self.database_name}", flush=True)
        conn = self._get_conn()
        conn.execute("DROP TABLE IF EXISTS PREDICTION_SCORE_TABLE")
        conn.execute("""
            CREATE TABLE PREDICTION_SCORE_TABLE (
                drug_id      VARCHAR(255),
                drug_name    VARCHAR(255),
                disease_id   VARCHAR(255),
                disease_name VARCHAR(255),
                tn_score     FLOAT,
                tp_score     FLOAT,
                unknown_score FLOAT
            )
        """)
        conn.execute("DROP TABLE IF EXISTS PATH_RESULT_TABLE")
        conn.execute("""
            CREATE TABLE PATH_RESULT_TABLE (
                drug_id      VARCHAR(255),
                drug_name    VARCHAR(255),
                disease_id   VARCHAR(255),
                disease_name VARCHAR(255),
                path         VARCHAR(255),
                path_score   FLOAT
            )
        """)
        conn.commit()
        print("INFO: Tables created successfully", flush=True)

    def populate_table(self):
        """Read TSV score/path files and batch-insert into the database.

        Uses WAL journal mode and disabled synchronous writes for bulk-load performance.
        Each file is expected to have a header row (skipped) with tab-separated fields.
        """
        BATCH_SIZE = 50000
        SCORE_INSERT = f"INSERT INTO PREDICTION_SCORE_TABLE({', '.join(_SCORE_COLUMNS)}) VALUES ({','.join('?' * len(_SCORE_COLUMNS))})"
        PATH_INSERT = f"INSERT INTO PATH_RESULT_TABLE({', '.join(_PATH_COLUMNS)}) VALUES ({','.join('?' * len(_PATH_COLUMNS))})"

        conn = self._get_conn()
        # Optimize for bulk loading
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA cache_size = -2000000")

        self._bulk_insert(self.path_to_score_results, SCORE_INSERT, BATCH_SIZE, desc="score_results")
        self._bulk_insert(self.path_to_path_results, PATH_INSERT, BATCH_SIZE, desc="path_results")

        # Restore safe synchronous mode after bulk load
        conn.execute("PRAGMA synchronous = NORMAL")
        print("INFO: Table population completed", flush=True)

    def _bulk_insert(self, directory: str, insert_sql: str, batch_size: int, desc: str = ""):
        """Read all TSV files in a directory and batch-insert rows into the database.

        Args:
            directory: Path to folder containing TSV files.
            insert_sql: Parameterized INSERT statement.
            batch_size: Number of rows per executemany() call.
            desc: Label for the tqdm progress bar.
        """
        conn = self._get_conn()
        files = os.listdir(directory)
        batch: list = []
        for file_name in tqdm(files, desc=desc):
            filepath = os.path.join(directory, file_name)
            with open(filepath, 'r') as f:
                next(f)  # skip header
                for line in f:
                    batch.append(tuple(line.strip().split("\t")))
                    if len(batch) >= batch_size:
                        conn.executemany(insert_sql, batch)
                        conn.commit()
                        batch = []
        if batch:
            conn.executemany(insert_sql, batch)
            conn.commit()

    def create_indexes(self):
        """Create B-tree indexes on drug_id, drug_name, disease_id, disease_name for both tables."""
        print("INFO: Creating indexes", flush=True)
        conn = self._get_conn()
        for table in ("PREDICTION_SCORE_TABLE", "PATH_RESULT_TABLE"):
            for col in ("drug_id", "drug_name", "disease_id", "disease_name"):
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col})")
        conn.commit()
        print("INFO: Index creation completed", flush=True)

    # ──────────────────────────────────────────────────────────────────────
    #  Run mode: query methods
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_curie_ids(curie_ids: Union[str, List[str], None]) -> Optional[List[str]]:
        """Ensure curie_ids is a deduplicated list, or None if empty/None."""
        if curie_ids is None:
            return None
        if isinstance(curie_ids, str):
            return [curie_ids]
        return list(set(curie_ids))

    @staticmethod
    def _build_where_clause(
        drug_ids: Optional[List[str]],
        disease_ids: Optional[List[str]],
    ) -> Tuple[str, list]:
        """Build a parameterized WHERE clause for drug/disease CURIE filtering.

        Returns (where_sql, params) where where_sql starts with ' WHERE ...' and
        params is the flat list of bind values.

        Examples:
            (' WHERE drug_id IN (?,?)', ['CHEMBL:1', 'CHEMBL:2'])
            (' WHERE drug_id IN (?) AND disease_id IN (?)', ['CHEMBL:1', 'MONDO:1'])
        """
        clauses = []
        params = []
        if drug_ids:
            clauses.append(f"drug_id IN ({','.join('?' * len(drug_ids))})")
            params.extend(drug_ids)
        if disease_ids:
            clauses.append(f"disease_id IN ({','.join('?' * len(disease_ids))})")
            params.extend(disease_ids)
        if not clauses:
            return "", []
        return " WHERE " + " AND ".join(clauses), params

    def get_score_table(
        self,
        drug_curie_ids: Union[str, List[str], None] = None,
        disease_curie_ids: Union[str, List[str], None] = None,
    ) -> pd.DataFrame:
        """Query the PREDICTION_SCORE_TABLE for matching drug/disease CURIEs.

        Args:
            drug_curie_ids: Single CURIE string or list, e.g. "CHEMBL.COMPOUND:CHEMBL55643" or ["CHEMBL.COMPOUND:CHEMBL55643","CHEBI:6908"].
            disease_curie_ids: Single CURIE string or list, e.g. "MONDO:0008753" or ["MONDO:0008753","MONDO:0005148","MONDO:0005155"].

        Returns:
            DataFrame with columns: drug_id, drug_name, disease_id, disease_name,
            tn_score, tp_score, unknown_score.  Empty DataFrame if no IDs provided.
        """
        drug_ids = self._normalize_curie_ids(drug_curie_ids)
        disease_ids = self._normalize_curie_ids(disease_curie_ids)

        if not drug_ids and not disease_ids:
            print("WARNING: get_score_table called with no drug or disease CURIEs", flush=True)
            return pd.DataFrame([], columns=_SCORE_COLUMNS)

        where_sql, params = self._build_where_clause(drug_ids, disease_ids)
        query = f"SELECT {', '.join(_SCORE_COLUMNS)} FROM PREDICTION_SCORE_TABLE{where_sql}"

        cursor = self._get_conn().cursor()
        cursor.execute(query, params)
        return pd.DataFrame(cursor.fetchall(), columns=_SCORE_COLUMNS)

    def get_top_path(
        self,
        drug_curie_ids: Union[str, List[str], None] = None,
        disease_curie_ids: Union[str, List[str], None] = None,
    ) -> Dict[Tuple[str, str], List[list]]:
        """Query the PATH_RESULT_TABLE for explanation paths matching drug/disease CURIEs.

        Args:
            drug_curie_ids: Single CURIE string or list, e.g. "CHEMBL.COMPOUND:CHEMBL55643" or ["CHEMBL.COMPOUND:CHEMBL55643","CHEBI:6908"].
            disease_curie_ids: Single CURIE string or list, e.g. "MONDO:0008753" or ["MONDO:0008753","MONDO:0005148","MONDO:0005155"].

        Returns:
            Dict mapping (drug_id, disease_id) -> list of [path_string, path_score].
            Empty dict if no IDs provided.
        """
        drug_ids = self._normalize_curie_ids(drug_curie_ids)
        disease_ids = self._normalize_curie_ids(disease_curie_ids)

        if not drug_ids and not disease_ids:
            print("WARNING: get_top_path called with no drug or disease CURIEs", flush=True)
            return {}

        where_sql, params = self._build_where_clause(drug_ids, disease_ids)
        query = f"SELECT drug_id, disease_id, path, path_score FROM PATH_RESULT_TABLE{where_sql}"

        cursor = self._get_conn().cursor()
        cursor.execute(query, params)

        top_paths: Dict[Tuple[str, str], List[list]] = {}
        for drug_id, disease_id, path, path_score in cursor.fetchall():
            top_paths.setdefault((drug_id, disease_id), []).append([path, path_score])
        return top_paths


# ══════════════════════════════════════════════════════════════════════════
#  CLI entry point
# ══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Build or test the ExplainableDTD database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--build', action="store_true", default=False,
                        help="(Re)build the database from scratch")
    parser.add_argument('--test', action="store_true", default=False,
                        help="Run test lookups against the database")
    parser.add_argument('--path_to_score_results', type=str, default=None,
                        help="Directory containing prediction score TSV files (required for --build)")
    parser.add_argument('--path_to_path_results', type=str, default=None,
                        help="Directory containing path result TSV files (required for --build)")
    parser.add_argument('--database_name', type=str, default="ExplainableDTD.db",
                        help="SQLite database filename")
    parser.add_argument('--outdir', type=str, default="./",
                        help="Output directory for the database file")
    args = parser.parse_args()

    if not args.build and not args.test:
        parser.print_help()
        sys.exit(2)

    if args.build:
        # Build mode: input directories are required
        if not args.path_to_score_results or not args.path_to_path_results:
            parser.error("--path_to_score_results and --path_to_path_results are required for --build")
        db = ExplainableDTD(
            path_to_score_results=args.path_to_score_results,
            path_to_path_results=args.path_to_path_results,
            database_name=args.database_name,
            outdir=args.outdir,
            build=True,
        )
        db.create_tables()
        db.populate_table()
        db.create_indexes()
    else:
        # Test-only mode: connect to existing database (run mode)
        db = ExplainableDTD(
            database_name=args.database_name,
            outdir=args.outdir,
            build=False,
        )

    if args.test:
        print("==== Testing: score table by disease ID ====", flush=True)
        print(db.get_score_table(disease_curie_ids='MONDO:0005148'))
        print("==== Testing: top paths by disease ID ====", flush=True)
        print(db.get_top_path(disease_curie_ids='MONDO:0005148'))


if __name__ == "__main__":
    main()
