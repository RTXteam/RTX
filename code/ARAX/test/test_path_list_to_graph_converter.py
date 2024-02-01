import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery/Path_Finder/converter")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery/Path_Finder/model")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../..")

from Path import Path
from Node import Node

from SimpleGraphToContentGraphConverter import SimpleGraphToContentGraphConverter
from PathListToGraphConverter import PathListToGraphConverter
from EdgeExtractorFromPloverDB import EdgeExtractorFromPloverDB
from RTXConfiguration import RTXConfiguration


def test_path_list_to_graph_converter():
    source_name = "n01"
    destination_name = "n00"
    paths = [
        Path(0, [
            Node('DrugCentral:4904', 0, "", 0),
            Node('UNII:B72HH48FLU', 0.07100789377383077, "", 0),
            Node('MONDO:0005101', 0, "", 0)]),
        Path(0, [
            Node('DrugCentral:4904', 0, "", 0),
            Node('MONDO:0005011', 0.1483385445715853, "", 0),
            Node('MONDO:0005101', 0, "", 0)]),
        Path(0, [
            Node('DrugCentral:4904', 0, "", 0),
            Node('MESH:D007166', 0.21133088839106862, "", 0),
            Node('MONDO:0005101', 0, "", 0)]),
        Path(0, [
            Node('DrugCentral:4904', 0, "", 0),
            Node('MONDO:0005101', 0.22402580029455008, "", 0)]),
    ]

    nodes, edges = PathListToGraphConverter(source_name, destination_name).convert(paths)
    assert len(nodes) == 5
    assert len(edges) == 7

    rtx_config = RTXConfiguration()
    plover_url = rtx_config.plover_url
    SimpleGraphToContentGraphConverter(EdgeExtractorFromPloverDB(plover_url)).convert(nodes, edges)

def test_path_list_to_graph_converter_2():
    source_name = "n01"
    destination_name = "n00"
    paths = [
        Path(0, [
            Node('DrugCentral:4904', 0, "", 0),
            Node('UNII:B72HH48FLU', 0.07100789377383077, "", 0),
            Node('MONDO:0005101', 0, "", 0)]
             ),
        Path(0, [
            Node('DrugCentral:4904', 0, "", 0),
            Node('MONDO:0005011', 0.1483385445715853, "", 0),
            Node('UNII:B72HH48FLU', 0.02100789377383077, "", 0),
            Node('MONDO:0005101', 0, "", 0)]
             ),
        Path(0, [
            Node('DrugCentral:4904', 0, "", 0),
            Node('MONDO:0005101', 0.22402580029455008, "", 0)]
             ),
    ]

    nodes, edges = PathListToGraphConverter(source_name, destination_name).convert(paths)
    assert len(nodes) == 4
    assert len(edges) == 5
