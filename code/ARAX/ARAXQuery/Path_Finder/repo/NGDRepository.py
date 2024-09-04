import os
import sys
import sqlite3
import ast

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.utility import get_curie_ngd_path


class NGDRepository:

    def __init__(self, db_path=get_curie_ngd_path()):
        self.db_path = db_path

    def get_curie_ngd(self, curie):
        try:
            sqlite_connection_read = sqlite3.connect(self.db_path)
            cursor = sqlite_connection_read.cursor()
            query = "SELECT ngd FROM curie_ngd WHERE curie = ?"
            cursor.execute(query, (curie,))
            row = cursor.fetchone()
            cursor.close()
            sqlite_connection_read.close()
        except Exception as e:
            raise Exception(f"{e}, db path: {self.db_path}")
        if row:
            ngds = ast.literal_eval(row[0])
            return ngds

        return []

    def get_curies_pmid_length(self, curies, limit):
        try:
            sqlite_connection_read = sqlite3.connect(self.db_path)
            cursor = sqlite_connection_read.cursor()
            query = f"""
            SELECT curie, pmid_length
            FROM curie_ngd
            WHERE curie IN ({','.join('?' for _ in curies)})
            ORDER BY pmid_length DESC
            LIMIT {limit};
            """
            cursor.execute(query, curies)
            rows = cursor.fetchall()
            cursor.close()
            sqlite_connection_read.close()
        except Exception as e:
            raise Exception(f"{e}, db path: {self.db_path}")
        return rows
