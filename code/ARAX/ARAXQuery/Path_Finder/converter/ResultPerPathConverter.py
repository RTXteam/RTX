import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PathConverter import PathConverter


class ResultPerPathConverter:

    def __init__(
            self,
            paths,
            node_1_id,
            node_2_id,
            qnode_1_id,
            qnode_2_id,
            aux_name,
            edge_extractor,
    ):
        self.paths = paths
        self.node_1_id = node_1_id
        self.node_2_id = node_2_id
        self.qnode_1_id = qnode_1_id
        self.qnode_2_id = qnode_2_id
        self.aux_name = aux_name
        self.edge_extractor = edge_extractor

    def convert(self, logger):
        self.extract_edges(logger)

        aux_graphs = {}
        analyses = []
        knowledge_graph = {'edges': {}, 'nodes': {}}

        i = 0
        for path in self.paths:
            i = i + 1
            analysis, aux_graph , kg = PathConverter(
                path,
                self.qnode_1_id,
                self.qnode_2_id,
                f"{self.aux_name}_{i}",
                self.edge_extractor,
                path.compute_weight(),
            ).convert(logger)
            aux_graphs[f"{self.aux_name}_{i}"] = aux_graph
            analyses.append(analysis)
            knowledge_graph['edges'].update(kg['edges'])
            knowledge_graph['nodes'].update(kg['nodes'])


        result = {
            "id": "result",
            "analyses": analyses,
            "node_bindings": {
                self.qnode_1_id: [
                    {
                        "id": self.node_1_id,
                        "attributes": []
                    }
                ],
                self.qnode_2_id: [
                    {
                        "id": self.node_2_id,
                        "attributes": []
                    }
                ]
            },
            "essence": "result",
            "resource_id": "infores:arax",
        }

        return result, aux_graphs, knowledge_graph

    def extract_edges(self, logger):
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
                self.edge_extractor.get_edges(pair_list, logger)
                pairs = set()
        if len(pairs) > 0:
            pair_list = []
            for pair in pairs:
                s = pair.split("--")
                pair_list.append([s[0], s[1]])
            self.edge_extractor.get_edges(pair_list, logger)
