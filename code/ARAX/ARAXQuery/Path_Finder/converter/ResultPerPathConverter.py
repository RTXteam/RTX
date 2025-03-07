import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../BiolinkHelper/")
from biolink_helper import BiolinkHelper

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Names import Names
from PathConverter import PathConverter


class ResultPerPathConverter:

    def __init__(
            self,
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            qnode_mid_id,
            names,
            edge_extractor,
            node_category_constraint
    ):
        self.paths = paths
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.qnode_mid_id = qnode_mid_id
        self.names = names
        self.edge_extractor = edge_extractor
        self.node_category_constraint = node_category_constraint

    def convert(self, response):
        biolink_helper = BiolinkHelper()
        descendants = biolink_helper.get_descendants(self.node_category_constraint)
        i = 0
        for path in self.paths:
            i = i + 1
            PathConverter(
                path,
                self.node_1_id,
                self.node_2_id,
                self.qnode_1_id,
                self.qnode_2_id,
                self.qnode_mid_id,
                Names(
                    result_name=f"{self.names.result_name}_{i}",
                    auxiliary_graph_name=f"{self.names.auxiliary_graph_name}_{i}",
                ),
                self.edge_extractor,
                path.compute_weight(),
                set(descendants)
            ).convert(response)
