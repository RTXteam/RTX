import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Names import Names
from HugeGraphConverter import HugeGraphConverter


class OneByOneConverter:

    def __init__(
            self,
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            names
    ):
        self.paths = paths
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.names = names

    def convert(self, response):
        i = 0
        for path in self.paths:
            i += 1
            HugeGraphConverter(
                [path],
                self.node_1_id,
                self.node_2_id,
                self.qnode_1_id,
                self.qnode_2_id,
                Names(
                    q_edge_name=self.names.q_edge_name,
                    result_name=f"{self.names.result_name}_{i}",
                    auxiliary_graph_name=f"{self.names.auxiliary_graph_name}_{i}",
                    kg_edge_name=f"{self.names.kg_edge_name}_{i}"
                )
            ).convert(response)
