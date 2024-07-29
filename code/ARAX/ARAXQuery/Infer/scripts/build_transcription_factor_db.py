import sqlite3
import requests
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration


def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            edge_id INTEGER,
            transcription_factor TEXT,
            neighbour TEXT
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

def insert_data_in_batches(db_path, data, batch_size=1000):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Prepare the insert statement
    insert_query = 'INSERT INTO edges (edge_id, transcription_factor, neighbour) VALUES (?, ?, ?)'
    
    # Insert data in batches
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany(insert_query, batch)
        conn.commit()
    
    cursor.close()
    conn.close()

def call_plover(tf):
    config = RTXConfiguration()
    json = []
    plover_url = config.plover_url
    endpoint = "/query"
    body = {
            "edges": {
                "e00": {
                    "subject": "n00",
                    "object": "n01"
                }
            },
            "nodes": {
                "n00": {
                    "ids": [tf]
                },
                "n01": {
                    "categories": ["biolink:NamedThing"]
                }
            },
            "include_metadata": True,
            "respect_predicate_symmetry": True
        }
    try:
        response = requests.post(plover_url + endpoint, headers={'accept': 'application/json'}, json=body)
        json = response.json()
    except Exception as e:
        pass
    return json

def main():
    parser = argparse.ArgumentParser(description="Create and populate an SQLite database.")
    parser.add_argument("--db_path", type=str, required=True, help="Path to the SQLite database file.")

    args = parser.parse_args()
    
    # Parse the data input (assuming a simple string representation for this example)

    data = []
    create_database(args.db_path)
    insert_data_in_batches(args.db_path, data)

if __name__ == "__main__":
    main()

