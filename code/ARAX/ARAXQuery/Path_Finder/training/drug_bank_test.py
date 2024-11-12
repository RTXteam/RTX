import json
import os
import sys
import logging
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from path_finder_service import get_paths_from_path_finder


def extract_intermediate_nodes(paths):
    nodes = set()
    for path in paths:
        for i in range(0, len(path.links)):
            if i != 0 and (i != len(path.links) - 1):
                nodes.add(str(path.links[i]))
    return nodes


def run_tests():
    with open('./Path_Finder/training/data/DrugBank_aligned_with_KG2.json', 'r') as file:
        data = json.load(file)

    counter = 0
    for source, value in data.items():
        test_nodes = set(value['mechanistic_intermediate_nodes'].keys())
        for destination, _ in value['indication_NER_aligned'].items():
            paths = get_paths_from_path_finder(source, destination)
            intermediate_node_from_path_finder = extract_intermediate_nodes(paths)
            matched = intermediate_node_from_path_finder & test_nodes
            containment_index = len(matched) / len(test_nodes)
            insert(source, destination, str(matched), containment_index, len(intermediate_node_from_path_finder),
                   len(test_nodes))
            logging.info(f"{++counter}: {source} - {destination}:  {containment_index}")


def number_of_test_data():
    with open('./Path_Finder/training/data/DrugBank_aligned_with_KG2.json', 'r') as file:
        data = json.load(file)
    counter = 0
    for source, value in data.items():
        counter = counter + len(value['indication_NER_aligned'].items())

    logging.info(f"Number of test pairs: {counter}")


def insert(drug, disease, matched, containment_index, number_of_found_nodes, number_of_test_nodes):
    conn = sqlite3.connect('drug_disease.db')
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO DrugDiseaseMatch (drug, disease, matched, containment_index, number_of_found_nodes, number_of_test_nodes)
    VALUES (?, ?, ?, ?, ?, ?);
    """

    cursor.execute(insert_query,
                   (drug, disease, matched, containment_index, number_of_found_nodes, number_of_test_nodes))

    conn.commit()
    conn.close()


def create_table():
    conn = sqlite3.connect('drug_disease.db')

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


def read_all():
    conn = sqlite3.connect('drug_disease.db')

    query = "SELECT containment_index FROM DrugDiseaseMatch"
    data = pd.read_sql_query(query, conn)
    conn.close()
    return data


def depict_pdf():
    data = read_all()

    data = data[data['containment_index'] != 0]

    mean_containment_index = data['containment_index'].mean()
    std_dev_containment_index = data['containment_index'].std()

    plt.figure(figsize=(10, 6))
    sns.kdeplot(data['containment_index'], bw_adjust=0.5, fill=True, color='skyblue', alpha=0.6)
    plt.title("Probability Density Function of Containment Index (Non-Zero Values)")
    plt.xlabel("Containment Index")
    plt.ylabel("Density")
    plt.axvline(mean_containment_index, color='red', linestyle='--', label=f'Mean: {mean_containment_index:.2f}')
    plt.axvline(mean_containment_index + std_dev_containment_index, color='green', linestyle='--',
                label=f'Mean + 1 SD: {(mean_containment_index + std_dev_containment_index):.2f}')
    plt.axvline(mean_containment_index - std_dev_containment_index, color='purple', linestyle='--',
                label=f'Mean - 1 SD: {(mean_containment_index - std_dev_containment_index):.2f}')
    plt.legend()
    plt.show()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # create_table()
    # number_of_test_data()
    # run_tests()
    depict_pdf()
