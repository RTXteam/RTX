import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/model")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import NEIGHBOR_LIMIT, NUMBER_OF_WORKER_THREADS
from Node import Node
from Path import Path
import queue
import concurrent.futures


class BreadthFirstSearch:

    def __init__(self, repository, path_container):
        self.repo = repository
        self.path_container = path_container

    def process_path(self, path):
        result = []
        if path.path_limit > 0:
            last_link = path.last()
            neighbors = self.repo.get_neighbors(last_link, NEIGHBOR_LIMIT)
            for neighbor in neighbors:
                if neighbor not in path.links:
                    new_path = path.make_new_path(neighbor)
                    result.append(new_path)

        return result

    def traverse(self, source_id, hops_numbers=1):
        path_queue = queue.Queue()
        new_path = Path(hops_numbers, [Node(source_id, 0)])
        path_queue.put(new_path)
        self.path_container.add_new_path(new_path)

        if hops_numbers == 0:
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=NUMBER_OF_WORKER_THREADS) as executor:
            while not path_queue.empty():
                paths = []
                for _ in range(NUMBER_OF_WORKER_THREADS):
                    if not path_queue.empty():
                        paths.append(path_queue.get())

                new_paths_list = executor.map(self.process_path, paths)

                for new_paths in new_paths_list:
                    for new_path in new_paths:
                        path_queue.put(new_path)
                        self.path_container.add_new_path(new_path)
