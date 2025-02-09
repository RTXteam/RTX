import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from BidirectionalPathFinder import BidirectionalPathFinder


def pathfinder_factory(pathfinder_type: str):
    if pathfinder_type == "legacy":
        return BidirectionalPathFinder(
            "NGDSortedNeighborsRepo",
            logging
        )
    elif pathfinder_type == "new":
        return BidirectionalPathFinder(
            "MLRepo",
            logging
        )
    else:
        raise ValueError(f"Unknown animal_type '{pathfinder_type}'.")


def get_paths_from_path_finder(pathfinder_type, normalize_src_node_id, normalize_dst_node_id):
    path_finder = pathfinder_factory(pathfinder_type)
    try:
        paths = path_finder.find_all_paths(
            normalize_src_node_id,
            normalize_dst_node_id,
            hops_numbers=4
        )
    except Exception as error:
        logging.error(f"src: {normalize_src_node_id}\n"
                      f"dst: {normalize_dst_node_id}\n"
                      f"error: {error}")
        return set()

    return paths
