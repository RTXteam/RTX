# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import functools
import json
import math
import subprocess
import sys
import os
import sqlite3
import traceback
import numpy as np
from datetime import datetime
from typing import List
import itertools

import random
import time
random.seed(time.time())

# relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import overlay_utilities as ou
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../OpenAPI/python-flask-server/")
from openapi_server.models.attribute import Attribute as EdgeAttribute
from openapi_server.models.edge import Edge
from openapi_server.models.q_edge import QEdge
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
RTXConfig.live = "Production"


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
        self.ngd_normalizer = 2.2e+7 * 20  # From PubMed home page there are 27 million articles; avg 20 MeSH terms per article

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
        self.response.debug(f"Computing NGD")
        self.response.info(f"Computing the normalized Google distance: weighting edges based on subject/object node "
                           f"co-occurrence frequency in PubMed abstracts")
        name = "normalized_google_distance"
        type = "EDAM:data_2526"
        value = self.parameters['default_value']
        url = "https://arax.ncats.io/api/rtx/v1/ui/#/PubmedMeshNgd"
        qg = self.message.query_graph
        kg = self.message.knowledge_graph

        # if you want to add virtual edges, identify the subject/objects, decorate the edges, add them to the KG, and then add one to the QG corresponding to them
        if 'virtual_relation_label' in parameters:
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
                    value = ngd_value
                edge_attribute = EdgeAttribute(type=type, name=name, value=str(value), url=url)  # populate the NGD edge attribute
                pmid_attribute = EdgeAttribute(type="biolink:publications", name="publications", value=[f"PMID:{pmid}" for pmid in pmid_set])
                if edge_attribute:
                    added_flag = True
                    # make the edge, add the attribute

                    # edge properties
                    now = datetime.now()
                    edge_type = "biolink:has_normalized_google_distance_with"
                    qedge_keys = [parameters['virtual_relation_label']]
                    relation = parameters['virtual_relation_label']
                    is_defined_by = "ARAX"
                    defined_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
                    provided_by = "ARAX"
                    confidence = None
                    weight = None  # TODO: could make the actual value of the attribute
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
                        pmid_attribute,
                        EdgeAttribute(name="is_defined_by", value=is_defined_by, type="ARAX_TYPE_PLACEHOLDER"),
                        EdgeAttribute(name="defined_datetime", value=defined_datetime, type="metatype:Datetime"),
                        EdgeAttribute(name="provided_by", value=provided_by, type="biolink:provided_by"),
                        #EdgeAttribute(name="confidence", value=confidence, type="biolink:ConfidenceLevel"),
                        #EdgeAttribute(name="weight", value=weight, type="metatype:Float"),
                        #EdgeAttribute(name="qedge_keys", value=qedge_keys)
                    ]
                    # edge = Edge(id=id, type=edge_type, relation=relation, subject_key=subject_key,
                    #             object_key=object_key,
                    #             is_defined_by=is_defined_by, defined_datetime=defined_datetime,
                    #             provided_by=provided_by,
                    #             confidence=confidence, weight=weight, attributes=[edge_attribute], qedge_ids=qedge_ids)
                    edge = Edge(predicate=edge_type, subject=subject_key, object=object_key, relation=relation,
                                attributes=edge_attribute_list)
                    edge.qedge_keys = qedge_keys
                    self.message.knowledge_graph.edges[id] = edge

            # Now add a q_edge the query_graph since I've added an extra edge to the KG
            if added_flag:
                #edge_type = parameters['virtual_edge_type']
                edge_type = "biolink:has_normalized_google_distance_with"
                relation = parameters['virtual_relation_label']
                option_group_id = ou.determine_virtual_qedge_option_group(subject_qnode_key, object_qnode_key, qg, self.response)
                # q_edge = QEdge(id=relation, type=edge_type, relation=relation,
                #                subject_key=subject_qnode_key, object_key=object_qnode_key,
                #                option_group_id=option_group_id)
                q_edge = QEdge(predicate=edge_type, relation=relation, subject=subject_qnode_key,
                           object=object_qnode_key, option_group_id=option_group_id)
                self.message.query_graph.edges[relation]=q_edge

            self.response.info(f"NGD values successfully added to edges")
        else:  # you want to add it for each edge in the KG
            # iterate over KG edges, add the information
            try:
                # Map all nodes to their canonicalized curies in one batch (need canonical IDs for the local NGD system)
                canonicalized_curie_map = self._get_canonical_curies_map([key for key in self.message.knowledge_graph.nodes.keys()])
                self.load_curie_to_pmids_data(canonicalized_curie_map.values())
                self.response.debug(f"Looping through edges and calculating NGD values")
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
                        value = ngd_value
                    ngd_edge_attribute = EdgeAttribute(type=type, name=name, value=str(value), url=url)  # populate the NGD edge attribute
                    pmid_edge_attribute = EdgeAttribute(type="biolink:publications", name="ngd_publications", value=[f"PMID:{pmid}" for pmid in pmid_set])
                    edge.attributes.append(ngd_edge_attribute)  # append it to the list of attributes
                    edge.attributes.append(pmid_edge_attribute)
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(tb, error_code=error_type.__name__)
                self.response.error(f"Something went wrong adding the NGD edge attributes")
            else:
                self.response.info(f"NGD values successfully added to edges")
            self._close_database()
            return self.response

    def load_curie_to_pmids_data(self, canonicalized_curies):
        self.response.debug(f"Extracting PMID lists from sqlite database for relevant nodes")
        curies = list(set(canonicalized_curies))
        chunk_size = 20000
        num_chunks = len(curies) // chunk_size if len(curies) % chunk_size == 0 else (len(curies) // chunk_size) + 1
        start_index = 0
        stop_index = chunk_size
        for num in range(num_chunks):
            chunk = curies[start_index:stop_index] if stop_index <= len(curies) else curies[start_index:]
            curie_list_str = ", ".join([f"'{curie}'" for curie in chunk])
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
                self.response.debug(f"{n_pmids} publications found for edge ({subject_curie})-[]-({object_curie}) limiting to 30...")
                limited_pmids = set()
                for i, val in enumerate(itertools.islice(pubmed_id_set, 30)):
                    limited_pmids.add(val)
                pubmed_id_set = limited_pmids
            counts_res = self._compute_marginal_and_joint_counts(pubmed_ids_for_curies)
            return self._compute_multiway_ngd_from_counts(*counts_res), pubmed_id_set
        else:
            return math.nan, {}

    @staticmethod
    def _compute_marginal_and_joint_counts(concept_pubmed_ids: List[List[int]]) -> list:
        return [list(map(lambda pmid_list: len(set(pmid_list)), concept_pubmed_ids)),
                len(functools.reduce(lambda pmids_intersec_cumul, pmids_next:
                                     set(pmids_next).intersection(pmids_intersec_cumul),
                                     concept_pubmed_ids))]

    def _compute_multiway_ngd_from_counts(self, marginal_counts: List[int],
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
        self.response.debug(f"Canonicalizing curies of relevant nodes using NodeSynonymizer")
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
        # Download the ngd database if there isn't already a local copy or if a newer version is available
        #db_path_local = f"{os.path.dirname(os.path.abspath(__file__))}/ngd/{self.ngd_database_name}"
        #db_path_remote = f"/data/orangeboard/databases/KG2.3.4/{self.ngd_database_name}"
        ngd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
        db_path_local = f"{ngd_filepath}{os.path.sep}{self.ngd_database_name}"
        db_path_remote = RTXConfig.curie_to_pmids_path
        if not os.path.exists(f"{db_path_local}"):
            self.response.debug(f"Downloading fast NGD database because no copy exists... (will take a few minutes)")
            #os.system(f"scp rtxconfig@arax.ncats.io:{db_path_remote} {db_path_local}")
            os.system(f"scp {RTXConfig.curie_to_pmids_username}@{RTXConfig.curie_to_pmids_host}:{RTXConfig.curie_to_pmids_path} {db_path_local}")
        else:
            last_modified_local = int(os.path.getmtime(db_path_local))
            last_modified_remote_byte_str = subprocess.check_output(f"ssh rtxconfig@arax.ncats.io 'stat -c %Y {db_path_remote}'", shell=True)
            last_modified_remote = int(str(last_modified_remote_byte_str, 'utf-8'))
            if last_modified_local < last_modified_remote:
                self.response.debug(f"Downloading new version of fast NGD database... (will take a few minutes)")
                #os.system(f"scp rtxconfig@arax.ncats.io:{db_path_remote} {db_path_local}")
                os.system(f"scp {RTXConfig.curie_to_pmids_username}@{RTXConfig.curie_to_pmids_host}:{RTXConfig.curie_to_pmids_path} {db_path_local}")
            else:
                self.response.debug(f"Confirmed local NGD database is current")
        # Set up a connection to the database so it's ready for use
        try:
            connection = sqlite3.connect(db_path_local)
            cursor = connection.cursor()
        except Exception:
            self.response.error(f"Encountered an error connecting to ngd sqlite database", error_code="DatabaseSetupIssue")
            return None, None
        else:
            return connection, cursor

    def _close_database(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

