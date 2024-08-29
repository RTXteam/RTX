class Names:

    def __init__(
            self,
            q_src_dest_edge_name,
            q_src_mid_edge_name,
            q_mid_dest_edge_name,
            result_name,
            auxiliary_graph_name,
            kg_src_dest_edge_name,
            kg_src_mid_edge_name,
            kg_mid_dest_edge_name
    ):
        self.q_src_dest_edge_name = q_src_dest_edge_name
        self.q_src_mid_edge_name = q_src_mid_edge_name
        self.q_mid_dest_edge_name = q_mid_dest_edge_name
        self.result_name = result_name
        self.auxiliary_graph_name = auxiliary_graph_name
        self.kg_src_dest_edge_name = kg_src_dest_edge_name
        self.kg_src_mid_edge_name = kg_src_mid_edge_name
        self.kg_mid_dest_edge_name = kg_mid_dest_edge_name
