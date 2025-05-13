import logging

import redis


class RedisConnector:
    def __init__(self):
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

    def has_pmids(self, key):
        return self.redis_client.exists(key) == 1

    def get_key_length(self, key):
        return self.redis_client.scard(key)

    def get_len_of_keys(self, keys):
        try:
            pipeline = self.redis_client.pipeline()
            for key in keys:
                pipeline.scard(key)
            lengths = pipeline.execute()
            return zip(keys, lengths)
        except Exception as e:
            logging.error(f"Error fetching lengths for keys: {e}")
            raise e

    def get_intersection_list(self, curie, curies):
        pipeline = self.redis_client.pipeline()
        for key, value in curies:
            pipeline.sinter(curie, key)
        interesection_list = pipeline.execute()

        return interesection_list
