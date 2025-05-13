import redis
import json
import sqlite3
import multiprocessing
import logging
import time
from datetime import datetime
from NGDSortedNeighborsRepo import NGDSortedNeighborsRepo
from PloverDBRepo import PloverDBRepo
from curie_pmids_into_memory import curie_pmids_into_memory
from RedisConnector import RedisConnector


def set_up_log():
    logging.basicConfig(
        filename='NGD_script.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO
    )


def calculate_neighbor_NGD_list(data):
    try:
        return data[0], NGDSortedNeighborsRepo().get_neighbors(data[0], data[1]), None
    except Exception as e:
        logging.error(f"Exception occurred while get_neighbors called with key: {data[0]}")
        logging.error(f"Exception: {e}")
        return data[0], None, e


def run_ngd_calculation_process(curie_pmid_db_name, ngd_db_name):
    repo = PloverDBRepo("https://kg2cplover.rtx.ai:9990")
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

    sqlite_connection_read = sqlite3.connect(curie_pmid_db_name)
    cursor_read = sqlite_connection_read.cursor()
    num_cores = multiprocessing.cpu_count()
    batch_size = 10 * num_cores
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

        CURIEs_and_neighbors = [(curie, neighbors_by_curie[curie]) for curie in CURIEs]

        with multiprocessing.Pool(num_cores) as pool:
            results = pool.map(calculate_neighbor_NGD_list, CURIEs_and_neighbors)

        redis_client = RedisConnector()

        curie_pmid_length_zip = redis_client.get_len_of_keys(CURIEs)

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


if __name__ == "__main__":
    set_up_log()
    logging.info(f"Start time: {datetime.now()}")
    curie_pmid_db_name = 'curie_to_pmids_v1.0_KG2.10.1.sqlite'
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.flushall()
    curie_pmids_into_memory(curie_pmid_db_name, redis_client)
    logging.info(f"{curie_pmid_db_name} inserted completely into Redis")
    run_ngd_calculation_process(curie_pmid_db_name, "curie_ngd_v1.0_KG2.10.1.sqlite")
