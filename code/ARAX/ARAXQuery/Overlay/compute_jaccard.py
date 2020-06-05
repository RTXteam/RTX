#!/bin/env python3
# This class will add a virtual edge to the KG decorated with the Jaccard index value on it.
# relevant issue is #611
# will need to figure out DSL syntax to ensure that such edges will be added to the correct source target nodes
# Need to decide if this will be done *only* on the local KG, or if the computation is going to be done via our underlying Neo4j KG
# for now, just do the computation on the local KG
import sys
import os
import traceback
import numpy as np
from datetime import datetime

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from swagger_server.models.edge_attribute import EdgeAttribute
from swagger_server.models.edge import Edge
from swagger_server.models.q_edge import QEdge

class ComputeJaccard:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters

    def compute_jaccard(self):
        message = self.message
        parameters = self.parameters
        self.response.debug(f"Computing Jaccard distance and adding this information as virtual edges")
        self.response.info(f"Computing Jaccard distance and adding this information as virtual edges")

        self.response.info("Getting all relevant nodes")
        # TODO: should I check that they're connected to the start node, or just assume that they are?
        # TODO: For now, assume that they are
        try:
            intermediate_nodes = set()
            end_node_to_intermediate_node_set = dict()  # keys will be end node curies, values will be tuples the (intermediate curie ids, edge_type)
            for node in message.knowledge_graph.nodes:
                if node.qnode_id == parameters['intermediate_node_id']:
                    intermediate_nodes.add(node.id)  # add the intermediate node by it's identifier
                # also look for the source node id
                if node.qnode_id == parameters['start_node_id']:
                    source_node_id = node.id
                if node.qnode_id == parameters['end_node_id']:
                    end_node_to_intermediate_node_set[node.id] = set()

            # now iterate over the edges to look for the ones we need to add  # TODO: Here, I won't care which direction the edges are pointing
            for edge in message.knowledge_graph.edges:
                if edge.source_id in intermediate_nodes:  # if source is intermediate
                    if edge.target_id in end_node_to_intermediate_node_set:
                        end_node_to_intermediate_node_set[edge.target_id].add((edge.source_id, edge.type))  # add source
                elif edge.target_id in intermediate_nodes:  # if target is intermediate
                    if edge.source_id in end_node_to_intermediate_node_set:
                        end_node_to_intermediate_node_set[edge.source_id].add((edge.target_id, edge.type))  # add target

            # now compute the actual jaccard indexes
            denom = len(intermediate_nodes)
            end_node_to_jaccard = dict()
            for end_node_id in end_node_to_intermediate_node_set:
                # TODO: add code here if you care about edge types
                numerator = len(end_node_to_intermediate_node_set[end_node_id])
                jacc = numerator / float(denom)
                end_node_to_jaccard[end_node_id] = jacc

            # now add them all as virtual edges

            # edge properties
            j_iter = 0
            now = datetime.now()
            #edge_type = parameters['virtual_edge_type']
            edge_type = 'has_jaccard_index_with'
            qedge_id = parameters['virtual_relation_label']
            relation = parameters['virtual_relation_label']
            is_defined_by = "ARAX"
            defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
            provided_by = "ARAX"
            confidence = None
            weight = None  # TODO: could make the jaccard index the weight
            try:
                source_id = source_node_id
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.warning(
                    f"Source node id: {parameters['start_node_id']} not found in the KG. Perhaps the KG is empty?")
                #self.response.error(tb, error_code=error_type.__name__)

            # edge attribute properties
            description = f"Jaccard index based on intermediate query nodes {parameters['intermediate_node_id']}"
            attribute_type = 'data:1772'
            name = "jaccard_index"
            url = None

            # now actually add the virtual edges in
            for end_node_id, value in end_node_to_jaccard.items():
                edge_attribute = EdgeAttribute(type=attribute_type, name=name, value=value, url=url)
                id = f"J{j_iter}"
                j_iter += 1
                target_id = end_node_id
                edge = Edge(id=id, type=edge_type, relation=relation, source_id=source_id, target_id=target_id,
                            is_defined_by=is_defined_by, defined_datetime=defined_datetime, provided_by=provided_by,
                            confidence=confidence, weight=weight, edge_attributes=[edge_attribute], qedge_id=qedge_id)
                message.knowledge_graph.edges.append(edge)

            # Now add a q_edge the query_graph since I've added an extra edge to the KG
            q_edge = QEdge(id=edge_type, type=edge_type, relation=relation, source_id=parameters['start_node_id'], target_id=parameters['end_node_id'])  # TODO: ok to make the id and type the same thing?
            self.message.query_graph.edges.append(q_edge)

            return self.response
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Something went wrong when computing the Jaccard index")
            self.response.error(tb, error_code=error_type.__name__)
