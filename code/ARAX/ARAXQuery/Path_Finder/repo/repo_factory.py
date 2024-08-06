import sys
import os
from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from repo.NGDSortedNeighborsRepo import NGDSortedNeighborsRepo
from repo.PloverDBRepo import PloverDBRepo


def get_repo():
    return NGDSortedNeighborsRepo(
        PloverDBRepo(plover_url=RTXConfiguration().plover_url)
    )
