import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Names import Names
from PathConverter import PathConverter

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node_binding import NodeBinding
from openapi_server.models.result import Result


class ResultPerPathConverter:

    def __init__(
            self,
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            names,
            edge_extractor,
    ):
        self.paths = paths
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.names = names
        self.edge_extractor = edge_extractor

    def convert(self, response):
        self.extract_edges(response)

        if response.envelope.message.results is None:
            response.envelope.message.results = []

        node_bindings = {
            self.qnode_1_id: [NodeBinding(id=self.node_1_id, attributes=[])],
            self.qnode_2_id: [NodeBinding(id=self.node_2_id, attributes=[])]
        }

        response.envelope.message.results.append(
            Result(
                id=self.names.result_name,
                analyses=[],
                node_bindings=node_bindings,
                essence=self.names.result_name
            )
        )

        i = 0
        for path in self.paths:
            i = i + 1
            PathConverter(
                path,
                self.qnode_1_id,
                self.qnode_2_id,
                Names(
                    result_name=f"{self.names.result_name}_{i}",
                    auxiliary_graph_name=f"{self.names.auxiliary_graph_name}_{i}",
                ),
                self.edge_extractor,
                path.compute_weight(),
            ).convert(response)

    def extract_edges(self, response):
        pairs = set()
        for path in self.paths:
            n1 = path.links[0]
            for i in range(1, len(path.links)):
                n2 = path.links[i]
                if f"{n2.id}--{n1.id}" not in pairs:
                    pairs.add(f"{n1.id}--{n2.id}")
                n1 = n2
            if len(pairs) > 200:
                pair_list = []
                for pair in pairs:
                    s = pair.split("--")
                    pair_list.append([s[0], s[1]])
                self.edge_extractor.get_edges(pair_list, response)
                pairs = set()
        if len(pairs) > 0:
            pair_list = []
            for pair in pairs:
                s = pair.split("--")
                pair_list.append([s[0], s[1]])
            self.edge_extractor.get_edges(pair_list, response)
