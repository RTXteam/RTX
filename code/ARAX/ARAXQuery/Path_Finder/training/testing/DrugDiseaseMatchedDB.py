import sqlite3

import pandas as pd


class DrugDiseaseMatchedDB:

    def __init__(self, db_address):
        self.db_address = db_address

    def create_table(self):
        conn = sqlite3.connect(self.db_address)

        cursor = conn.cursor()

        create_table_query = """
        CREATE TABLE IF NOT EXISTS DrugDiseaseMatch (
            drug TEXT,
            disease TEXT,
            matched TEXT,
            containment_index REAL,
            number_of_found_nodes INTEGER,
            number_of_test_nodes INTEGER
        );
        """

        cursor.execute(create_table_query)

        conn.commit()
        conn.close()

    def read_all(self):
        conn = sqlite3.connect(self.db_address)

        query = "SELECT containment_index FROM DrugDiseaseMatch"
        data = pd.read_sql_query(query, conn)
        conn.close()
        return data

    def insert(self, drug, disease, matched, containment_index, number_of_found_nodes, number_of_test_nodes):
        conn = sqlite3.connect(self.db_address)
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO DrugDiseaseMatch (drug, disease, matched, containment_index, number_of_found_nodes, number_of_test_nodes)
        VALUES (?, ?, ?, ?, ?, ?);
        """

        cursor.execute(insert_query,
                       (drug, disease, matched, containment_index, number_of_found_nodes, number_of_test_nodes))

        conn.commit()
        conn.close()

    def has_pair(self, source, destination):
        conn = sqlite3.connect(self.db_address)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM DrugDiseaseMatch
            WHERE drug = ? AND disease = ? AND containment_index > 0
        """, (source, destination))

        results = cursor.fetchall()

        conn.close()
        if results:
            return True
        else:
            return False