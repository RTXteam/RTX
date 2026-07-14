#!/usr/bin/env python3
"""Builds curie_to_pmids.sqlite in three independently-invokable stages:

    download  -> mirror PubMed FTP into --pubmed-dir (+ touch --mirror-sentinel)
    concept   -> parse the PubMed XML mirror into conceptname_to_pmids.sqlite
    curie     -> resolve concept names via Babel, merge tier-0 edge PMIDs,
                 write the final curie_to_pmids.sqlite

Each stage is its own subcommand so a Snakemake DAG can drive them independently.
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

from lxml import etree
from extraction_script import process_names
from stitch.local_babel import (
    connect_to_db_read_only,
    map_curie_to_preferred_curies,
    map_name_to_curie,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _setup_logging(diag_dir):
    """Configure root logging to console + <diag_dir>/ngdbuild.log."""
    os.makedirs(diag_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(diag_dir, "ngdbuild.log")),
            logging.StreamHandler(),
        ],
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
# Entries represent cases where Babel's case-insensitive name index maps a term
# to the wrong CURIE because of an unrelated identifier that shares the string
# (e.g. "Male" -> NCBIGene malE, the E. coli maltose transporter).
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

        # map_name_to_curie does a label-prefix LIKE with LIMIT 1 / no
        # ORDER BY -- it returns *some* identifier in the right clique,
        # not necessarily the clique's preferred (primary) curie. Walk
        # to the preferred curie so PMIDs land where runtime NGD lookups
        # actually look.
        raw_curie = result[0]
        try:
            preferred = map_curie_to_preferred_curies(
                _worker_babel_conn, raw_curie
            )
        except Exception as e:
            return None, concept_name, None, str(e)

        curie = preferred[0][0] if preferred else raw_curie

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
    """Builds the conceptname_to_pmids and curie_to_pmids SQLite databases.

    Paths are explicit (no single output_dir, no skip_download). Only the args a
    given stage needs must be supplied; the rest stay None.
    """

    def __init__(self, *, pubmed_dir=None, babel_db_path=None,
                 concept_db_path=None, curie_db_path=None,
                 tier0_edges_path=None, diag_dir=None, num_workers=None):
        self.pubmed_directory_path        = pubmed_dir
        self.babel_db_path                = babel_db_path
        self.conceptname_to_pmids_db_path = concept_db_path
        self.curie_to_pmids_db_path       = curie_db_path
        self.tier0_edges_path             = tier0_edges_path
        self.diag_dir                     = diag_dir
        self.num_workers = num_workers or max(1, (multiprocessing.cpu_count() or 2) - 1)
        self.status = "OK"

    # ----- stage: download -----
    def download_pubmed_mirror(self, sentinel_path):
        """Mirror the PubMed FTP tree into pubmed_dir, then touch the sentinel.

        Snakemake tracks the single sentinel file rather than the thousands of
        mirrored .xml.gz files.
        """
        os.makedirs(self.pubmed_directory_path, exist_ok=True)
        # -N: only fetch files newer than local copies (incremental). -nv: quieter.
        subprocess.check_call([
            "wget", "-r", "-N", "-nv",
            "ftp://ftp.ncbi.nlm.nih.gov/pubmed",
            "-P", self.pubmed_directory_path,
        ])
        sentinel = pathlib.Path(sentinel_path)
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.touch()

    # ----- stage: concept (parse-only) -----
    def build_conceptname_to_pmids_db(self):
        """Parse the local PubMed XML mirror and write a SQLite map from concept
        name to PMID list."""
        logging.info("Building conceptname_to_pmids...")
        start = time.time()

        if os.path.exists(self.conceptname_to_pmids_db_path):
            os.remove(self.conceptname_to_pmids_db_path)

        conn = sqlite3.connect(self.conceptname_to_pmids_db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("CREATE TABLE staging (concept_name TEXT, pmid TEXT)")
        conn.commit()

        logging.info("Parsing PubMed XML with %d workers", self.num_workers)

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

            with multiprocessing.Pool(self.num_workers) as pool:
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

    # ----- stage: curie (resolve + merge tier0) -----
    def build_curie_to_pmids_db(self):
        """Resolve concept names to CURIEs via Babel and write the final
        curie_to_pmids SQLite database, merging in tier 0 edges if set."""
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

        if self.tier0_edges_path:
            self._add_pmids_from_tier0_edges(out_cursor, out_conn)
        else:
            logging.warning(
                "No --tier0-edges provided; skipping tier 0 publication harvest. "
                "Output will only contain PubMed-scrape-derived curies."
            )

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

    def _add_pmids_from_tier0_edges(self, out_cursor, out_conn):
        # Harvests PMIDs from edges.publications in the tier 0 KGX JSONL graph
        # and attaches them to both endpoint curies. Tier 0 nodes do not carry
        # a publications field, so only edges are scanned. Curies are written
        # as-is (already canonical for tier 0), restoring the overlap that the
        # old KG2 harvest used to provide.
        logging.info("Harvesting PMIDs from tier 0 edges: %s",
                     self.tier0_edges_path)
        start = time.perf_counter()

        opener = gzip.open if self.tier0_edges_path.endswith(".gz") else open
        BATCH_FLUSH = 500_000
        LOG_EVERY = 1_000_000
        staging_rows = []
        total_lines = 0
        edges_with_pubs = 0
        rows_added = 0

        with opener(self.tier0_edges_path, "rt") as f:
            for line in f:
                total_lines += 1
                if '"publications"' not in line:
                    continue
                try:
                    edge = json.loads(line)
                except json.JSONDecodeError:
                    continue

                pubs = edge.get("publications")
                if not pubs:
                    continue

                pmid_nums = []
                for p in pubs:
                    if isinstance(p, str) and p.upper().startswith("PMID:"):
                        local = p.split(":", 1)[1]
                        digits = "".join(c for c in local if c.isdigit())
                        if digits:
                            pmid_nums.append(int(digits))
                if not pmid_nums:
                    continue

                edges_with_pubs += 1
                subj = edge.get("subject")
                obj = edge.get("object")
                for curie in (subj, obj):
                    if not curie:
                        continue
                    for n in pmid_nums:
                        staging_rows.append((curie, n))
                        rows_added += 1

                if len(staging_rows) >= BATCH_FLUSH:
                    out_cursor.executemany(
                        "INSERT INTO staging VALUES (?, ?)", staging_rows
                    )
                    out_conn.commit()
                    staging_rows.clear()

                if total_lines % LOG_EVERY == 0:
                    elapsed = time.perf_counter() - start
                    rate = total_lines / elapsed if elapsed > 0 else 0
                    logging.info(
                        "  scanned %d edges (%d with pubs, %d rows added) | %.0f edges/sec",
                        total_lines, edges_with_pubs, rows_added, rate,
                    )

        if staging_rows:
            out_cursor.executemany(
                "INSERT INTO staging VALUES (?, ?)", staging_rows
            )
            out_conn.commit()
            staging_rows.clear()

        logging.info(
            "Tier 0 harvest: scanned %d edges, %d had PMIDs, "
            "%d (curie, pmid) rows added in %.2f min",
            total_lines, edges_with_pubs, rows_added,
            (time.perf_counter() - start) / 60,
        )

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

        logging.info("Resolver pool: %d workers", self.num_workers)

        start = time.perf_counter()

        def row_iter():
            yield from in_cursor.execute(
                "SELECT concept_name, pmids FROM conceptname_to_pmids"
            )

        with multiprocessing.Pool(
            self.num_workers,
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
            self.diag_dir, "unrecognized_pubmed_concept_names.txt"
        )
        with open(unrecognized_path, "w", encoding="utf-8") as f:
            for name in sorted(unrecognized):
                f.write(name + "\n")

        logging.info("Recognized: %d, Unrecognized: %d (unique: %d), Errors: %d",
                     total_recognized, total_unrecognized,
                     len(unrecognized), total_errors)
        in_conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Build the NGD curie_to_pmids SQLite database in stages."
    )
    sub = parser.add_subparsers(dest="stage", required=True)

    d = sub.add_parser("download", help="Mirror PubMed FTP -> --pubmed-dir.")
    d.add_argument("--pubmed-dir", required=True)
    d.add_argument("--mirror-sentinel", required=True,
                   help="File touched on successful mirror (Snakemake target).")

    c = sub.add_parser("concept", help="Parse PubMed XML -> conceptname_to_pmids.sqlite.")
    c.add_argument("--pubmed-dir", required=True)
    c.add_argument("--concept-db", required=True)
    c.add_argument("--diag-dir", required=True)
    c.add_argument("--threads", type=int, default=None)

    u = sub.add_parser("curie", help="Resolve + merge tier0 -> curie_to_pmids.sqlite.")
    u.add_argument("--concept-db", required=True)
    u.add_argument("--babel-db", required=True)
    u.add_argument("--tier0-edges", default=None,
                   help="tier-0 KGX edges.jsonl[.gz]; optional but recommended.")
    u.add_argument("--curie-db", required=True)
    u.add_argument("--diag-dir", required=True)
    u.add_argument("--threads", type=int, default=None)

    args = parser.parse_args()

    if args.stage == "download":
        _setup_logging(os.path.dirname(args.mirror_sentinel) or ".")
        NGDDatabaseBuilder(pubmed_dir=args.pubmed_dir) \
            .download_pubmed_mirror(args.mirror_sentinel)

    elif args.stage == "concept":
        _setup_logging(args.diag_dir)
        builder = NGDDatabaseBuilder(
            pubmed_dir=args.pubmed_dir,
            concept_db_path=args.concept_db,
            diag_dir=args.diag_dir,
            num_workers=args.threads,
        )
        builder.build_conceptname_to_pmids_db()
        if builder.status != "OK":
            sys.exit(1)

    elif args.stage == "curie":
        _setup_logging(args.diag_dir)
        builder = NGDDatabaseBuilder(
            babel_db_path=args.babel_db,
            concept_db_path=args.concept_db,
            curie_db_path=args.curie_db,
            tier0_edges_path=args.tier0_edges,
            diag_dir=args.diag_dir,
            num_workers=args.threads,
        )
        builder.build_curie_to_pmids_db()
        if builder.status != "OK":
            sys.exit(1)


if __name__ == "__main__":
    main()
