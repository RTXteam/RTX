import sys
import os
import multiprocessing
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import NEIGHBOR_LIMIT, NODE_DEGREE_LIMIT
from model.Node import Node
from model.Path import Path
import queue
from repo.repo_factory import get_repo


def get_path(path):
    ids = path.split("_")
    links = []
    for i in range(0, len(ids)-1):
        links.append(Node(ids[i]))
    return Path(int(ids[-1]), links)

def process_path(path_string):
    path = get_path(path_string)
    result = []
    if path.path_limit > 0:
        last_link = path.last()
        repo = get_repo()
        node_degree = repo.get_node_degree(last_link)
        if node_degree > NODE_DEGREE_LIMIT:
            return result
        neighbors = repo.get_neighbors(last_link, NEIGHBOR_LIMIT)
        for neighbor in neighbors:
            if neighbor not in path.links:
                new_path = path.make_new_path(neighbor)
                result.append(str(new_path))

    return result

class BreadthFirstSearch:

    def __init__(self, repository_name, path_container):
        self.repo_name = repository_name
        self.path_container = path_container



    def traverse(self, source_id, hops_numbers=1):
        path_queue = queue.Queue()
        new_path = Path(hops_numbers, [Node(source_id, 0)])
        path_queue.put(new_path)
        self.path_container.add_new_path(new_path)

        if hops_numbers == 0:
            return

        num_cores = multiprocessing.cpu_count()

        with multiprocessing.Pool(num_cores) as pool:
            while not path_queue.empty():
                paths = []
                for _ in range(4*num_cores):
                    if not path_queue.empty():
                        paths.append(str(path_queue.get()))

                new_paths_list = pool.map(process_path, paths)

                for new_paths in new_paths_list:
                    for new_path in new_paths:
                        p = get_path(new_path)
                        path_queue.put(p)
                        self.path_container.add_new_path(p)
