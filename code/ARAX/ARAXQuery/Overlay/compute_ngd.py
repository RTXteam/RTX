# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import functools
import json
import math
import sys
import os
import sqlite3
import traceback
import numpy as np
from datetime import datetime
import itertools
import copy

import random
import time

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import overlay_utilities as ou
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.q_edge import QEdge
from openapi_server.models.retrieval_source import RetrievalSource
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../")
from RTXConfiguration import RTXConfiguration
random.seed(time.time())
RTXConfig = RTXConfiguration()


class ComputeNGD:

    #### Constructor
    def __init__(self, response, message, parameters):
        self.response = response
        self.message = message
        self.parameters = parameters
        self.global_iter = 0
        self.ngd_database_name = RTXConfig.curie_to_pmids_path.split('/')[-1]
        self.connection, self.cursor = self._setup_ngd_database()
        self.curie_to_pmids_map = dict()
        self.ngd_normalizer = 3.5e+7 * 20  # From PubMed home page there are 35 million articles (based on the information on https://pubmed.ncbi.nlm.nih.gov/ on 08/09/2023); avg 20 MeSH terms per article
        self.first_ngd_log = True

    def compute_ngd(self):
        """
        Iterate over all the edges in the knowledge graph, compute the normalized google distance and stick that info
        on the attributes
        :default: The default value to set for NGD if it returns a nan
        :return: response
        """
        if self.response.status != 'OK':  # Catches any errors that may have been logged during initialization
            self._close_database()
            return self.response
        parameters = self.parameters
        self.response.debug("Computing NGD")
        self.response.info("Computing the normalized Google distance: weighting edges based on subject/object node "
                           "co-occurrence frequency in PubMed abstracts")
        name = "normalized_google_distance"
        type = "EDAM-DATA:2526"
        default_value = self.parameters['default_value']
        url = "https://arax.ncats.io/api/rtx/v1/ui/#/PubmedMeshNgd"
        qg = self.message.query_graph
        kg = self.message.knowledge_graph
        ngd_description = """
        Normalized google distance is a metric based on edge subject/object node co-occurrence in abstracts of all [PubMed](https://pubmed.ncbi.nlm.nih.gov/) articles. 
        The formula can be found here on [wikipedia.](https://en.wikipedia.org/wiki/Normalized_Google_distance) 
        Where in this case f(x,y) is the number of PubMed abstracts both concepts apear in, f(x)/f(y) are the number of abstracts individual concepts apear in, and N is the number of pubmed articles times the average number of search terms per article (35 million * 20).
        """
        
        # if you want to add virtual edges, identify the subject/objects, decorate the edges, add them to the KG, and then add one to the QG corresponding to them
        # FW: changing this so if there is a virtual relation label but no subject and object then add edges for all subject object pairs in the quesry graph.
        if 'subject_qnode_key' not in parameters and 'object_qnode_key' not in parameters and 'virtual_relation_label' in parameters:
            seen_node_pairs = set()
            qgraph_edges = copy.deepcopy(list(qg.edges.values()))
            for query_edge in qgraph_edges:
                subject_qnode_key = query_edge.subject
                object_qnode_key = query_edge.object
                if subject_qnode_key < object_qnode_key:
                    qnode_key_pair = (subject_qnode_key,object_qnode_key)
                else:
                    qnode_key_pair = (object_qnode_key,subject_qnode_key)
                # FW: check if we have already added an edge for this pair
                if qnode_key_pair in seen_node_pairs:
                    pass
                else:
                    seen_node_pairs.add(qnode_key_pair)
                    # FW: Now add the edge for this qnode pair
                    # FW NOTE: If we decide to keep these changes we should really pull this out into a method as everything after this was copy pasted from below in the 'virtual_relation_label' in parameters section
                    node_pairs_to_evaluate = ou.get_node_pairs_to_overlay(subject_qnode_key, object_qnode_key, qg, kg, self.response)
                    # Grab PMID lists for all involved nodes
                    involved_curies = {curie for node_pair in node_pairs_to_evaluate for curie in node_pair}
                    canonicalized_curie_lookup = self._get_canonical_curies_map(list(involved_curies))
                    self.load_curie_to_pmids_data(canonicalized_curie_lookup.values())
                    added_flag = False  # check to see if any edges where added
                    self.response.debug(f"Looping through {len(node_pairs_to_evaluate)} node pairs and calculating NGD values")
                    # iterate over all pairs of these nodes, add the virtual edge, decorate with the correct attribute
                    for (subject_curie, object_curie) in node_pairs_to_evaluate:
                        # create the edge attribute if it can be
                        canonical_subject_curie = canonicalized_curie_lookup.get(subject_curie, subject_curie)
                        canonical_object_curie = canonicalized_curie_lookup.get(object_curie, object_curie)
                        ngd_value, pmid_set = self.calculate_ngd_fast(canonical_subject_curie, canonical_object_curie)
                        if np.isfinite(ngd_value):  # if ngd is finite, that's ok, otherwise, stay with default
                            edge_value = ngd_value
                        else:
                            edge_value = default_value
                        edge_attribute = EdgeAttribute(attribute_type_id=type, original_attribute_name=name, value=str(edge_value), value_url=url, description=ngd_description)  # populate the NGD edge attribute
                        if edge_attribute:
                            added_flag = True
                            # make the edge, add the attribute

                            # edge properties
                            now = datetime.now()
                            edge_type = "biolink:occurs_together_in_literature_with"
                            qedge_keys = [parameters['virtual_relation_label']]
                            relation = parameters['virtual_relation_label']
                            defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                            subject_key = subject_curie
                            object_key = object_curie

                            # now actually add the virtual edges in
                            id = f"{relation}_{self.global_iter}"
                            # ensure the id is unique
                            # might need to change after expand is implemented for TRAPI 1.0
                            while id in self.message.knowledge_graph.edges:
                                id = f"{relation}_{self.global_iter}.{random.randint(10**(9-1), (10**9)-1)}"
                            self.global_iter += 1
                            edge_attribute_list = [
                                edge_attribute,
                                EdgeAttribute(original_attribute_name="virtual_relation_label", value=relation, attribute_type_id="EDAM-OPERATION:0226"),
                                #EdgeAttribute(original_attribute_name="is_defined_by", value=is_defined_by, attribute_type_id="biolink:Unknown"),
                                # EdgeAttribute(original_attribute_name=None, value="infores:rtx-kg2", attribute_type_id="biolink:knowledge_source", attribute_source="infores:rtx-kg2", value_type_id="biolink:InformationResource"),
                                # EdgeAttribute(original_attribute_name=None, value="infores:arax", attribute_type_id="primary_knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                                EdgeAttribute(original_attribute_name="defined_datetime", value=defined_datetime, attribute_type_id="metatype:Datetime"),
                                # EdgeAttribute(original_attribute_name=None, value=provided_by, attribute_type_id="aggregator_knowledge_source", attribute_source=provided_by, value_type_id="biolink:InformationResource"),
                                EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges.")
                                #EdgeAttribute(original_attribute_name="confidence", value=confidence, attribute_type_id="biolink:ConfidenceLevel"),
                                #EdgeAttribute(original_attribute_name="weight", value=weight, attribute_type_id="metatype:Float"),
                                #EdgeAttribute(original_attribute_name="qedge_keys", value=qedge_keys)
                            ]
                            # edge = Edge(id=id, type=edge_type, relation=relation, subject_key=subject_key,
                            #             object_key=object_key,
                            #             is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                            #             provided_by=provided_by,
                            #             confidence=confidence, weight=weight, attributes=[edge_attribute], qedge_ids=qedge_ids)
                            
                            ## fix #1980 issue
                            temp_list = [f"PMID:{pmid}" for pmid in pmid_set]
                            if len(temp_list) != 0:
                                pmid_attribute = EdgeAttribute(attribute_type_id="biolink:publications", original_attribute_name="publications", value=temp_list)
                                edge_attribute_list.append(pmid_attribute)

                            #### FIXME temporary hack by EWD
                            #edge = Edge(predicate=edge_type, subject=subject_key, object=object_key, relation=relation,
                            #            attributes=edge_attribute_list)
                            retrieval_source = [
                                        RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                            ]
                            edge = Edge(predicate=edge_type, subject=subject_key, object=object_key,
                                        attributes=edge_attribute_list,sources=retrieval_source)
                            #edge.relation = relation
                            #### /end FIXME

                            edge.qedge_keys = qedge_keys
                            self.message.knowledge_graph.edges[id] = edge

                            #FW: check if results exist then modify them with the ngd edge
                            # import pdb;pdb.set_trace()
                            if self.message.results is not None and len(self.message.results) > 0:
                                ou.update_results_with_overlay_edge(subject_knode_key=subject_key, object_knode_key=object_key, kedge_key=id, message=self.message, log=self.response)

                    # Now add a q_edge the query_graph since I've added an extra edge to the KG
                    if added_flag:
                        # edge_type = parameters['virtual_edge_type']
                        edge_type = ["biolink:occurs_together_in_literature_with"]
                        relation = parameters['virtual_relation_label']
                        option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key, qg, self.response)
                        # q_edge = QEdge(id=relation, type=edge_type, relation=relation,
                        #                subject_key=subject_qnode_key, object_key=object_qnode_key,
                        #                option_group_id=option_group_id)

                        #### FIXME by EWD. For later fixing
                        #q_edge = QEdge(predicates=edge_type, relation=relation, subject=subject_qnode_key,
                        #           object=object_qnode_key, option_group_id=option_group_id)
                        q_edge = QEdge(predicates=edge_type, subject=subject_qnode_key,
                                   object=object_qnode_key, option_group_id=option_group_id)
                        q_edge.relation = relation
                        q_edge.filled = True
                        #### end FIXME

                        self.message.query_graph.edges[relation]=q_edge


                    self.response.info(f"NGD values successfully added to edges for the qnode pair ({subject_qnode_key},{object_qnode_key})")

        elif 'virtual_relation_label' in parameters:
            # Figure out which node pairs to compute NGD between
            subject_qnode_key = parameters['subject_qnode_key']
            object_qnode_key = parameters['object_qnode_key']
            node_pairs_to_evaluate = ou.get_node_pairs_to_overlay(subject_qnode_key, object_qnode_key, qg, kg, self.response)
            # Grab PMID lists for all involved nodes
            involved_curies = {curie for node_pair in node_pairs_to_evaluate for curie in node_pair}
            canonicalized_curie_lookup = self._get_canonical_curies_map(list(involved_curies))
            self.load_curie_to_pmids_data(canonicalized_curie_lookup.values())
            added_flag = False  # check to see if any edges where added
            self.response.debug(f"Looping through {len(node_pairs_to_evaluate)} node pairs and calculating NGD values")
            # iterate over all pairs of these nodes, add the virtual edge, decorate with the correct attribute
            for (subject_curie, object_curie) in node_pairs_to_evaluate:
                # create the edge attribute if it can be
                canonical_subject_curie = canonicalized_curie_lookup.get(subject_curie, subject_curie)
                canonical_object_curie = canonicalized_curie_lookup.get(object_curie, object_curie)
                ngd_value, pmid_set = self.calculate_ngd_fast(canonical_subject_curie, canonical_object_curie)
                if np.isfinite(ngd_value):  # if ngd is finite, that's ok, otherwise, stay with default
                    edge_value = ngd_value
                else:
                    edge_value = default_value
                edge_attribute = EdgeAttribute(attribute_type_id=type, original_attribute_name=name, value=str(edge_value), value_url=url, description=ngd_description)  # populate the NGD edge attribute

                if edge_attribute:
                    added_flag = True
                    # make the edge, add the attribute

                    # edge properties
                    now = datetime.now()
                    edge_type = "biolink:occurs_together_in_literature_with"
                    qedge_keys = [parameters['virtual_relation_label']]
                    relation = parameters['virtual_relation_label']
                    defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                    subject_key = subject_curie
                    object_key = object_curie
                    # now actually add the virtual edges in
                    id = f"{relation}_{self.global_iter}"
                    # ensure the id is unique
                    # might need to change after expand is implemented for TRAPI 1.0
                    while id in self.message.knowledge_graph.edges:
                        id = f"{relation}_{self.global_iter}.{random.randint(10**(9-1), (10**9)-1)}"
                    self.global_iter += 1
                    edge_attribute_list = [
                        edge_attribute,
                        EdgeAttribute(original_attribute_name="virtual_relation_label", value=relation, attribute_type_id="EDAM-OPERATION:0226"),
                        #EdgeAttribute(original_attribute_name="is_defined_by", value=is_defined_by, attribute_type_id="biolink:Unknown"),
                        # EdgeAttribute(original_attribute_name=None, value="infores:arax", attribute_type_id="biolink:knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                        # EdgeAttribute(original_attribute_name=None, value="infores:arax", attribute_type_id="primary_knowledge_source", attribute_source="infores:arax", value_type_id="biolink:InformationResource"),
                        EdgeAttribute(original_attribute_name="defined_datetime", value=defined_datetime, attribute_type_id="metatype:Datetime"),
                        # EdgeAttribute(original_attribute_name=None, value=provided_by, attribute_type_id="aggregator_knowledge_source", attribute_source=provided_by, value_type_id="biolink:InformationResource"),
                        EdgeAttribute(original_attribute_name=None, value=True, attribute_type_id="EDAM-DATA:1772", attribute_source="infores:arax", value_type_id="metatype:Boolean", value_url=None, description="This edge is a container for a computed value between two nodes that is not directly attachable to other edges.")
                        #EdgeAttribute(original_attribute_name="confidence", value=confidence, attribute_type_id="biolink:ConfidenceLevel"),
                        #EdgeAttribute(original_attribute_name="weight", value=weight, attribute_type_id="metatype:Float"),
                        #EdgeAttribute(original_attribute_name="qedge_keys", value=qedge_keys)
                    ]
                    # edge = Edge(id=id, type=edge_type, relation=relation, subject_key=subject_key,
                    #             object_key=object_key,
                    #             is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                    #             provided_by=provided_by,
                    #             confidence=confidence, weight=weight, attributes=[edge_attribute], qedge_ids=qedge_ids)

                    ## fix #1980 issue
                    temp_list = [f"PMID:{pmid}" for pmid in pmid_set]
                    if len(temp_list) != 0:
                        pmid_attribute = EdgeAttribute(attribute_type_id="biolink:publications", original_attribute_name="publications", value=temp_list)
                        edge_attribute_list.append(pmid_attribute)

                    #### FIXME temporary hack by EWD
                    #edge = Edge(predicate=edge_type, subject=subject_key, object=object_key, relation=relation,
                    #            attributes=edge_attribute_list)
                    retrieval_source = [
                                        RetrievalSource(resource_id="infores:arax", resource_role="primary_knowledge_source")
                            ]
                    edge = Edge(predicate=edge_type, subject=subject_key, object=object_key,
                                attributes=edge_attribute_list, sources=retrieval_source)
                    #edge.relation = relation
                    #### /end FIXME

                    edge.qedge_keys = qedge_keys
                    self.message.knowledge_graph.edges[id] = edge

                    #FW: check if results exist then modify them with the ngd edge
                    # import pdb;pdb.set_trace()
                    if self.message.results is not None and len(self.message.results) > 0:
                        ou.update_results_with_overlay_edge(subject_knode_key=subject_key, object_knode_key=object_key, kedge_key=id, message=self.message, log=self.response)

            # Now add a q_edge the query_graph since I've added an extra edge to the KG
            if added_flag:
                # edge_type = parameters['virtual_edge_type']
                edge_type = ["biolink:occurs_together_in_literature_with"]
                relation = parameters['virtual_relation_label']
                option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key, qg, self.response)
                # q_edge = QEdge(id=relation, type=edge_type, relation=relation,
                #                subject_key=subject_qnode_key, object_key=object_qnode_key,
                #                option_group_id=option_group_id)

                #### FIXME by EWD. For later fixing
                #q_edge = QEdge(predicates=edge_type, relation=relation, subject=subject_qnode_key,
                #           object=object_qnode_key, option_group_id=option_group_id)
                q_edge = QEdge(predicates=edge_type, subject=subject_qnode_key,
                           object=object_qnode_key, option_group_id=option_group_id)
                q_edge.relation = relation
                q_edge.filled = True
                #### end FIXME

                self.message.query_graph.edges[relation]=q_edge


            self.response.info("NGD values successfully added to edges")
        else:  # you want to add it for each edge in the KG
            # iterate over KG edges, add the information
            try:
                # Map all nodes to their canonicalized curies in one batch (need canonical IDs for the local NGD system)
                canonicalized_curie_map = self._get_canonical_curies_map([key for key in self.message.knowledge_graph.nodes.keys()])
                self.load_curie_to_pmids_data(canonicalized_curie_map.values())
                self.response.debug("Looping through edges and calculating NGD values")
                for edge in self.message.knowledge_graph.edges.values():
                    # Make sure the attributes are not None
                    if not edge.attributes:
                        edge.attributes = []  # should be an array, but why not a list?
                    # now go and actually get the NGD
                    subject_curie = edge.subject
                    object_curie = edge.object
                    canonical_subject_curie = canonicalized_curie_map.get(subject_curie, subject_curie)
                    canonical_object_curie = canonicalized_curie_map.get(object_curie, object_curie)
                    ngd_value, pmid_set = self.calculate_ngd_fast(canonical_subject_curie, canonical_object_curie)
                    if np.isfinite(ngd_value):  # if ngd is finite, that's ok, otherwise, stay with default
                        edge_value = ngd_value
                    else:
                        edge_value = default_value
                    ngd_edge_attribute = EdgeAttribute(attribute_type_id=type, original_attribute_name=name, value=str(edge_value), value_url=url, description=ngd_description)  # populate the NGD edge attribute
                    edge.attributes.append(ngd_edge_attribute)  # append it to the list of attributes
                    ## fix #1980 issue
                    temp_list = [f"PMID:{pmid}" for pmid in pmid_set]
                    if len(temp_list) != 0:
                        pmid_edge_attribute = EdgeAttribute(attribute_type_id="biolink:publications", original_attribute_name="ngd_publications", value_type_id="EDAM-DATA:1187", value=temp_list)
                        edge.attributes.append(pmid_edge_attribute)
            except Exception:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error("Something went wrong adding the NGD edge attributes")
            else:
                self.response.info("NGD values successfully added to edges")
            self._close_database()
        return self.response

    def load_curie_to_pmids_data(self, canonicalized_curies):
        self.response.debug("Extracting PMID lists from sqlite database for relevant nodes")
        curies = list(set(canonicalized_curies))
        chunk_size = 20000
        num_chunks = len(curies) // chunk_size if len(curies) % chunk_size == 0 else (len(curies) // chunk_size) + 1
        start_index = 0
        stop_index = chunk_size
        for num in range(num_chunks):
            chunk = curies[start_index:stop_index] if stop_index <= len(curies) else curies[start_index:]
            curie_list_str = ", ".join([f"'{curie}'" for curie in chunk if "'" not in curie])
            self.cursor.execute(f"SELECT * FROM curie_to_pmids WHERE curie in ({curie_list_str})")
            rows = self.cursor.fetchall()
            for row in rows:
                self.curie_to_pmids_map[row[0]] = json.loads(row[1])  # PMID list is stored as JSON string in sqlite db
            start_index += chunk_size
            stop_index += chunk_size

    def calculate_ngd_fast(self, subject_curie, object_curie):
        if subject_curie in self.curie_to_pmids_map and object_curie in self.curie_to_pmids_map:
            pubmed_ids_for_curies = [self.curie_to_pmids_map.get(subject_curie),
                                     self.curie_to_pmids_map.get(object_curie)]
            pubmed_id_set = set(self.curie_to_pmids_map.get(subject_curie)).intersection(set(self.curie_to_pmids_map.get(object_curie)))
            n_pmids = len(pubmed_id_set)
            if n_pmids > 30:
                if self.first_ngd_log:
                    #self.response.debug(f"{n_pmids} publications found for edge ({subject_curie})-[]-({object_curie}) limiting to 30...")
                    self.response.debug("More than 30 publications found for some edges limiting to 30...")
                    self.first_ngd_log = False
                # limited_pmids = set()
                # for i, val in enumerate(itertools.islice(pubmed_id_set, 30)):
                #     limited_pmids.add(val)
                # pubmed_id_set = limited_pmids
                pubmed_id_set = set([val for val in itertools.islice(pubmed_id_set, 30)])
            counts_res = self._compute_marginal_and_joint_counts(pubmed_ids_for_curies)
            return self._compute_multiway_ngd_from_counts(*counts_res), pubmed_id_set
        else:
            return math.nan, {}

    @staticmethod
    def _compute_marginal_and_joint_counts(concept_pubmed_ids: list[list[int]]) -> list:
        def reducer(pmids_intersec_cumul: set[int], pmids_next: set[int]) -> set[int]:
            return pmids_intersec_cumul.intersection(pmids_next)
        # Convert concept_pubmed_ids to a list of sets first
        pubmed_id_sets: list[set[int]] = [set(pmid_list) for pmid_list in concept_pubmed_ids]
        # Reduce over set[int], which is now type-consistent
        joint_pubmed_ids: set[int] = functools.reduce(reducer, pubmed_id_sets)
        marginal_counts = [len(s) for s in pubmed_id_sets]
        return [marginal_counts, len(joint_pubmed_ids)]

    def _compute_multiway_ngd_from_counts(self, marginal_counts: list[int],
                                          joint_count: int) -> float:
        # Make sure that things are within the right domain for the logs
        # Should also make sure things are not negative, but I'll just do this with a ValueError
        if None in marginal_counts:
            return math.nan
        elif 0 in marginal_counts or 0. in marginal_counts:
            return math.nan
        elif joint_count == 0 or joint_count == 0.:
            return math.nan
        else:
            try:
                return (max([math.log(count) for count in marginal_counts]) - math.log(joint_count)) / \
                   (math.log(self.ngd_normalizer) - min([math.log(count) for count in marginal_counts]))
            except ValueError:
                return math.nan

    def _get_canonical_curies_map(self, curies):
        self.response.debug("Canonicalizing curies of relevant nodes using NodeSynonymizer")
        synonymizer = NodeSynonymizer()
        try:
            canonicalized_node_info = synonymizer.get_canonical_curies(curies)
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Encountered a problem using NodeSynonymizer: {tb}", error_code=error_type.__name__)
            return {}
        else:
            canonical_curies_map = dict()
            for input_curie, node_info in canonicalized_node_info.items():
                if node_info:
                    canonical_curies_map[input_curie] = node_info.get('preferred_curie', input_curie)
                else:
                    canonical_curies_map[input_curie] = input_curie
            return canonical_curies_map

    def _setup_ngd_database(self):
        ngd_filepath = os.path.dirname(os.path.abspath(__file__)) + "/../../KnowledgeSources/NormalizedGoogleDistance/"
        db_path_local = f"{ngd_filepath}{self.ngd_database_name}"
        # Set up a connection to the database so it's ready for use
        try:
            connection = sqlite3.connect(db_path_local)
            cursor = connection.cursor()
        except Exception:
            self.response.error("Encountered an error connecting "
                                "to ngd sqlite database",
                                error_code="DatabaseSetupIssue")
            return None, None
        else:
            return connection, cursor

    def _close_database(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
