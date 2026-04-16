#!/usr/bin/env python3
"""
Builds a SQLite database that maps canonicalized curies to PubMed articles
they appear in.

Uses local_babel for name -> CURIE resolution (no external API calls).
"""
import argparse
import gzip
import json
import logging
import multiprocessing
import os
import pathlib
import sqlite3
import subprocess
import sys
import time

# Lazy imports — these are checked by --test and loaded at build time.
etree = None
process_names = None
connect_to_db_read_only = None
map_name_to_curie = None


def _load_dependencies():
    global etree, process_names, connect_to_db_read_only, map_name_to_curie
    from lxml import etree as _etree
    from extraction_script import process_names as _process_names
    from stitch_proj.local_babel import (
        connect_to_db_read_only as _connect,
        map_name_to_curie as _map,
    )
    etree = _etree
    process_names = _process_names
    connect_to_db_read_only = _connect
    map_name_to_curie = _map

DEFAULT_PUBMED_DIR = os.environ.get("NGD_PUBMED_DIR")
DEFAULT_BABEL_DB = os.environ.get("NGD_BABEL_DB")
DEFAULT_OUTPUT_DIR = os.environ.get(
    "NGD_OUTPUT_DIR",
    os.path.dirname(os.path.abspath(__file__)),
)


# ---------------------------------------------------------------------------
# PubMed XML parse worker
# ---------------------------------------------------------------------------
def _parse_one_pubmed_file(file_path):
    rows = []
    try:
        with gzip.open(file_path, "rb") as gz_file:
            context = etree.iterparse(gz_file, events=("end",), tag="PubmedArticle")
            for _, article in context:
                pmid_elements = article.xpath(".//MedlineCitation/PMID/text()")
                if not pmid_elements:
                    article.clear()
                    continue

                pmid_curie = f"PMID:{pmid_elements[0]}"
                mc = ".//MedlineCitation"

                # MeSH qualifiers (subheadings like "metabolism", "pharmacology")
                # are modifiers on a parent descriptor, not standalone concepts —
                # harvesting them as top-level names produces meaningless
                # co-occurrence signal. Only DescriptorName is pulled from MeSH.
                all_concept_names = (
                    article.xpath(f"{mc}/MeshHeadingList/MeshHeading/DescriptorName/text()") +
                    article.xpath(f"{mc}/ChemicalList/Chemical/NameOfSubstance/text()") +
                    article.xpath(f"{mc}/GeneSymbolList/GeneSymbol/text()") +
                    article.xpath(f"{mc}/KeywordList/Keyword/text()")
                )

                for concept_name in process_names(all_concept_names):
                    rows.append((concept_name, pmid_curie))

                article.clear()
                while article.getprevious() is not None:
                    del article.getparent()[0]

            del context

    except Exception as e:
        return file_path, rows, str(e)

    return file_path, rows, None


# ---------------------------------------------------------------------------
# CURIE resolution worker (one Babel connection per process)
# ---------------------------------------------------------------------------
# Targeted overrides for known Babel name-resolution collisions. Consulted
# before map_name_to_curie and keyed on the lowercased raw concept name.
#
# Entries here represent cases where Babel's case-insensitive name index
# maps a term to the wrong CURIE because of an unrelated identifier that
# shares the string (e.g. "Male" → NCBIGene:69652262 "malE", the E. coli
# maltose transporter). Add a new entry when the accountability trace in
# audit_ngd_db.py surfaces another collision.
NAME_CURIE_OVERRIDES = {
    "male": "MESH:D008297",  # MeSH "Male" sex descriptor (not malE gene)
}


_worker_babel_conn = None


def _init_resolver_worker(babel_db_path):
    global _worker_babel_conn
    _worker_babel_conn = connect_to_db_read_only(babel_db_path)


