import json
import os
import sys
import logging
import matplotlib.pyplot as plt
import seaborn as sns

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from path_finder_service import get_paths_from_path_finder
from DrugDiseaseMatchedDB import DrugDiseaseMatchedDB


def extract_intermediate_nodes(paths):
    nodes = set()
    for path in paths:
        for i in range(0, len(path.links)):
            if i != 0 and (i != len(path.links) - 1):
                nodes.add(str(path.links[i]))
    return nodes


def run_tests(db, pathfinder_type):
    with open(os.path.dirname(os.path.abspath(__file__)) + '/../data/testing.json', 'r') as file:
        data = json.load(file)

    counter = 0
    zeros = 0
    for source, value in data.items():
        test_nodes = set(value['mechanistic_intermediate_nodes'].keys())
        for destination, _ in value['indication_NER_aligned'].items():
            counter += 1
            if db.has_pair(source, destination):
                continue
            if zeros < 0:
                zeros += 1
                continue
            paths = get_paths_from_path_finder(pathfinder_type, source, destination)
            intermediate_node_from_path_finder = extract_intermediate_nodes(paths)
            matched = intermediate_node_from_path_finder & test_nodes
            containment_index = len(matched) / len(test_nodes)
            db.insert(source, destination, str(matched), containment_index, len(intermediate_node_from_path_finder),
                      len(test_nodes))
            if containment_index == 0:
                zeros += 1
                logging.info(f"Zeros:  {zeros}")
            logging.info(f"{counter}: {source} - {destination}:  {containment_index}")


def number_of_test_data():
    with open(os.path.dirname(os.path.abspath(__file__)) + '/../data/testing.json', 'r') as file:
        data = json.load(file)
    counter = 0
    for source, value in data.items():
        counter = counter + len(value['indication_NER_aligned'].items())

    logging.info(f"Number of test pairs: {counter}")


def depict_pdf(db, file_name, zero_included = False):
    data = db.read_all()

    if not zero_included:
        logging.info(len(data[data['containment_index'] == 0]))
        data = data[data['containment_index'] != 0]

    mean_containment_index = data['containment_index'].mean()
    std_dev_containment_index = data['containment_index'].std()

    plt.figure(figsize=(10, 6))
    sns.kdeplot(data['containment_index'], bw_adjust=0.5, fill=True, color='skyblue', alpha=0.6)
    zero_inclusion_title = "Zero Values Excluded"
    if zero_included:
        zero_inclusion_title = "Zero Values Included"
    title = f"Probability Density Function of Containment Index ({zero_inclusion_title})"
    plt.title(title)
    plt.xlabel("Containment Index")
    plt.ylabel("Density")
    plt.axvline(mean_containment_index, color='red', linestyle='--', label=f'Mean: {mean_containment_index:.2f}')
    plt.axvline(mean_containment_index + std_dev_containment_index, color='green', linestyle='--',
                label=f'Mean + 1 SD: {(mean_containment_index + std_dev_containment_index):.2f}')
    plt.axvline(mean_containment_index - std_dev_containment_index, color='purple', linestyle='--',
                label=f'Mean - 1 SD: {(mean_containment_index - std_dev_containment_index):.2f}')
    plt.legend()
    plt.savefig(f"{file_name}-{zero_inclusion_title}.png")


def test(pathfinder_type, file_name):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    db = DrugDiseaseMatchedDB(f"drug_disease_{pathfinder_type}.db")
    db.create_table()
    # number_of_test_data()
    # run_tests(db, pathfinder_type)
    depict_pdf(db, file_name, False)
    depict_pdf(db, file_name, True)


if __name__ == "__main__":
    test("new", "node_degree")
