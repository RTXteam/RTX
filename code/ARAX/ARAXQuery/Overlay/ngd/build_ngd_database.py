#!/usr/bin/env python3
"""
Builds a SQLite database that maps canonicalized curies to PubMed articles they appear in. It creates
these mappings using data from a PubMed XML download and from the Tier-0 Dogpark graph.

There are two halves to the (full) build process:

1. Create an intermediary artifact called "conceptname_to_pmids.sqlite"
     - Contains mappings from "concept names" to the list of articles (PMIDs) they appear in (where "concept names"
       include MESH Descriptor/Qualifier names, Keywords, and Chemical names)
     - These mappings are obtained by scraping all of the PubMed XML files (which are automatically downloaded)
     - This file needs updating very infrequently (i.e., only with new PubMed releases)

2. Create the final file called "curie_to_pmids.sqlite"
     - Contains mappings from canonicalized curies to their list of PMIDs based on the data scraped from PubMed AND
       from Tier-0 data (nodes.jsonl and edges.jsonl publications)
     - The NodeSynonymizer resolves concept names from step 1 to canonical curies via external APIs
       (Name Resolver + Node Normalizer), using concurrent workers for throughput

Usage: python build_ngd_database.py [--test] [--full] [--skip-download]
       By default, only step 2 above will be performed. To do a "full" build, use the --full flag.
       Use --skip-download with --full to reuse previously downloaded PubMed XML files.
"""
import argparse
import concurrent.futures
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
from typing import List

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from lxml import etree

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
NGD_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))  # code directory


def _parse_one_pubmed_file(file_path):
    """Worker function: parses a single PubMed XML file and returns
    a list of (concept_name, pmid_curie) tuples."""
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
                    article.xpath(f"{mc}/MeshHeadingList/MeshHeading/QualifierName/text()") +
                    article.xpath(f"{mc}/ChemicalList/Chemical/NameOfSubstance/text()") +
                    article.xpath(f"{mc}/GeneSymbolList/GeneSymbol/text()") +
                    article.xpath(f"{mc}/KeywordList/Keyword/text()")
                )
                for concept_name in {cn for cn in all_concept_names if cn}:
                    rows.append((concept_name, pmid_curie))
                article.clear()
                while article.getprevious() is not None:
                    del article.getparent()[0]
            del context
    except Exception as e:
        return file_path, rows, str(e)
    return file_path, rows, None


