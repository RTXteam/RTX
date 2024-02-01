import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery/Path_Finder/converter")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../..")

from EdgeExtractorFromPloverDB import EdgeExtractorFromPloverDB
from RTXConfiguration import RTXConfiguration


def test_get_edges():
    rtx_config = RTXConfiguration()
    plover_url = rtx_config.plover_url
    edgeExtractor = EdgeExtractorFromPloverDB(plover_url)
    result = edgeExtractor.get_edges("n01", "DrugCentral:4904", "n00", "MONDO:0005101", "e00")

    assert len(result['nodes']) == 2
    assert len(result['edges']) == 1
