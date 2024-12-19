import json
import os
import sys

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from repo.NGDRepository import NGDRepository
from repo.PloverDBRepo import PloverDBRepo
from model.Node import Node
from RTXConfiguration import RTXConfiguration


def read_training_data():
    with open('./../data/training.json', 'r') as file:
        data = json.load(file)
    training = []
    for key, value in data.items():
        related_CURIE = set()

        related_CURIE.add(key)
        indication_NER_aligned = [k for k in value["indication_NER_aligned"].keys()]
        mechanistic_intermediate_nodes = [k for k in value["mechanistic_intermediate_nodes"].keys()]
        indication_NER_aligned.extend(mechanistic_intermediate_nodes)

        related_CURIE.update(indication_NER_aligned)

        for rel in related_CURIE:
            training.append((rel, related_CURIE))

    return training


def get_neighbors_info(curie):
    ngd_repo = NGDRepository()
    repo = PloverDBRepo(plover_url=RTXConfiguration().plover_url)
    curie_ngd_list = ngd_repo.get_curie_ngd(curie)
    neighbors = repo.trapi_query(Node(id=curie))
    neighbors_id = [curie.id for curie in neighbors]
    node_pmids_length = ngd_repo.get_curies_pmid_length(neighbors_id)
    content_by_curie = {item: dict() for item in neighbors_id}
    for curie, num_of_pmids in node_pmids_length:
        content_by_curie[curie]["pmids"] = num_of_pmids
    for ngd in curie_ngd_list:
        content_by_curie[ngd[0]]["ngd"] = ngd[1]
    for node in neighbors:
        content_by_curie[node.id]["category"] = node.category
    return content_by_curie


if __name__ == "__main__":
    training_data = read_training_data()
    i = 0
    print(len(training_data))

    for key_nodes_pair in training_data:
        content_by_curie = get_neighbors_info(key_nodes_pair[0])
        i += 1
        print(i)
