import logging
import os
import sys
import json
import sqlite3
import multiprocessing
import time
from datetime import datetime

from NGDSortedNeighborsRepo import NGDSortedNeighborsRepo
from PloverDBRepo import PloverDBRepo

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from RTXConfiguration import RTXConfiguration

def calculate_neighbor_NGD_list(data):
    try:
        return data[0], NGDSortedNeighborsRepo().get_neighbors(data[0], data[1], data[2]), None
    except Exception as e:
        logging.error(f"Exception occurred while get_neighbors called with key: {data[0]}")
        logging.error(f"Exception: {e}")
        return data[0], None, e


def run_ngd_calculation_process(curie_to_pmids_path, ngd_db_name, log_of_NGD_normalizer, redis_connector):
    repo = PloverDBRepo(plover_url=RTXConfiguration().plover_url)
    sqlite_connection_write = sqlite3.connect(ngd_db_name)
    cursor_write = sqlite_connection_write.cursor()
    cursor_write.execute('''
        CREATE TABLE IF NOT EXISTS curie_ngd (
            curie TEXT NOT NULL PRIMARY KEY,
            ngd TEXT NOT NULL,
            pmid_length INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor_write.close()
    sqlite_connection_write.close()

    sqlite_connection_read = sqlite3.connect(f"file:{curie_to_pmids_path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    cursor_read = sqlite_connection_read.cursor()
    num_cores = multiprocessing.cpu_count()
    batch_size = min(128, num_cores * 10)
    offset = 0

    while True:
        logging.info("Begin Time: %s", datetime.now())
        query = f"SELECT curie, pmids FROM curie_to_pmids LIMIT {batch_size} OFFSET {offset}"
        cursor_read.execute(query)
        rows = cursor_read.fetchall()
        if not rows:
            break
        CURIEs = [row[0] for row in rows]
        try:
            neighbors_by_curie = repo.get_neighbors(CURIEs)
        except Exception as e:
            logging.info(f"get neighbors exception, Error:{e}")
            time.sleep(5)
            continue
        logging.info("After Getting Neighbors: %s", datetime.now())
        offset += batch_size

        CURIEs_and_neighbors = [(curie, neighbors_by_curie[curie], log_of_NGD_normalizer) for curie in CURIEs]

        with multiprocessing.Pool(num_cores) as pool:
            results = pool.map(calculate_neighbor_NGD_list, CURIEs_and_neighbors)

        curie_pmid_length_zip = redis_connector.get_len_of_keys(CURIEs)

        pmid_length_by_curie = {}
        for curie, pmid_length in curie_pmid_length_zip:
            pmid_length_by_curie[curie] = pmid_length

        sqlite_connection_write = sqlite3.connect(ngd_db_name)
        cursor_write = sqlite_connection_write.cursor()

        for curie, ngds, error in results:
            if ngds is None:
                logging.info(f"Error occurred for CURIE: {curie}, Error:{error}")
                continue
            ngd_as_text = json.dumps(ngds)
            if curie in pmid_length_by_curie:
                pmid_length = pmid_length_by_curie[curie]
            cursor_write.execute('''
                INSERT INTO curie_ngd (curie, ngd, pmid_length)
                VALUES (?, ?, ?)
            ''', (curie, ngd_as_text, pmid_length))

        sqlite_connection_write.commit()
        cursor_write.close()
        sqlite_connection_write.close()

        logging.info("Current Time: %s", datetime.now())
        logging.info(f"Total keys: {offset}")

    cursor_read.close()
    sqlite_connection_read.close()