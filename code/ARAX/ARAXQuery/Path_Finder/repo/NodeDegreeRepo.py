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
            return degree_by_biolink_type["biolink:NamedThing"]
        else:
            return 0
