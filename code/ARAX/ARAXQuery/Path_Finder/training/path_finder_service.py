import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from BidirectionalPathFinder import BidirectionalPathFinder


def get_paths_from_path_finder(normalize_src_node_id, normalize_dst_node_id):
    path_finder = BidirectionalPathFinder(
        "NGDSortedNeighborsRepo",
        logging
    )
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
