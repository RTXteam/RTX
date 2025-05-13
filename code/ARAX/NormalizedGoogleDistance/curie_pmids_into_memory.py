import sqlite3
import logging
import ast


def curie_pmids_into_memory(db_name, redis_client):
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()

    batch_size = 1000
    pipeline_size = 1000
    offset = 0

    while True:
        try:
            query = f"SELECT curie, pmids FROM curie_to_pmids LIMIT {batch_size} OFFSET {offset}"
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                break

            pipeline = redis_client.pipeline()

            for row in rows:
                curie = row[0]
                pmids = ast.literal_eval(row[1])
                if len(pmids) == 0:
                    continue
                pipeline.sadd(curie, *pmids)

                if len(pipeline) >= pipeline_size:
                    pipeline.execute()

            pipeline.execute()
            offset += batch_size
        except Exception as e:
            logging.error("Exception occurred while inserting CURIE PMIDS into Redis in memory database.")
            logging.error(f"Exception: {e}")
            logging.error(f"Offset: {offset}")
            logging.error(f"Batch size: {batch_size}")

    cursor.close()
    sqlite_connection.close()

    logging.info("Data inserted successfully into Redis.")
