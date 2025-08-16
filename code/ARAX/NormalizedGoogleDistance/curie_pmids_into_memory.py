import logging
import sqlite3


def curie_pmids_into_memory(curie_to_pmids_path, curie_to_pmids_version, redis_client):

    version = redis_client.get('version')
    if version is not None:
        version = version.decode('utf-8')
        if version == curie_to_pmids_version:
            return


    redis_client.flushall()
    sqlite_connection = sqlite3.connect(f"file:{curie_to_pmids_path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
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
            raise e
    redis_client.set('version', curie_to_pmids_version)
    cursor.close()
    sqlite_connection.close()

    logging.info("Data inserted successfully into Redis.")
