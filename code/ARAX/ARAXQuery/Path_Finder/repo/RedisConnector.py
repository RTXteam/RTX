import redis


class RedisConnector:
    def __init__(self):
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

    def has_pmids(self, key):
        return self.redis_client.exists(key) == 1

    def get_key_length(self, key):
        try:
            return self.redis_client.scard(key)
        except redis.exceptions.ResponseError as e:
            print(f"Error fetching lengths for keys: {e}")
            return 0

    def get_len_of_keys(self, keys):
        try:
            pipeline = self.redis_client.pipeline()
            for key in keys:
                pipeline.scard(key)
            lengths = pipeline.execute()
            return zip(keys, lengths)
        except redis.exceptions.ResponseError as e:
            print(f"Error fetching lengths for keys: {e}")

    def get_intersection_list(self, curie, curies):
        try:
            pipeline = self.redis_client.pipeline()
            for key, value in curies:
                pipeline.sinter(curie, key)
            interesection_list = pipeline.execute()

            return interesection_list

        except redis.exceptions.ResponseError as e:
            print(f"Error fetching lengths for keys: {e}")
            return []
