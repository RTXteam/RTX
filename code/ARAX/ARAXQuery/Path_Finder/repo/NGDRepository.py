import os
import sys
import sqlite3
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.utility import get_curie_ngd_path


class NodeDegreeRepo:

    def __init__(self, db_path=get_curie_ngd_path()):
        self.db_path = db_path

    def get_curie_ngd(self, node):
        sqlite_connection_read = sqlite3.connect(self.db_path)
        cursor = sqlite_connection_read.cursor()
        query = "SELECT ngd FROM curie_ngd WHERE curie = ?"
        cursor.execute(query, (node.id,))
        row = cursor.fetchone()
        cursor.close()
        sqlite_connection_read.close()

        if row:
            ngds = ast.literal_eval(row[0])
            return ngds
        return []
