#!/bin/env python3
# This class will add a virtual edge to the KG decorated with the Jaccard index value on it.
# relevant issue is #611
# will need to figure out DSL syntax to ensure that such edges will be added to the correct subject object nodes
# Need to decide if this will be done *only* on the local KG, or if the computation is going to be done via our underlying Neo4j KG
# for now, just do the computation on the local KG
import sys
import os
import traceback
import numpy as np
from datetime import datetime
import random
import time
random.seed(time.time())

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import overlay_utilities as ou

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
            for key, node in message.knowledge_graph.nodes.items():
                if parameters['intermediate_node_key'] in node.qnode_keys:
                    intermediate_nodes.add(key)  # add the intermediate node by it's identifier
                # also look for the subject node id
                if parameters['start_node_key'] in node.qnode_keys:
                    subject_node_key = key
                if parameters['end_node_key'] in node.qnode_keys:
                    end_node_to_intermediate_node_set[key] = set()

            # now iterate over the edges to look for the ones we need to add  # TODO: Here, I won't care which direction the edges are pointing
            for edge in message.knowledge_graph.edges.values():
                if edge.subject in intermediate_nodes:  # if subject is intermediate
                    if edge.object in end_node_to_intermediate_node_set:
                        end_node_to_intermediate_node_set[edge.object].add((edge.subject, edge.predicate))  # add subject
                elif edge.object in intermediate_nodes:  # if object is intermediate
                    if edge.subject in end_node_to_intermediate_node_set:
                        end_node_to_intermediate_node_set[edge.subject].add((edge.object, edge.predicate))  # add object

            # now compute the actual jaccard indexes
            denom = len(intermediate_nodes)
            end_node_to_jaccard = dict()
            for end_node_key in end_node_to_intermediate_node_set:
                # TODO: add code here if you care about edge types
                numerator = len(end_node_to_intermediate_node_set[end_node_key])
                jacc = numerator / float(denom)
                end_node_to_jaccard[end_node_key] = jacc

            # now add them all as virtual edges

            # edge properties
            j_iter = 0
            now = datetime.now()
            #edge_type = parameters['virtual_edge_type']
            edge_type = 'has_jaccard_index_with'
            qedge_keys = [parameters['virtual_relation_label']]
            relation = parameters['virtual_relation_label']
            is_defined_by = "ARAX"
            defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
            provided_by = "ARAX"
            confidence = None
            weight = None  # TODO: could make the jaccard index the weight
            try:
                subject_key = subject_node_key
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.warning(
                    f"subject node id: {parameters['start_node_key']} not found in the KG. Perhaps the KG is empty?")
                #self.response.error(tb, error_code=error_type.__name__)

            # edge attribute properties
            description = f"Jaccard index based on intermediate query nodes {parameters['intermediate_node_key']}"
            attribute_type = 'EDAM:data_1772'
            name = "jaccard_index"
            url = None

            # now actually add the virtual edges in
            for end_node_key, value in end_node_to_jaccard.items():
                edge_attribute = EdgeAttribute(type=attribute_type, name=name, value=value, url=url)
                # try to ensure a unique edge id
                id = f"J{j_iter}"
                # if by chance you get the same id then loop until a unique one is generated
                # probably a btter way of doing this but need to check how ids are generated in expand first
                while id in message.knowledge_graph.edges:
                    id = f"J{j_iter}.{random.randint(10**(9-1), (10**9)-1)}"
                j_iter += 1
                object_key = end_node_key
                # likely will need to fix this for TRAPI 1.0 after being able to test
                # Do these need a attribute type and url?
                edge_attribute_list = [
                    edge_attribute,
                    EdgeAttribute(name="is_defined_by", value=is_defined_by),
                    EdgeAttribute(name="defined_datetime", value=defined_datetime),
                    EdgeAttribute(name="provided_by", value=provided_by),
                    EdgeAttribute(name="confidence", value=confidence),
                    EdgeAttribute(name="weight", value=weight),
                    #EdgeAttribute(name="qedge_ids", value=qedge_ids)
                ]
                # edge = Edge(id=id, type=edge_type, relation=relation, subject_key=subject_key, object_key=object_key,
                #             is_defined_by=is_defined_by, defined_datetime=defined_datetime, provided_by=provided_by,
                #             confidence=confidence, weight=weight, attributes=[edge_attribute], qedge_ids=qedge_ids)
                edge = Edge(predicate=edge_type, subject=subject_key, object=object_key,
                            attributes=edge_attribute_list)
                edge.qedge_keys = qedge_keys
                message.knowledge_graph.edges[id] = edge

            # Now add a q_edge the query_graph since I've added an extra edge to the KG
            subject_qnode_key = parameters['start_node_key']
            object_qnode_key = parameters['end_node_key']
            option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key,
                                                                      self.message.query_graph, self.response)
            # q_edge = QEdge(id=relation, type=edge_type, relation=relation, subject_key=subject_qnode_key,
            #                object_key=object_qnode_key, option_group_id=option_group_id)  # TODO: ok to make the id and type the same thing?
            
            # Does not look to be a way to add option group ids to the new QEdge in TRAPI 1.0? Will error as written now
            q_edge = QEdge(predicate=edge_type, relation=relation, subject=subject_qnode_key,
                           object=object_qnode_key, option_group_id=option_group_id)
            # Need to fix this for TRAPI 1.0
            self.message.query_graph.edges[relation] = q_edge

            return self.response
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Something went wrong when computing the Jaccard index")
            self.response.error(tb, error_code=error_type.__name__)
