import sys
import os
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.NGDSortedNeighborsRepo import NGDSortedNeighborsRepo
from repo.MLRepo import MLRepo
from repo.PloverDBRepo import PloverDBRepo


def get_repo(repo_name):
    if repo_name == "NGDSortedNeighborsRepo":
        return NGDSortedNeighborsRepo(
            PloverDBRepo(plover_url=RTXConfiguration().plover_url)
        )
    elif repo_name == "MLRepo":
        return MLRepo(
            PloverDBRepo(plover_url=RTXConfiguration().plover_url)
        )
    else:
        raise ValueError(f"Unknown animal_type '{repo_name}'.")



