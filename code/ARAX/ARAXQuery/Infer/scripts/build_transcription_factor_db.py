import sqlite3
import requests
import sys
import os
import argparse
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../data/")  # ARAXQuery directory

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration 

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    db_create_queries = ['''
        CREATE TABLE IF NOT EXISTS tf_neighbors (
            edge_id INTEGER,
            transcription_factor TEXT,
            neighbour TEXT
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS edges (
            edge_id INTEGER,
            predicate TEXT,
            primary_knowledge_source TEXT,
            qualified_predicate TEXT,
            object_direction TEXT,
            object_aspect TEXT


        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS nodes (
            curie STRING,
            name TEXT,
            category TEXT


        )
        '''

        ]
    

    for query in db_create_queries:
        cursor.execute(query)
        conn.commit()
    cursor.close()
    conn.close()

def get_transcription_factors():
    with open('../data/xCRG_data/transcription_factors.json') as fp:
        tf = json.loads(fp.read())
    return tf["tf"]

def insert_data_in_batches(db_path, data, query, batch_size=1000):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany(query, batch)
        conn.commit()
    cursor.close()
    conn.close()

def insert_tf_data(db_path, data):
    insert_tf_neighbour_query = 'INSERT INTO tf_neighbors (edge_id, transcription_factor, neighbour) VALUES (?, ?, ?)'
    insert_edge_query = 'INSERT INTO edges (edge_id, predicate, primary_knowledge_source, qualified_predicate, object_direction, object_aspect) VALUES (?, ?, ?, ?, ?, ?)'
    insert_node_query = 'INSERT INTO nodes (curie, name, category) VALUES (?, ?, ?)'
    # {"neigbhor_data": tf_neighbor_data, "edge_data": edge_data, "node_data": node_data}
    insert_data_in_batches(db_path, data['neigbhor_data'], insert_tf_neighbour_query)
    insert_data_in_batches(db_path, data['edge_data'], insert_edge_query)
    insert_data_in_batches(db_path, data['node_data'], insert_node_query)

def batch_list(input_list, batch_size):
    # Using list comprehension to batch the list
    return [input_list[i:i + batch_size] for i in range(0, len(input_list), batch_size)]

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
def get_tf_neighbors(tf):

    tf_neighbor_data = []
    edge_data = []
    node_data = []
    response = call_plover(tf)
    edges = response.get("edges",{}).get("e00",{})
    for edge in edges.keys():
        c1 = edges[edge][0]
        c2 = edges[edge][1]
        curie = c1 if c1 != tf else c2
        tf_neighbor_data.append([edge, tf, curie])
    return {"neigbhor_data": tf_neighbor_data, "edge_data": edge_data, "node_data": node_data}


    answer = []
def main():
    parser = argparse.ArgumentParser(description="Create and populate TF database.")
    parser.add_argument("--db_path", type=str, required=True, help="Path to the SQLite database file.")

    args = parser.parse_args()
    
    # Parse the data input (assuming a simple string representation for this example)

    data = []
    create_database(args.db_path)
    tfs = get_transcription_factors()
    count = 1
    for tf in tfs[:]:
        print(count)
        count += 1
        data = get_tf_neighbors(tf)
        insert_tf_data(args.db_path, data)
        break

if __name__ == "__main__":
    main()

