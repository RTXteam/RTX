import sys
import os
import multiprocessing

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import NEIGHBOR_LIMIT, NODE_DEGREE_LIMIT
from model.Node import Node
from model.Path import Path
from model.PathFinderModel import PathFinderModel
import queue
from repo.repo_factory import get_repo


def process_path(path_string):
    try:
        path_finder_model = PathFinderModel.deserialize(path_string)
        result = []
        if path_finder_model.path.path_limit > 0:
            last_link = path_finder_model.path.last()
            repo = get_repo(path_finder_model.repo_name)
            node_degree = repo.get_node_degree(last_link)
            if node_degree > NODE_DEGREE_LIMIT:
                return path_string, result, None
            neighbors = repo.get_neighbors(last_link, NEIGHBOR_LIMIT)
            for neighbor in neighbors:
                if neighbor not in path_finder_model.path.links:
                    new_path = path_finder_model.path.make_new_path(neighbor)
                    result.append(new_path.serialize())

        return path_string, result, None
    except Exception as e:
        return path_string, None, e


class BreadthFirstSearch:

    def __init__(self, repository_name, path_container, logger):
        self.repo_name = repository_name
        self.path_container = path_container
        self.logger = logger

    def traverse(self, source_id, hops_numbers=1):
        path_queue = queue.Queue()
        new_path = Path(hops_numbers, [Node(source_id, weight=1)])
        path_queue.put(new_path)
        self.path_container.add_new_path(new_path)

        if hops_numbers == 0:
            return

        num_cores = multiprocessing.cpu_count()

        with multiprocessing.Pool(num_cores) as pool:
            while not path_queue.empty():
                paths = []
                for _ in range(4 * num_cores):
                    if not path_queue.empty():
                        paths.append(PathFinderModel(self.repo_name, path_queue.get()).serialize())

                new_paths_list = pool.map(process_path, paths)

                for path_string, new_paths, exception in new_paths_list:
                    if exception:
                        self.logger.warning(f"Path {path_string} raised an exception: {exception}")
                    else:
                        for new_path in new_paths:
                            p = Path.deserialize(new_path)
                            path_queue.put(p)
                            self.path_container.add_new_path(p)
