import os
import sys
import sqlite3
import json



sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.utility import get_kg2c_db_path


class NodeDegreeRepo:

    def __init__(self, db_path=get_kg2c_db_path()):
        self.db_path = db_path

    def get_node_degree(self, node_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = "SELECT neighbor_counts FROM neighbors WHERE id = ?"
        cursor.execute(query, (node_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            degree_by_biolink_type = json.loads(result[0])
            return degree_by_biolink_type.get('biolink:NamedThing', 0)
        else:
            return 0


    def get_degrees_by_node(self, curie_ids, batch_size=10000):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        degree_dict = {}

        for i in range(0, len(curie_ids), batch_size):
            batch_ids = curie_ids[i:i + batch_size]
            placeholders = ",".join("?" for _ in batch_ids)
            query = f"SELECT id, neighbor_counts FROM neighbors WHERE id IN ({placeholders})"
            cursor.execute(query, batch_ids)

            for node_id, neighbor_counts in cursor.fetchall():
                degree_by_biolink_type = json.loads(neighbor_counts)
                degree_dict[node_id] = degree_by_biolink_type

        conn.close()

        for curie in curie_ids:
            degree_dict.setdefault(curie, {})

        return degree_dict

    def get_degree_categories(self, batch_size=10000):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        degree_category_set = set()
        offset = 0

        while True:
            query = f"SELECT id, neighbor_counts FROM neighbors LIMIT {batch_size} OFFSET {offset}"
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                break

            for node_id, neighbor_counts in rows:
                degree_by_biolink_type = json.loads(neighbor_counts)
                degree_category_set.update(degree_by_biolink_type.keys())

            offset += batch_size
            print(offset)

        conn.close()

        return degree_category_set