def _resolve_one(item):
    concept_name, pmids_json = item

    override = NAME_CURIE_OVERRIDES.get(concept_name.lower())
    if override is not None:
        curie = override
    else:
        try:
            result = map_name_to_curie(_worker_babel_conn, concept_name)
        except Exception as e:
            return None, concept_name, None, str(e)

        if not result:
            return None, concept_name, None, None

        curie = result[0]

    try:
        pmids = json.loads(pmids_json)
    except Exception as e:
        return None, concept_name, None, f"bad pmids json: {e}"

    nums = []
    for pmid in pmids:
        if isinstance(pmid, str) and pmid.startswith("PMID:"):
            try:
                nums.append(int(pmid.split(":", 1)[1]))
            except ValueError:
                pass
    return curie, None, nums, None


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
class NGDDatabaseBuilder:
    def __init__(self, pubmed_dir, babel_db_path, output_dir, skip_download=False):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s',
            handlers=[logging.FileHandler(os.path.join(output_dir, "ngdbuild.log")),
                      logging.StreamHandler()],
        )

        self.pubmed_directory_path = pubmed_dir
        self.babel_db_path = babel_db_path
        self.output_dir = output_dir

        self.conceptname_to_pmids_db_path = os.path.join(
            output_dir, "conceptname_to_pmids.sqlite"
        )
        self.curie_to_pmids_db_path = os.path.join(
            output_dir, "curie_to_pmids.sqlite"
        )

        self.status = 'OK'
        self.skip_download = skip_download

    def build_ngd_database(self, do_full_build: bool):
        if do_full_build:
            self.build_conceptname_to_pmids_db()
        else:
            concept_db = pathlib.Path(self.conceptname_to_pmids_db_path)
            if not concept_db.exists():
                logging.error("Missing conceptname_to_pmids DB at %s",
                              self.conceptname_to_pmids_db_path)
                self.status = "ERROR"

        if self.status == 'OK':
            self.build_curie_to_pmids_db()

    # ----- stage 1: conceptname_to_pmids -----
    def build_conceptname_to_pmids_db(self):
        logging.info("Building conceptname_to_pmids...")
        start = time.time()

        if not self.skip_download:
            os.makedirs(self.pubmed_directory_path, exist_ok=True)
            # -N: only download files newer than local copies (incremental).
            # -nv: less noisy. Keeps existing files intact.
            subprocess.check_call([
                "wget", "-r", "-N", "-nv",
                "ftp://ftp.ncbi.nlm.nih.gov/pubmed",
                "-P", self.pubmed_directory_path,
            ])

        if os.path.exists(self.conceptname_to_pmids_db_path):
            os.remove(self.conceptname_to_pmids_db_path)

        conn = sqlite3.connect(self.conceptname_to_pmids_db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("CREATE TABLE staging (concept_name TEXT, pmid TEXT)")
        conn.commit()

        num_workers = max(1, (multiprocessing.cpu_count() or 2) - 1)
        logging.info("Parsing PubMed XML with %d workers", num_workers)

        total_files = 0
        total_errors = 0

        for sub_dir in ["baseline", "updatefiles"]:
            xml_dir = f"{self.pubmed_directory_path}/ftp.ncbi.nlm.nih.gov/pubmed/{sub_dir}"

            if not os.path.isdir(xml_dir):
                logging.warning("Missing PubMed subdir: %s", xml_dir)
                continue

            files = [f for f in os.listdir(xml_dir)
                     if f.lower().startswith("pubmed") and f.endswith(".xml.gz")]
            file_paths = [f"{xml_dir}/{f}" for f in files]
            logging.info("  %s: %d files", sub_dir, len(file_paths))

            with multiprocessing.Pool(num_workers) as pool:
                for file_path, rows, err in pool.imap_unordered(
                    _parse_one_pubmed_file, file_paths
                ):
                    total_files += 1
                    if err:
                        total_errors += 1
                        logging.error("Parse failed for %s: %s", file_path, err)
                    if rows:
                        # chunked insert to bound memory
                        for i in range(0, len(rows), 100_000):
                            cursor.executemany(
                                "INSERT INTO staging VALUES (?, ?)",
                                rows[i:i + 100_000],
                            )
                    if total_files % 50 == 0:
                        conn.commit()
                        logging.info("  parsed %d files (%d errors so far)",
                                     total_files, total_errors)

            conn.commit()

        logging.info("Indexing staging table...")
        cursor.execute("CREATE INDEX idx_staging_name ON staging(concept_name)")
        conn.commit()

        cursor.execute("""
            CREATE TABLE conceptname_to_pmids (
                concept_name TEXT PRIMARY KEY,
                pmids TEXT
            )
        """)

        # Stream-aggregate in Python and emit real JSON.
        logging.info("Aggregating concept_name -> pmids...")
        agg_cursor = conn.cursor()
        rows_iter = agg_cursor.execute(
            "SELECT concept_name, pmid FROM staging "
            "ORDER BY concept_name"
        )

        write_cursor = conn.cursor()
        current_name = None
        current_pmids = set()
        n_written = 0

        def flush(name, pmids):
            nonlocal n_written
            if name is None:
                return
            write_cursor.execute(
                "INSERT INTO conceptname_to_pmids VALUES (?, ?)",
                (name, json.dumps(sorted(pmids))),
            )
            n_written += 1
            if n_written % 200_000 == 0:
                conn.commit()
                logging.info("  wrote %d concepts", n_written)

        for name, pmid in rows_iter:
            if name != current_name:
                flush(current_name, current_pmids)
                current_name = name
                current_pmids = set()
            current_pmids.add(pmid)
        flush(current_name, current_pmids)

        conn.commit()
        cursor.execute("DROP TABLE staging")
        conn.commit()
        conn.close()

        logging.info("Done concept DB in %.2f min (%d files, %d errors, %d concepts)",
                     (time.time() - start) / 60, total_files, total_errors, n_written)

    # ----- stage 2: curie_to_pmids -----
    def build_curie_to_pmids_db(self):
        logging.info("Building curie_to_pmids...")
        start = time.time()

        if os.path.exists(self.curie_to_pmids_db_path):
            os.remove(self.curie_to_pmids_db_path)

        out_conn = sqlite3.connect(self.curie_to_pmids_db_path)
        out_cursor = out_conn.cursor()
        out_cursor.execute("PRAGMA journal_mode=WAL")
        out_cursor.execute("PRAGMA synchronous=NORMAL")
        out_cursor.execute("CREATE TABLE staging (curie TEXT, pmid INTEGER)")
        out_conn.commit()

        self._add_pmids_from_pubmed_scrape(out_cursor, out_conn)

        if self.status != 'OK':
            return

        logging.info("Indexing staging table...")
        out_cursor.execute("CREATE INDEX idx_staging_curie ON staging(curie)")
        out_conn.commit()

        out_cursor.execute("""
            CREATE TABLE curie_to_pmids (
                curie TEXT PRIMARY KEY,
                pmids TEXT
            )
        """)

        logging.info("Aggregating curie -> pmids...")
        agg_cursor = out_conn.cursor()
        rows_iter = agg_cursor.execute(
            "SELECT curie, pmid FROM staging ORDER BY curie"
        )

        write_cursor = out_conn.cursor()
        current_curie = None
        current_pmids = set()
        n_written = 0

        for curie, pmid in rows_iter:
            if curie != current_curie:
                if current_curie is not None:
                    write_cursor.execute(
                        "INSERT INTO curie_to_pmids VALUES (?, ?)",
                        (current_curie, json.dumps(sorted(current_pmids))),
                    )
                    n_written += 1
                current_curie = curie
                current_pmids = set()
            current_pmids.add(pmid)
        if current_curie is not None:
            write_cursor.execute(
                "INSERT INTO curie_to_pmids VALUES (?, ?)",
                (current_curie, json.dumps(sorted(current_pmids))),
            )
            n_written += 1

        out_cursor.execute("DROP TABLE staging")
        out_conn.commit()
        out_conn.close()

        logging.info("Done curie DB in %.2f min (%d curies)",
                     (time.time() - start) / 60, n_written)

    def _add_pmids_from_pubmed_scrape(self, out_cursor, out_conn):
        logging.info("Resolving concept names using local_babel (parallel)...")

        # check_same_thread=False: pool.imap_unordered consumes row_iter()
        # from a Pool helper thread, not the main thread.
        in_conn = sqlite3.connect(
            self.conceptname_to_pmids_db_path, check_same_thread=False
        )
        in_cursor = in_conn.cursor()

        total_recognized = 0
        total_unrecognized = 0
        total_processed = 0
        total_errors = 0
        unrecognized = set()
        staging_rows = []
        BATCH_FLUSH = 500_000
        LOG_EVERY = 100_000

        num_workers = max(1, (multiprocessing.cpu_count() or 2) - 1)
        logging.info("Resolver pool: %d workers", num_workers)

        start = time.perf_counter()

        def row_iter():
            for row in in_cursor.execute(
                "SELECT concept_name, pmids FROM conceptname_to_pmids"
            ):
                yield row

        with multiprocessing.Pool(
            num_workers,
            initializer=_init_resolver_worker,
            initargs=(self.babel_db_path,),
        ) as pool:
            for curie, unrec_name, pmid_nums, err in pool.imap_unordered(
                _resolve_one, row_iter(), chunksize=200
            ):
                total_processed += 1
                if err:
                    total_errors += 1
                    if total_errors <= 20:
                        logging.warning("resolve error: %s", err)
                    continue

                if curie is None:
                    total_unrecognized += 1
                    if unrec_name is not None:
                        unrecognized.add(unrec_name)
                else:
                    total_recognized += 1
                    for n in pmid_nums:
                        staging_rows.append((curie, n))

                if len(staging_rows) >= BATCH_FLUSH:
                    out_cursor.executemany(
                        "INSERT INTO staging VALUES (?, ?)", staging_rows
                    )
                    out_conn.commit()
                    staging_rows.clear()

                if total_processed % LOG_EVERY == 0:
                    elapsed = time.perf_counter() - start
                    rate = total_processed / elapsed if elapsed > 0 else 0
                    logging.info(
                        "  processed %d (rec %d / unrec %d) | %.0f names/sec",
                        total_processed, total_recognized,
                        total_unrecognized, rate,
                    )

        if staging_rows:
            out_cursor.executemany(
                "INSERT INTO staging VALUES (?, ?)", staging_rows
            )
            out_conn.commit()
            staging_rows.clear()

        unrecognized_path = os.path.join(
            self.output_dir, "unrecognized_pubmed_concept_names.txt"
        )
        with open(unrecognized_path, "w") as f:
            for name in sorted(unrecognized):
                f.write(name + "\n")

        logging.info("Recognized: %d, Unrecognized: %d (unique: %d), Errors: %d",
                     total_recognized, total_unrecognized,
                     len(unrecognized), total_errors)
        in_conn.close()


def _check_environment(args):
    """Verify that all required paths exist and dependencies are importable."""
    ok = True
    p = print

    # Describe the build mode
    p("")
    p("=" * 60)
    if args.test:
        p("  NGD BUILD — DRY RUN (--test)")
        p("  Validating paths and dependencies only.")
        p("  No data will be read or written.")
    elif args.full:
        if args.skip_download:
            p("  NGD BUILD — FULL (--skip-download)")
            p("  Will parse local PubMed XML and resolve to CURIEs.")
        else:
            p("  NGD BUILD — FULL")
            p("  Will sync PubMed mirror, parse XML, and resolve to CURIEs.")
    else:
        p("  NGD BUILD — RESOLVE ONLY")
        p("  Will re-resolve existing concept names to CURIEs.")
        p("  (Skipping XML parsing — use --full to re-parse.)")
    p("=" * 60)

    # Paths
    p("")
    p("Paths:")

    # Babel DB — always required
    if not args.babel_db:
        p("  [FAIL] --babel-db: not set (required, or set NGD_BABEL_DB)")
        ok = False
    elif not os.path.isfile(args.babel_db):
        p(f"  [FAIL] --babel-db: {args.babel_db} (not found)")
        ok = False
    else:
        p(f"  [ OK ] --babel-db: {args.babel_db}")

    # PubMed dir — validate whenever provided, required for --full
    if args.pubmed_dir:
        if not os.path.isdir(args.pubmed_dir):
            p(f"  [FAIL] --pubmed-dir: {args.pubmed_dir} (not found)")
            ok = False
        else:
            p(f"  [ OK ] --pubmed-dir: {args.pubmed_dir}")
            baseline = os.path.join(
                args.pubmed_dir, "ftp.ncbi.nlm.nih.gov", "pubmed", "baseline"
            )
            if not os.path.isdir(baseline):
                p(f"  [WARN] Expected baseline/ not found: {baseline}")
    elif args.full:
        p("  [FAIL] --pubmed-dir: not set (required for --full, or set NGD_PUBMED_DIR)")
        ok = False
    else:
        p("  [ -- ] --pubmed-dir: not set (not needed for resolve-only)")

    # Output dir
    if not os.path.isdir(args.output_dir):
        p(f"  [FAIL] --output-dir: {args.output_dir} (not found)")
        ok = False
    else:
        p(f"  [ OK ] --output-dir: {args.output_dir}")

    # Resolve-only prereq
    if not args.full:
        concept_db = os.path.join(args.output_dir, "conceptname_to_pmids.sqlite")
        if not os.path.isfile(concept_db):
            p(f"  [FAIL] conceptname_to_pmids.sqlite not found in --output-dir")
            p(f"         (required for resolve-only — use --full to build from scratch)")
            ok = False
        else:
            p(f"  [ OK ] conceptname_to_pmids.sqlite found in --output-dir")

    # Dependencies
    p("")
    p("Dependencies:")

    try:
        from lxml import etree  # noqa: F401
        p("  [ OK ] lxml")
    except ImportError:
        p("  [FAIL] lxml — not installed (pip install lxml)")
        ok = False

    try:
        from stitch_proj.local_babel import connect_to_db_read_only, map_name_to_curie  # noqa: F401
        p("  [ OK ] stitch_proj.local_babel")
    except ImportError:
        p("  [FAIL] stitch_proj — not installed (pip install stitch_proj)")
        ok = False

    # Summary
    p("")
    p("-" * 60)
    if ok:
        p("  PASSED — environment is ready.")
    else:
        p("  FAILED — fix the errors above before building.")
    p("-" * 60)
    p("")

    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Build the NGD curie_to_pmids SQLite database."
    )
    parser.add_argument("--full", action="store_true",
                        help="Re-parse PubMed XML from scratch.")
    parser.add_argument("--skip-download", action="store_true",
                        help="With --full, skip mirroring PubMed and use what's on disk.")
    parser.add_argument("--pubmed-dir", default=DEFAULT_PUBMED_DIR,
                        help="Local PubMed mirror root. "
                             "Also settable via NGD_PUBMED_DIR env var.")
    parser.add_argument("--babel-db", default=DEFAULT_BABEL_DB,
                        help="Babel sqlite path. "
                             "Also settable via NGD_BABEL_DB env var.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Directory for output databases and logs. "
                             "Also settable via NGD_OUTPUT_DIR env var. "
                             "Defaults to the script's directory.")
    parser.add_argument("--test", action="store_true",
                        help="Verify paths and environment without running the build.")

    args = parser.parse_args()

    env_ok = _check_environment(args)

    if args.test:
        sys.exit(0 if env_ok else 1)

    if not env_ok:
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
    )

    _load_dependencies()

    builder = NGDDatabaseBuilder(
        pubmed_dir=args.pubmed_dir,
        babel_db_path=args.babel_db,
        output_dir=args.output_dir,
        skip_download=args.skip_download,
    )
    builder.build_ngd_database(args.full)


if __name__ == "__main__":
    main()
