import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from HugeGraphConverter import HugeGraphConverter
from OneByOneConverter import OneByOneConverter
from SuperNodeConverter import SuperNodeConverter


def paths_to_response_converter_factory(
        converter_name,
        paths,
        node_1_id,
        node_2_id,
        qnode_1_id,
        qnode_2_id,
        names
):
    if converter_name == 'huge_graph':
        return HugeGraphConverter(
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            names
        )
    elif converter_name == 'one_by_one':
        return OneByOneConverter(
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            names
        )
    else:
        return SuperNodeConverter(
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            names
        )