class NGDDatabaseBuilder:
    def __init__(self, is_test, skip_download=False):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)s: %(message)s',
                            handlers=[logging.FileHandler("ngdbuild.log"),
                                      logging.StreamHandler()])
        self.pubmed_directory_path = "/home/ubuntu/data/pubmed_xml_files"
        self.conceptname_to_pmids_db_name = "conceptname_to_pmids.sqlite"
        self.conceptname_to_pmids_db_path = f"{NGD_DIR}/{self.conceptname_to_pmids_db_name}"
        self.curie_to_pmids_db_name = "curie_to_pmids.sqlite"
        self.curie_to_pmids_db_path = f"{NGD_DIR}/{self.curie_to_pmids_db_name}"
        self.status = 'OK'
        self.synonymizer = NodeSynonymizer(autocomplete=False)
        self.is_test = is_test
        self.skip_download = skip_download

    def build_ngd_database(self, do_full_build: bool):
        """Entry point: runs full or partial build depending on flag."""
        if do_full_build:
            self.build_conceptname_to_pmids_db()
        else:
            conceptname_to_pmids_db = pathlib.Path(self.conceptname_to_pmids_db_path)
            if not conceptname_to_pmids_db.exists():
                logging.error(f"You did not specify to do a full build, but the artifact necessary for a partial "
                              f"build ({self.conceptname_to_pmids_db_name}) does not yet exist. Either use --full "
                              f"to do a full build or put your {self.conceptname_to_pmids_db_name} into the right "
                              f"place ({self.conceptname_to_pmids_db_path}).")
                self.status = "ERROR"
        if self.status == 'OK':
            self.build_curie_to_pmids_db()

    def build_conceptname_to_pmids_db(self):
        """Downloads and parses PubMed XML files, saving concept name
        to PMID mappings in a SQLite database, flushing after each file
        to keep memory usage bounded."""
        logging.info(f"Starting to build {self.conceptname_to_pmids_db_name} from pubmed files..")
        start = time.time()
        if not self.skip_download:
            logging.info(f" Deleting any pre-existing Pubmed files..")
            subprocess.call(["rm", "-rf", self.pubmed_directory_path])
            logging.info(f" Downloading latest Pubmed XML files (baseline and update files)..")
            subprocess.check_call(["wget", "-r", "ftp://ftp.ncbi.nlm.nih.gov/pubmed", "-P", self.pubmed_directory_path])
        else:
            logging.info(f" Skipping download, using existing files in {self.pubmed_directory_path}")

        # Set up the intermediary SQLite database with append-only staging table
        if os.path.exists(self.conceptname_to_pmids_db_path):
            os.remove(self.conceptname_to_pmids_db_path)
        cn_conn = sqlite3.connect(self.conceptname_to_pmids_db_path)
        cn_cursor = cn_conn.cursor()
        cn_cursor.execute("PRAGMA journal_mode=WAL")
        cn_cursor.execute("PRAGMA synchronous=NORMAL")
        cn_cursor.execute("CREATE TABLE staging (concept_name TEXT, pmid TEXT)")
        cn_conn.commit()

        num_workers = min(8, multiprocessing.cpu_count() - 1) or 1

        for sub_dir_name in ["baseline", "updatefiles"]:
            xml_file_sub_dir = f"{self.pubmed_directory_path}/ftp.ncbi.nlm.nih.gov/pubmed/{sub_dir_name}"
            all_file_names = [os.fsdecode(file) for file in os.listdir(xml_file_sub_dir)]
            pubmed_file_names = [file_name for file_name in all_file_names if file_name.lower().startswith('pubmed')
                                 and file_name.lower().endswith('.xml.gz')]

            # Make sure the files seem to have been downloaded ok
            if not pubmed_file_names:
                if sub_dir_name == "baseline":
                    logging.error("Couldn't find any PubMed baseline XML files to scrape. Something must've gone wrong "
                                  "downloading them.")
                    self.status = 'ERROR'
                    cn_conn.close()
                    return
                else:
                    logging.warning(f"No Pubmed 'update' files detected. This might be ok (it's possible none exist), "
                                    f"but it's a little weird.")

            pubmed_file_names_to_process = pubmed_file_names if not self.is_test else pubmed_file_names[:1]
            file_paths = [f"{xml_file_sub_dir}/{fn}" for fn in pubmed_file_names_to_process]
            total_files = len(file_paths)
            logging.info(f" Starting to process {total_files} {sub_dir_name} PubMed files with {num_workers} workers..")

            num_skipped_files = 0
            files_done = 0
            with multiprocessing.Pool(num_workers, maxtasksperchild=1) as pool:
                for file_path, rows, error in pool.imap_unordered(_parse_one_pubmed_file, file_paths):
                    files_done += 1
                    if error:
                        logging.warning(f"  File {os.path.basename(file_path)} threw an exception: {error}")
                        num_skipped_files += 1
                    if rows:
                        cn_cursor.executemany("INSERT INTO staging (concept_name, pmid) VALUES (?, ?)", rows)
                    del rows
                    if files_done % 50 == 0:
                        cn_conn.commit()
                        logging.info(f"  Processed {files_done}/{total_files} {sub_dir_name} files")
                cn_conn.commit()

            if num_skipped_files:
                logging.warning(f"Was unable to process {num_skipped_files} of {total_files} "
                                f"{sub_dir_name} files because they threw an exception on etree.parse()")

        # Merge pass: aggregate staging rows into final deduplicated table
        logging.info("  Creating index on staging table for merge..")
        cn_cursor.execute("CREATE INDEX idx_staging_concept ON staging (concept_name)")
        cn_conn.commit()
        logging.info("  Merging staging rows into final conceptname_to_pmids table..")
        cn_cursor.execute("""
            CREATE TABLE conceptname_to_pmids (
                concept_name TEXT PRIMARY KEY,
                pmids TEXT
            )
        """)
        cn_cursor.execute("""
            INSERT INTO conceptname_to_pmids (concept_name, pmids)
            SELECT concept_name,
                   '[' || GROUP_CONCAT(DISTINCT '"' || pmid || '"') || ']'
            FROM staging
            GROUP BY concept_name
        """)
        cn_conn.commit()
        logging.info("  Dropping staging table..")
        cn_cursor.execute("DROP TABLE staging")
        cn_conn.commit()

        cn_cursor.execute("SELECT COUNT(*) FROM conceptname_to_pmids")
        count = cn_cursor.fetchone()[0]
        cn_conn.close()
        elapsed_hours = round(((time.time() - start) / 60) / 60, 3)
        logging.info(f"Done! Building {self.conceptname_to_pmids_db_name} "
                     f"took {elapsed_hours} hours ({count} concept names)")

    def build_curie_to_pmids_db(self):
        """Creates a sqlite database of curie->PMIDs mappings from
        PubMed scrape data and Tier-0 graph publications.
        Uses an append-only staging table, then a single merge pass."""
        logging.info(f"Starting to build {self.curie_to_pmids_db_name}..")
        start = time.time()

        # Set up the output database with append-only staging
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
            out_conn.close()
            return
        self._add_pmids_from_tier0_edges(out_cursor, out_conn)
        self._add_pmids_from_tier0_nodes(out_cursor, out_conn)

        # Merge pass: aggregate staging into final table in Python to avoid
        # slow GROUP_CONCAT on hundreds of millions of rows
        logging.info("  Creating index on staging table for merge..")
        out_cursor.execute("CREATE INDEX idx_staging_curie ON staging (curie)")
        out_conn.commit()
        logging.info("  Merging staging rows into final curie_to_pmids table (Python merge)..")
        out_cursor.execute("CREATE TABLE curie_to_pmids (curie TEXT PRIMARY KEY, pmids TEXT)")
        out_conn.commit()

        curie_pmids = {}
        out_cursor.execute("SELECT curie, pmid FROM staging ORDER BY curie")
        batch_count = 0
        while True:
            rows = out_cursor.fetchmany(500000)
            if not rows:
                break
            for curie, pmid in rows:
                if curie not in curie_pmids:
                    curie_pmids[curie] = set()
                curie_pmids[curie].add(pmid)
            batch_count += len(rows)
            if batch_count % 5000000 == 0:
                logging.info(f"    Read {batch_count} staging rows..")

        logging.info(f"  Writing {len(curie_pmids)} curies to final table..")
        insert_batch = []
        for curie, pmid_set in curie_pmids.items():
            insert_batch.append((curie, json.dumps(list(pmid_set))))
            if len(insert_batch) >= 50000:
                out_cursor.executemany("INSERT INTO curie_to_pmids VALUES (?, ?)", insert_batch)
                insert_batch.clear()
        if insert_batch:
            out_cursor.executemany("INSERT INTO curie_to_pmids VALUES (?, ?)", insert_batch)
        out_conn.commit()

        logging.info("  Dropping staging table..")
        out_cursor.execute("DROP TABLE staging")
        out_conn.commit()

        count = len(curie_pmids)
        del curie_pmids
        logging.info(f"  In the end, found PMID lists for {count} (canonical) curies")
        out_conn.close()
        logging.info(f"Done! Building {self.curie_to_pmids_db_name} took {round((time.time() - start) / 60)} minutes.")

    # Helper methods

    def _append_curie_pmids(self, cursor, connection, rows):
        """Appends (curie, pmid_int) rows to the staging table."""
        if rows:
            cursor.executemany("INSERT INTO staging (curie, pmid) VALUES (?, ?)", rows)
            connection.commit()

    def _add_pmids_from_tier0_edges(self, out_cursor, out_conn):
        """Reads edges.jsonl and appends curie/pmid rows to staging."""
        logging.info("  Getting PMIDs from edges in Tier-0 graph..")
        edges_file = "/home/ubuntu/data/graph/edges.jsonl"
        rows = []
        flush_size = 50000
        count = 0

        with open(edges_file, "r") as f:
            for line in f:
                edge = json.loads(line)
                publications = edge.get("publications")
                if not publications:
                    continue

                subj = edge.get("subject")
                obj = edge.get("object")
                if not subj or not obj:
                    continue

                pmids = self._extract_and_format_pmids(publications)
                if not pmids:
                    continue

                for curie in (subj, obj):
                    for pmid in pmids:
                        pmid_int = self._get_local_id_as_int(pmid)
                        if pmid_int is not None:
                            rows.append((curie, pmid_int))

                count += 1
                if len(rows) >= flush_size:
                    self._append_curie_pmids(out_cursor, out_conn, rows)
                    rows.clear()

                if self.is_test and count >= 100:
                    break

        self._append_curie_pmids(out_cursor, out_conn, rows)
        logging.info(f"  Processed {count} edges with publications.")

    def _add_pmids_from_tier0_nodes(self, out_cursor, out_conn):
        """Reads nodes.jsonl and appends curie/pmid rows to staging."""
        logging.info("  Getting PMIDs from nodes in Tier-0 graph..")
        nodes_file = "/home/ubuntu/data/graph/nodes.jsonl"
        rows = []
        flush_size = 50000
        count = 0

        with open(nodes_file, "r") as f:
            for line in f:
                node = json.loads(line)
                publications = node.get("publications")
                if not publications:
                    continue

                node_id = node.get("id")
                if not node_id:
                    continue

                pmids = self._extract_and_format_pmids(publications)
                if not pmids:
                    continue

                for pmid in pmids:
                    pmid_int = self._get_local_id_as_int(pmid)
                    if pmid_int is not None:
                        rows.append((node_id, pmid_int))

                count += 1
                if len(rows) >= flush_size:
                    self._append_curie_pmids(out_cursor, out_conn, rows)
                    rows.clear()

                if self.is_test and count >= 100:
                    break

        self._append_curie_pmids(out_cursor, out_conn, rows)
        logging.info(f"  Processed {count} nodes with publications.")

    def _add_pmids_from_pubmed_scrape(self, out_cursor, out_conn):
        """Loads PubMed concept-name-to-PMID mappings from SQLite,
        resolves via NodeSynonymizer using parallel threads, and appends
        curie/pmid rows to the staging table."""
        logging.info(f"  Loading concept-to-pmids DB ({self.conceptname_to_pmids_db_name})..")
        if not os.path.exists(self.conceptname_to_pmids_db_path):
            logging.error(f"{self.conceptname_to_pmids_db_name} must exist in order to do a partial build. Use "
                          f"--full to do a full build or put your {self.conceptname_to_pmids_db_name} into the right"
                          f" place ({self.conceptname_to_pmids_db_path}).")
            self.status = 'ERROR'
            return
        cn_conn = sqlite3.connect(self.conceptname_to_pmids_db_path)
        cn_cursor = cn_conn.cursor()
        cn_cursor.execute("SELECT COUNT(*) FROM conceptname_to_pmids")
        total_rows = cn_cursor.fetchone()[0]
        if total_rows == 0:
            logging.error(f"{self.conceptname_to_pmids_db_name} exists but is empty.")
            self.status = 'ERROR'
            cn_conn.close()
            return

        # Load all concept names and their PMID lists
        logging.info(f"  Loading all {total_rows} concept names from DB..")
        cn_cursor.execute("SELECT concept_name, pmids FROM conceptname_to_pmids")
        all_rows = cn_cursor.fetchall()
        cn_conn.close()

        concept_names = [row[0] for row in all_rows]
        pmids_map = {row[0]: json.loads(row[1]) for row in all_rows}
        del all_rows

        # Resolve concept names to canonical curies using 10 concurrent workers,
        # each processing batches of 1000 names via the NodeSynonymizer API.
        batch_size = 1000
        num_workers = 10
        name_batches = [concept_names[i:i + batch_size]
                        for i in range(0, len(concept_names), batch_size)]
        total_batches = len(name_batches)
        logging.info(f"  Resolving {len(concept_names)} concept names in {total_batches} batches "
                     f"({num_workers} concurrent workers, {batch_size} names/batch)..")

        canonical_curies_dict = {}
        batches_done = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_batch = {
                executor.submit(self.synonymizer.get_canonical_curies, names=batch): batch
                for batch in name_batches
            }
            for future in concurrent.futures.as_completed(future_to_batch):
                result = future.result()
                if result:
                    canonical_curies_dict.update(result)
                batches_done += 1
                if batches_done % 500 == 0:
                    logging.info(f"    Resolved {batches_done}/{total_batches} batches..")

        logging.info(f"  Got results back from NodeSynonymizer ({len(canonical_curies_dict)} entries).")

        if not canonical_curies_dict:
            logging.error("NodeSynonymizer didn't return anything!")
            self.status = 'ERROR'
            return

        # Map canonical curies to PMIDs
        logging.info(f"  Mapping canonical curies to PMIDs..")
        total_recognized = 0
        total_unrecognized = 0
        staging_rows = []
        unrecognized_names = []

        for concept_name in concept_names:
            canonical_info = canonical_curies_dict.get(concept_name)
            if not canonical_info or not canonical_info.get('preferred_curie'):
                total_unrecognized += 1
                unrecognized_names.append(concept_name)
                continue

            total_recognized += 1
            canonical_curie = canonical_info['preferred_curie']
            for pub_id in pmids_map[concept_name]:
                if pub_id.upper().startswith('PMID'):
                    local_id = pub_id.split(":")[-1] if ":" in pub_id else pub_id[4:]
                    stripped = "".join(c for c in local_id if c.isdigit())
                    if stripped:
                        staging_rows.append((canonical_curie, int(stripped)))

            # Flush staging rows periodically
            if len(staging_rows) >= 500000:
                out_cursor.executemany("INSERT INTO staging (curie, pmid) VALUES (?, ?)", staging_rows)
                out_conn.commit()
                staging_rows.clear()

        if staging_rows:
            out_cursor.executemany("INSERT INTO staging (curie, pmid) VALUES (?, ?)", staging_rows)
            out_conn.commit()

        with open(f"{NGD_DIR}/unrecognized_pubmed_concept_names.txt", "w") as unrecognized_file:
            for name in unrecognized_names:
                unrecognized_file.write(f"{name}\n")

        total_concepts = total_recognized + total_unrecognized
        if total_concepts > 0:
            logging.info(f"  NodeSynonymizer recognized {round((total_recognized / total_concepts) * 100)}%"
                         f" of concept names scraped from pubmed.")
        logging.info(f"  Unrecognized concept names were written to unrecognized_pubmed_concept_names.txt.")

    def _extract_and_format_pmids(self, publications: List[str]) -> List[str]:
        """Filters publications to PMIDs and normalizes to PMID:12345 format."""
        pmids = {pub_id for pub_id in publications
                 if pub_id.upper().startswith('PMID')}
        formatted_pmids = [
            self._create_pmid_curie_from_local_id(
                pmid.replace('PMID', '').replace(':', ''))
            for pmid in pmids
        ]
        return formatted_pmids

    @staticmethod
    def _create_pmid_curie_from_local_id(pmid):
        """Formats a bare PMID number as 'PMID:12345'."""
        return f"PMID:{pmid}"

    @staticmethod
    def _get_local_id_as_int(curie):
        """Converts 'PMID:1234' to integer 1234, stripping non-digit chars."""
        curie_pieces = curie.split(":")
        local_id_str = curie_pieces[-1]
        # Remove any strange characters (like in "PMID:_19960544")
        stripped_id_str = "".join([character for character in local_id_str if character.isdigit()])
        return int(stripped_id_str) if stripped_id_str else None


def main():
    # Load command-line arguments
    arg_parser = argparse.ArgumentParser(description="Builds database of curie->PMID mappings needed for NGD")
    arg_parser.add_argument("--full", dest="full", action="store_true", default=False)
    arg_parser.add_argument("--skip-download", dest="skip_download", action="store_true", default=False)
    arg_parser.add_argument("--test", dest="test", action="store_true", default=False)
    args = arg_parser.parse_args()

    # Build the database(s)
    database_builder = NGDDatabaseBuilder(args.test, skip_download=args.skip_download)
    database_builder.build_ngd_database(args.full)


if __name__ == '__main__':
    main()

