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
from openapi_server.models.retrieval_source import RetrievalSource
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
            end_node_to_intermediate_node_set = dict()
            subject_node_key = dict()
            # keys will be end node curies, values will be tuples the (intermediate curie ids, edge_type)
            for key, node in message.knowledge_graph.nodes.items():
                if parameters['intermediate_node_key'] in node.qnode_keys:
                    intermediate_nodes.add(key)  # add the intermediate node by it's identifier
                # also look for the subject node id
                if parameters['start_node_key'] in node.qnode_keys:
                    subject_node_key[key] = set()
                if parameters['end_node_key'] in node.qnode_keys:
                    end_node_to_intermediate_node_set[key] = set()

            # now iterate over the edges to look for the ones we need to add  # TODO: Here, I won't care which direction the edges are pointing
            for edge in message.knowledge_graph.edges.values():
                if edge.subject in intermediate_nodes:  # if subject is intermediate
                    if edge.object in end_node_to_intermediate_node_set:
                        # end_node_to_intermediate_node_set[edge.object].add((edge.subject, edge.predicate))  # add subjectend_node_to_intermediate_node_set[edge.object].add((edge.subject, edge.predicate))
                        # FW: Old way was to add in unique predicate, node id pairs but then count total number of intermediate nodes.
                        # I've now changed this to add only node ids on both but we could change back but instead count all pairs for the demoninator.
                        end_node_to_intermediate_node_set[edge.object].add(edge.subject)
                    elif edge.object in subject_node_key:
                        subject_node_key[edge.object].add(edge.subject)
                elif edge.object in intermediate_nodes:  # if object is intermediate
                    if edge.subject in end_node_to_intermediate_node_set:
                        # end_node_to_intermediate_node_set[edge.subject].add((edge.object, edge.predicate))  # add object
                        end_node_to_intermediate_node_set[edge.subject].add(edge.object)
                    elif edge.subject in subject_node_key:
                        subject_node_key[edge.subject].add(edge.object)

            # now compute the actual jaccard indexes
            end_node_to_jaccard = dict()
            for end_node_key in end_node_to_intermediate_node_set:
                end_node_to_jaccard[end_node_key] = dict()
                for start_node_key in subject_node_key:
                # TODO: add code here if you care about edge types
                    numerator = len(end_node_to_intermediate_node_set[end_node_key].intersection(subject_node_key[start_node_key]))
                    jacc = numerator/ float(len(subject_node_key[start_node_key]))
                    end_node_to_jaccard[end_node_key][start_node_key] = jacc

            # now add them all as virtual edges

            # edge properties
            j_iter = 0
            now = datetime.now()
            #edge_type = parameters['virtual_edge_type']
            edge_type = 'biolink:has_jaccard_index_with'
            qedge_keys = [parameters['virtual_relation_label']]
            relation = parameters['virtual_relation_label']
            is_defined_by = "ARAX"
            defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
            provided_by = "infores:arax"
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
            attribute_type = 'EDAM-DATA:1772'
            name = "jaccard_index"
            url = None

            # now actually add the virtual edges in
            for end_node_key, start_nodes in end_node_to_jaccard.items():
                for subject_key, value in start_nodes.items():
                    edge_attribute = EdgeAttribute(attribute_type_id=attribute_type, original_attribute_name=name, value=value, value_url=url)
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
                    retrieval_source = [
                                        RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                    ]


                    edge_attribute_list = [
                        edge_attribute,
                        EdgeAttribute(original_attribute_name="virtual_relation_label", value=relation, attribute_type_id="EDAM-OPERATION:0226"),
                        # EdgeAttribute(original_attribute_name=None, value="infores:arax", attribute_type_id="biolink:knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                        # EdgeAttribute(original_attribute_name=None, value="infores:arax", attribute_type_id="primary_knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                        EdgeAttribute(original_attribute_name="defined_datetime", value=defined_datetime, attribute_type_id="metatype:Datetime"),
                        # EdgeAttribute(original_attribute_name=None, value=provided_by, attribute_type_id="aggregator_knowledge_source", attribute_source=provided_by, value_type_id="biolink:InformationResource"),
                        EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges.")
                    ]

                    # edge = Edge(id=id, type=edge_type, relation=relation, subject_key=subject_key, object_key=object_key,
                    #             is_defined_by=is_defined_by, defined_datetime=defined_datetime, provided_by=provided_by,
                    #             confidence=confidence, weight=weight, attributes=[edge_attribute], qedge_ids=qedge_ids)
                    edge = Edge(predicate=edge_type, subject=subject_key, object=object_key,
                                attributes=edge_attribute_list, sources=retrieval_source)
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
            q_edge = QEdge(predicates=[edge_type], subject=subject_qnode_key,
                           object=object_qnode_key, option_group_id=option_group_id)
            q_edge.relation = relation
            q_edge.filled = True
            # Need to fix this for TRAPI 1.0
            self.message.query_graph.edges[relation] = q_edge

            return self.response
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Something went wrong when computing the Jaccard index")
            self.response.error(tb, error_code=error_type.__name__)
