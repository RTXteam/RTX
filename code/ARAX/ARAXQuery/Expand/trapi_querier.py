import copy
import json
import sys
import os
import time
from collections import defaultdict
import math

import requests
from typing import cast, Any, Iterable, Optional, Union

import requests_cache

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import Expand.expand_utilities as eu
from Expand.expand_utilities import QGOrganizedKnowledgeGraph
from Expand.kp_selector import KPSelector
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_messenger import ARAXMessenger
from trapi_query_cacher import KPQueryCacher
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.node import Node  # noqa: E402
from openapi_server.models.edge import Edge  # noqa: E402
from openapi_server.models.q_node import QNode  # noqa: E402
from openapi_server.models.q_edge import QEdge  # noqa: E402
from openapi_server.models.query_graph import QueryGraph  # noqa: E402
from openapi_server.models.result import Result  # noqa: E402
from openapi_server.models.attribute import Attribute  # noqa: E402
from openapi_server.models.retrieval_source import RetrievalSource  # noqa: E402
from openapi_server.models.auxiliary_graph import AuxiliaryGraph  # noqa: E402


def _remove_attributes_with_invalid_values(response_json: dict,
                                           kp_curie: str,
                                           log: ARAXResponse) -> \
                                           list[object]:
    r = response_json
    count_att_dropped = 0
    for ekey, edge_obj in r['message']['knowledge_graph']['edges'].items():
        new_attributes = []
        if 'attributes' in edge_obj:
            for attribute_obj in edge_obj['attributes']:
                att_source = attribute_obj.get('attribute_source', 'Unknown')
                if 'value' in attribute_obj:
                    value_obj = attribute_obj['value']
                    if isinstance(value_obj, float) and \
                       ((math.isinf(value_obj)) or math.isnan(value_obj)):
                        count_att_dropped += 1
                        log.warning(f"from KP {kp_curie}, "
                                    f"from attribute source {att_source}, "
                                    f"in edge {ekey}, "
                                    f"found invalid value {value_obj}; "
                                    "dropping attribute")
                        continue
                new_attributes.append(attribute_obj)
            edge_obj['attributes'] = new_attributes
    if count_att_dropped > 0:
        log.warning(f"For response from KP {kp_curie}, "
                    f"total number of attributes dropped: {count_att_dropped}")
    return [r, count_att_dropped]


def _summarize_set_elements(x: Iterable[str]) -> str:
    """
    Return a comma-delimited representation of the first 10 elements of Iterable[str].

    - If the set has fewer than 11 elements, return all elements.
    - Otherwise return the first 10 elements in lexicographic order followed by an ellipsis.
    """
    sorted_x = sorted(x)

    if len(sorted_x) <= 10:
        return "[" + ", ".join(sorted_x) + "]"

    return "[" + ", ".join(sorted_x[:10]) + ", ... ]"


class TRAPIQuerier:

    def __init__(self, response_object: ARAXResponse,
                 kp_name: str,
                 user_specified_kp: bool,
                 kp_timeout: Optional[int],
                 kp_selector: Optional[KPSelector] = None):
        self.log = response_object
        self.kp_infores_curie = kp_name
        self.user_specified_kp = user_specified_kp
        self.kp_timeout = kp_timeout
        if kp_selector is None:
            kp_selector = KPSelector()
        self.kp_selector = kp_selector
        self.kp_endpoint = kp_selector.kp_urls[self.kp_infores_curie]
        self.qnodes_with_single_id: dict[str, str] = {}  # This is set during the processing of each query
        self.arax_infores_curie = "infores:arax"
        self.arax_retrieval_source = RetrievalSource(resource_id=self.arax_infores_curie,
                                                     resource_role="aggregator_knowledge_source",
                                                     upstream_resource_ids=[self.kp_infores_curie])

    async def answer_one_hop_query_async(
            self, query_graph: QueryGraph,
            be_creative_treats: bool = False
    ) -> tuple[QGOrganizedKnowledgeGraph,
               dict[str, AuxiliaryGraph] | None]:
        """
        This function answers a one-hop (single-edge) query using the specified KP.
        :param query_graph: A TRAPI query graph.
        :param be_creative_treats: If true, will query KP for higher-level treats-type predicates instead of just
                                    'treats'. Any higher-level returned edges will later be altered appropriately
                                    in ARAX_expander.py.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = copy.deepcopy(query_graph)  # Create a copy so we don't modify the original
        qedge_key = next(qedge_key for qedge_key in qg_copy.edges)
        self.qnodes_with_single_id = {qnode_key: qnode.ids[0] for qnode_key, qnode in query_graph.nodes.items()
                                      if qnode.ids and len(qnode.ids) == 1}
        if self.qnodes_with_single_id:
            self.log.debug(f"{self.kp_infores_curie}: Qnodes with an implied parent query ID are: {self.qnodes_with_single_id}")

        self._verify_is_one_hop_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg, None

        # Verify that the KP accepts these predicates/categories/prefixes
        if self.kp_infores_curie != "infores:rtx-kg2":
            if self.user_specified_kp:  # This is already done if expand chose the KP itself
                if not self.kp_selector.kp_accepts_single_hop_qg(qg_copy, self.kp_infores_curie):
                    log.error(f"{self.kp_infores_curie} cannot answer queries with the specified categories/predicates",
                              error_code="UnsupportedQG")
                    return final_kg, None

        # Convert the QG so that it uses curies with prefixes the KP likes
        qg_copy = self.kp_selector.make_qg_use_supported_prefixes(qg_copy, self.kp_infores_curie, log)
        if not qg_copy:  # Means no equivalent curies with supported prefixes were found
            skipped_message = "No equivalent curies with supported prefixes found"
            log.update_query_plan(qedge_key, self.kp_infores_curie, "Skipped", skipped_message)
            return final_kg, None

        # Treat this as a creative 'treats' query
        if be_creative_treats:
            for qedge in qg_copy.edges.values():  # Note there's only ever one qedge per QG here
                qedge.predicates = list(set(qedge.predicates).union({"biolink:treats_or_applied_or_studied_to_treat",
                                                                     "biolink:applied_to_treat"}))  # Just to be safe
                log.info(f"For querying {self.kp_infores_curie}, edited {qedge_key} to use higher treats-type "
                         f"predicates: {qedge.predicates}")

        # Answer the query using the KP and load its answers into our object model
        return await self._answer_query_using_kp_async(qg_copy)

    def answer_one_hop_query(
            self, query_graph: QueryGraph
    ) -> tuple[QGOrganizedKnowledgeGraph,
               dict[str, AuxiliaryGraph] | None]:
        """
        This function answers a one-hop (single-edge) query using the specified KP.
        :param query_graph: A TRAPI query graph.
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
                results for the query. (Organized by QG IDs.)
        """
        # TODO: Delete this method once we're ready to let go of the multiprocessing (vs. asyncio) option
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = copy.deepcopy(query_graph)  # Create a copy so we don't modify the original
        qedge_key = next(qedge_key for qedge_key in qg_copy.edges)


        self._verify_is_one_hop_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg, None

        # Verify that the KP accepts these predicates/categories/prefixes
        if self.kp_infores_curie != "infores:rtx-kg2":
            if self.user_specified_kp:  # This is already done if expand chose the KP itself
                if not self.kp_selector.kp_accepts_single_hop_qg(qg_copy, self.kp_infores_curie):
                    log.error(f"{self.kp_infores_curie} cannot answer queries with the specified categories/predicates",
                              error_code="UnsupportedQG")
                    return final_kg, None

        # Convert the QG so that it uses curies with prefixes the KP likes
        qg_copy = self.kp_selector.make_qg_use_supported_prefixes(qg_copy, self.kp_infores_curie, log)
        if not qg_copy:  # Means no equivalent curies with supported prefixes were found
            skipped_message = "No equivalent curies with supported prefixes found"
            log.update_query_plan(qedge_key, self.kp_infores_curie, "Skipped", skipped_message)
            return final_kg, None

        # Answer the query using the KP and load its answers into our object model
        return self._answer_query_using_kp(qg_copy)

    def answer_single_node_query(
            self, single_node_qg: QueryGraph
    ) -> QGOrganizedKnowledgeGraph:
        """
        This function answers a single-node (edge-less) query using the specified KP.
        :param single_node_qg: A TRAPI query graph containing a single node (no edges).
        :return: An (almost) TRAPI knowledge graph containing all of the nodes and edges returned as
           results for the query. (Organized by QG IDs.)
        """
        log = self.log
        final_kg = QGOrganizedKnowledgeGraph()
        qg_copy = copy.deepcopy(single_node_qg)

        # Verify this query graph is valid, preprocess it for the KP's needs, and make sure it's answerable by the KP
        self._verify_is_single_node_query_graph(qg_copy)
        if log.status != 'OK':
            return final_kg

        # Answer the query using the KP and load its answers into our object model
        final_kg, _ = self._answer_query_using_kp(qg_copy)
        return final_kg

    def _verify_is_one_hop_query_graph(self, query_graph: QueryGraph):
        if len(query_graph.edges) != 1:
            self.log.error(f"answer_one_hop_query() was passed a query graph that is not one-hop: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) > 2:
            self.log.error(f"answer_one_hop_query() was passed a query graph with more than two nodes: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")
        elif len(query_graph.nodes) < 2:
            self.log.error(f"answer_one_hop_query() was passed a query graph with less than two nodes: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")

    def _verify_is_single_node_query_graph(self, query_graph: QueryGraph):
        if len(query_graph.edges) > 0:
            self.log.error(f"answer_single_node_query() was passed a query graph that has edges: "
                           f"{query_graph.to_dict()}", error_code="InvalidQuery")

    def _get_kg_to_qg_mappings_from_results(
            self,
            results: list[Result],
            qg: QueryGraph
    ) -> tuple[dict[str, dict[str, set[str]]], dict[str, set[str]]]:
        """
        This function returns a dictionary in which one can lookup which qnode_keys/qedge_keys a given node/edge
        fulfills. Like: {"nodes": {"PR:11": {"n00"}, "MESH:22": {"n00", "n01"} ... }, "edges": { ... }}
        """
        qnodes_with_multiple_ids = {qnode_key for qnode_key, qnode in qg.nodes.items() if qnode.ids and len(qnode.ids) > 1}
        qnodes_with_single_id = {qnode_key for qnode_key, qnode in qg.nodes.items() if qnode.ids and len(qnode.ids) == 1}
        qnode_key_mappings = defaultdict(set)
        kg_id_to_parent_query_id_map = defaultdict(set)
        qedge_key_mappings = defaultdict(set)
        for result in results:
            # Record mappings from the returned node to the parent curie listed in the QG that it is fulfilling
            for qnode_key, node_bindings in result.node_bindings.items():
                query_node_ids = set(eu.convert_to_list(qg.nodes[qnode_key].ids))
                for node_binding in node_bindings:
                    kg_id = node_binding.id
                    qnode_key_mappings[kg_id].add(qnode_key)
                    # Handle case where the KP does return a query_id
                    if node_binding.query_id:
                        if node_binding.query_id in query_node_ids:
                            kg_id_to_parent_query_id_map[kg_id].add(node_binding.query_id)
                        else:
                            self.log.warning(f"{self.kp_infores_curie} returned a NodeBinding.query_id ({node_binding.query_id})"
                                             f" for {qnode_key} that is not in {qnode_key}'s ids in the QG sent "
                                             f"to {self.kp_infores_curie}. This is invalid TRAPI. Skipping this binding.")
                    # Handle case where KP does NOT return a query_id (may or may not be valid TRAPI)
                    else:
                        if qnode_key in qnodes_with_single_id:
                            implied_parent_id = list(query_node_ids)[0]
                            kg_id_to_parent_query_id_map[kg_id].add(implied_parent_id)
                        elif qnode_key in qnodes_with_multiple_ids:
                            if kg_id in query_node_ids:
                                implied_parent_id = kg_id
                                kg_id_to_parent_query_id_map[kg_id].add(implied_parent_id)
                            else:
                                self.log.warning(f"{self.kp_infores_curie} returned a node binding for {qnode_key} that does "
                                                 f"not include a query_id, and {qnode_key} has multiple ids in the "
                                                 f"query sent to {self.kp_infores_curie}, none of which are the KG ID ({kg_id})."
                                                 f" This is invalid TRAPI. Skipping this binding.")

            for analysis in result.analyses:  # TODO: Maybe later extract Analysis support graphs from KPs?
                if analysis.edge_bindings:
                    for qedge_key, edge_bindings in analysis.edge_bindings.items():
                        for edge_binding in edge_bindings:
                            kg_id = edge_binding.id
                            qedge_key_mappings[kg_id].add(qedge_key)

        return {"nodes": qnode_key_mappings, "edges": qedge_key_mappings}, kg_id_to_parent_query_id_map



    async def _answer_query_using_kp_async(
            self, query_graph: QueryGraph
    ) -> tuple[QGOrganizedKnowledgeGraph,
               dict[str, AuxiliaryGraph] | None]:
        request_body = self._get_prepped_request_body(query_graph)
        query_sent = copy.deepcopy(request_body)
        query_timeout = self._get_query_timeout_length()
        if not query_graph.edges:
            raise ValueError("query graph has no edges")
        qedge_key = next(iter(query_graph.edges))
        num_input_curies = max(
            (len(eu.convert_to_list(qnode.ids)) for qnode in query_graph.nodes.values()),
            default=0,
        )
        waiting_message = f"Query with {num_input_curies} curies sent: waiting for response"
        self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Waiting", waiting_message, query=query_sent)
        start = time.time()
        self.log.debug(f"{self.kp_infores_curie}: Sending query to {self.kp_infores_curie} API ({self.kp_endpoint}) with timeout={query_timeout}")

        # Send the query graph to the KP's TRAPI API
        cacher = KPQueryCacher()
        r = None
        try:
            response_data, http_code, elapsed_time, error = await cacher.get_result(f"{self.kp_endpoint}/query",
                                                                                    request_body,
                                                                                    kp_curie=self.kp_infores_curie,
                                                                                    timeout=query_timeout,
                                                                                    async_session=True)
            if http_code == 200:
                r = response_data

            elif http_code == -1:
                wait_time = round(time.time() - start, 2)
                timeout_message = f"Query timed out after {wait_time} seconds"
                self.log.warning(f"{self.kp_infores_curie}: {timeout_message}")
                self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Timed out", timeout_message)
                return QGOrganizedKnowledgeGraph(), None

            else:
                wait_time = round(time.time() - start, 2)
                http_error_message = f"Returned HTTP error {http_code} after {wait_time} seconds"
                self.log.warning(f"{self.kp_infores_curie}: {http_error_message}. Query sent to KP was: {request_body}")
                self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Error", http_error_message)
                return QGOrganizedKnowledgeGraph(), None

        except Exception as ex:
            wait_time = round(time.time() - start, 2)
            exception_message = f"Request threw exception after {wait_time} seconds: {type(ex).__name__}: {ex}"
            self.log.warning(f"{self.kp_infores_curie}: {exception_message}")
            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Error", exception_message)
            return QGOrganizedKnowledgeGraph(), None

        if not isinstance(r, dict):
            self.log.warning(f"{self.kp_endpoint}: response is not a dict; got {type(r).__name__}")
            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Error", "Response is malformed")
            return QGOrganizedKnowledgeGraph(), None
        message = r.get('message')
        if not isinstance(message, dict):
            self.log.warning(f"{self.kp_endpoint}: response.message is not a dict; got {type(message).__name__}")
            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Warning", "Response message is malformed")
            return QGOrganizedKnowledgeGraph(), None
        kg = message.get('knowledge_graph')
        if not isinstance(kg, dict):
            self.log.warning(f"{self.kp_endpoint}: response.message.knowledge_graph is not a dict; got {type(kg).__name__}")
            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Warning", "Message KG is malformed")
            return QGOrganizedKnowledgeGraph(), None
        edges = kg.get('edges')
        if not isinstance(edges, dict):
            self.log.warning(f"{self.kp_endpoint}: response.message.knowledge_graph.edges is not a dict; got {type(edges).__name__}")
            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Warning", "KG edges are malformed")
            return QGOrganizedKnowledgeGraph(), None
        nodes = kg.get('nodes')
        if not isinstance(nodes, dict):
            self.log.warning(f"{self.kp_endpoint}: response.message.knowledge_graph.nodes is not a dict; got {type(nodes).__name__}")
            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Warning", "KG nodes are malformed")
            return QGOrganizedKnowledgeGraph(), None
        r, cd = _remove_attributes_with_invalid_values(
            r,
            self.kp_infores_curie,
            self.log
        )
        if not isinstance(r, dict):
            self.log.warning(f"{self.kp_endpoint}: cleaned response is not a dict; got {type(r).__name__}")
            self.log.update_query_plan(qedge_key, self.kp_infores_curie, "Error", "Cleaned response is malformed")
            return QGOrganizedKnowledgeGraph(), None
        r = cast(dict[str, Any], r)

        aux_graphs: dict[str, AuxiliaryGraph] | None
        qg_org_kg, aux_graphs = self._load_kp_json_response(r, query_graph)
        num_edges = len(qg_org_kg.edges_by_qg_id.get(qedge_key, {}))

        # This requires some explanation. If we get here, then the call to `get_result` was
        # successful. So at this point, there are two possibilities for the `error` variable:
        # - If the response is read from the cache successfully, then `error` contains
        #   the string "from cache"
        # - If the response is queried de-novo from the KP successfully, then `error`
        #   contains None
        cache_phrase = " from cache" if error == "from cache" else ""

        wait_time = round(time.time() - start, 2)

        done_message = f"Returned {num_edges} edges{cache_phrase} in {wait_time} seconds"

        if cd == 0:
            self.log.update_query_plan(qedge_key,
                                       self.kp_infores_curie,
                                       "Done",
                                       done_message)
        else:
            warn_msg = f"{cd} edge attributes dropped due to invalid values"
            self.log.update_query_plan(qedge_key, self.kp_infores_curie,
                                       "Warning",
                                       done_message + "; " + warn_msg)

        return qg_org_kg, aux_graphs



    def _answer_query_using_kp(
            self, query_graph: QueryGraph
    ) -> tuple[QGOrganizedKnowledgeGraph,
               dict[str, AuxiliaryGraph] | None]:
        # TODO: Delete this method once we're ready to let go of the multiprocessing (vs. asyncio) option
        request_body = self._get_prepped_request_body(query_graph)
        query_timeout = self._get_query_timeout_length()
        # Send the query graph to the KP's TRAPI API
        self.log.debug(f"{self.kp_infores_curie}: Sending query to KP API ({self.kp_endpoint})")
        try:
            with requests_cache.disabled():
                start = time.time()
                kp_response = requests.post(f"{self.kp_endpoint}/query",
                                            json=request_body,
                                            headers={'accept': 'application/json'},
                                            timeout=query_timeout)
                self.log.wait_time = round(time.time() - start, 2)
        except Exception:
            timeout_message = f"Query timed out after {query_timeout} seconds"
            self.log.warning(f"{self.kp_infores_curie}: {timeout_message}")
            self.log.timed_out = query_timeout
            return QGOrganizedKnowledgeGraph(), None
        if kp_response.status_code != 200:
            self.log.warning(f"{self.kp_infores_curie} API returned response of {kp_response.status_code}. "
                             f"Response from KP was: {kp_response.text}")
            self.log.http_error = f"HTTP {kp_response.status_code}"
            return QGOrganizedKnowledgeGraph(), None
        else:
            json_response = kp_response.json()

        json_response, _ = _remove_attributes_with_invalid_values(json_response,
                                                                  self.kp_infores_curie,
                                                                  self.log)
        json_response = cast(dict[str, Any], json_response)

        return self._load_kp_json_response(json_response, query_graph)

    def _get_prepped_request_body(self, qg: QueryGraph) -> dict:
        # Liberally use is_set to improve performance since we don't need individual results
        for qnode_key, qnode in qg.nodes.items():
            if not qnode.ids or len(qnode.ids) > 1:
                qnode.is_set = True

        # Strip non-essential and 'empty' properties off of our qnodes and qedges
        stripped_qnodes = {qnode_key: self._strip_empty_properties(qnode)
                           for qnode_key, qnode in qg.nodes.items()}
        stripped_qedges = {qedge_key: self._strip_empty_properties(qedge)
                           for qedge_key, qedge in qg.edges.items()}

        # Load the query into a JSON Query object
        json_qg = {'nodes': stripped_qnodes, 'edges': stripped_qedges}
        body: dict[str, Any] = {'message': {'query_graph': json_qg},
                                'submitter': 'infores:arax'}
        if self.kp_infores_curie == "infores:rtx-kg2":
            body['return_minimal_metadata'] = True  # Don't want KG2 attributes because ARAX adds them later (faster)

        # If sending a query to Retriever: specify Tier 1 only, unless tiers is already present
        if self.kp_infores_curie == "infores:retriever":
            body.setdefault('parameters', {})
            if 'tiers' not in body['parameters']:
                body['parameters']['tiers'] = [ 1 ]
                self.log.info(f"For query to {self.kp_infores_curie}, "
                              f"set body.parameters.tiers to {body['parameters']['tiers']}")

        return body


    def _load_kp_json_response(
            self,
            json_response: dict,
            qg: QueryGraph
    ) -> tuple[QGOrganizedKnowledgeGraph,
               dict[str, AuxiliaryGraph] | None]:

        kp_curie = self.kp_infores_curie

        # Load the results into the object model
        answer_kg = QGOrganizedKnowledgeGraph()
        message = json_response.get("message")
        if not message:
            self.log.warning(f"{kp_curie}: No 'message' was included in the response. "
                             f"Response was: {json.dumps(json_response, indent=4)}")
            return answer_kg, None

        arax_message = ARAXMessenger().from_dict(message)

        kg = arax_message.knowledge_graph
        if not kg:
            self.log.error(f"{kp_curie}: no knowledge graph was returned")
            return answer_kg, None

        aux_graphs = arax_message.auxiliary_graphs or {}

        results = arax_message.results or []
        if not results:
            self.log.debug(f"{kp_curie}: No 'results' were returned.")
            return answer_kg, aux_graphs
        self.log.debug(f"{kp_curie}: Got results from KP.")

        # Work around genetics provider's curie whitespace bug for now  TODO: remove once they've fixed it
        if kp_curie == "infores:genetics-data-provider":
            self._remove_whitespace_from_curies(arax_message)

        # Build a map that indicates which qnodes/qedges a given node/edge fulfills
        kg_to_qg_mappings, query_curie_mappings = \
            self._get_kg_to_qg_mappings_from_results(results, qg)

        # Populate our final KG with the returned edges
        unbound_edges = {}
        nodes_dict = kg.nodes or {}
        edges_dict = kg.edges or {}
        for edge_key, edge in edges_dict.items():
            # check the edge's subject and object properties:
            if not edge.subject or not edge.object:
                # the edge's `subject` or `object` property is empty; log a warning and skip this edge
                self.log.warning(f"{kp_curie}: Edge has empty subject/object, skipping. "
                                 f"subject: '{edge.subject}', object: '{edge.object}'")
                continue
            if edge.subject not in nodes_dict or edge.object not in nodes_dict:
                # the edge's `subject` or `object` refers to a node ID that is not in the KG;
                # log a warning and skip this edge
                self.log.warning(f"{kp_curie}: Edge is an orphan, skipping. "
                                 f"subject: '{edge.subject}', object: '{edge.object}'")
                continue

            # Put in a placeholder for missing required attribute fields, for TRAPI-compliance
            if edge.attributes:
                for attribute in edge.attributes:
                    if not attribute.attribute_source:
                        attribute.attribute_source = kp_curie
                    if not attribute.attribute_type_id:
                        attribute.attribute_type_id = \
                            f"not provided (this attribute came from {kp_curie})"

            # Indicate that this edge passed through ARAX
            if edge.sources:
                edge.sources.append(self.arax_retrieval_source)
            else:
                edge.sources = [self.arax_retrieval_source]

            # Create ARAX-generated edge key that's unique for us
            arax_edge_key = self._get_arax_edge_key(edge)

            if edge_key in kg_to_qg_mappings['edges']:
                for qedge_key in kg_to_qg_mappings['edges'][edge_key]:
                    # for each `qedge_key` to which this edge is bound,
                    # add the edge to `answer_kg` with the ARAX edge key
                    answer_kg.add_edge(arax_edge_key, edge, qedge_key)
            else:
                unbound_edges[edge_key] = edge

        # Populate our final KG with the returned nodes
        unbound_nodes = {}

        for node_key, node in nodes_dict.items():
            if not node_key:
                self.log.warning(f"{kp_curie}: Node has empty ID, skipping. "
                                 f"Node key is: '{node_key}'")
                continue
            if node_key in kg_to_qg_mappings['nodes']:
                # this node is bound to a qnode; add to answer KG
                for qnode_key in kg_to_qg_mappings['nodes'][node_key]:
                    answer_kg.add_node(node_key, node, qnode_key)
            else:
                # this node is not bound to a query node; store it in
                # `unbound_nodes`
                unbound_nodes[node_key] = node

            # if a node attrib has no `attribute_type_id`, put in a KP blame message
            for attribute in node.attributes or []:
                if not attribute.attribute_type_id:
                    attribute.attribute_type_id = \
                        f"not provided (this attribute came from {kp_curie})"

        # KPs can return result-specific "analyses" each of which can "bind" a
        # qedges to one or more edge keys in the knowledge graph. Each such
        # bound edge can, in turn, reference nodes (including nodes that are not
        # bound to qnodes) via the edge's subject and/or object
        # properties. These nodes should _not_ get dropped from the KG, since
        # the result analysis is semantically incomplete without them. To
        # compile a dictionary of such nodes, it is necessary to iterate through
        # results, analyses, and edges (in that specific order of nesting from
        # outermost to innermost loop). But, if there are no unbound nodes, there
        # is no need to do this, since all nodes will already be in the answer KG.
        nodes_linked_in_bound_edges = set()
        if unbound_nodes:
            for result in results:
                for analysis in result.analyses or []:
                    edge_bindings_iterable = analysis.edge_bindings or {}
                    for qedge_key, edge_bindings in edge_bindings_iterable.items():
                        if qedge_key in qg.edges:
                            for edge_binding in edge_bindings or []:
                                edge_id = edge_binding.id
                                if edge_id in edges_dict:
                                    edge = edges_dict[edge_id]
                                    nodes_linked_in_bound_edges.add(edge.subject)
                                    nodes_linked_in_bound_edges.add(edge.object)
        self.log.debug("Number of nodes referenced in result analysis edges: "
                       f"{len(nodes_linked_in_bound_edges)}")

        nodes_referenced_in_aux_graphs = set()
        unbound_edges_keep = {}
        # KPs can also return auxiliary graphs, which can reference edges.
        # Any edge referenced by an auxiliary graph can also reference nodes,
        # which should be retained in the knowledge graph for semantic
        # completeness.
        if unbound_edges and aux_graphs:
            for aux_graph_id, aux_graph in aux_graphs.items():
                for edge_id in aux_graph.edges or []:
                    edge = edges_dict.get(edge_id)
                    if edge is None:
                        self.log.warning(f"{kp_curie}: aux graph {aux_graph_id} "
                                         f"references edge not in KG: {edge_id}")
                        continue
                    if edge_id in unbound_edges:
                        unbound_edges_keep[edge_id] = edge
                    nodes_referenced_in_aux_graphs.add(edge.subject)
                    nodes_referenced_in_aux_graphs.add(edge.object)
        answer_kg.unbound_edges = unbound_edges_keep

        unbound_nodes_keep = {}
        unbound_nodes_not_kept = {}
        for node_key, node in unbound_nodes.items():
            if node_key in nodes_linked_in_bound_edges or \
               node_key in nodes_referenced_in_aux_graphs:
                unbound_nodes_keep[node_key] = node
            else:
                unbound_nodes_not_kept[node_key] = node
        answer_kg.unbound_nodes = unbound_nodes_keep

        if unbound_nodes_not_kept:
            curie_summary = _summarize_set_elements(unbound_nodes_not_kept.keys())
            self.log.warning(f"{kp_curie}: {len(unbound_nodes_not_kept)} "
                             "nodes in the KP's answer KG have no bindings to the QG "
                             "and are not referenced in any analysis or aux graphs: "
                             f"{curie_summary}")

        unreferenced_unbound_edges = set(unbound_edges) - set(unbound_edges_keep)
        if unreferenced_unbound_edges:
            edge_key_summary = _summarize_set_elements(unreferenced_unbound_edges)
            self.log.warning(f"{kp_curie}: {len(unreferenced_unbound_edges)} "
                             "edges in the KP's answer KG have no bindings to the QG "
                             f"and are not referenced in aux graphs: {edge_key_summary}")

        # Fill out our unofficial node.query_ids property
        for nodes in answer_kg.nodes_by_qg_id.values():
            for node_key, node in nodes.items():
                node.query_ids = eu.convert_to_list(query_curie_mappings.get(node_key))

        # Add subclass_of edges for any parent to child relationships KPs returned
        answer_kg = self._add_subclass_of_edges(answer_kg)

        return answer_kg, aux_graphs

    @staticmethod
    def _strip_empty_properties(qnode_or_qedge: Union[QNode, QEdge]) -> dict[str, Any]:
        dict_version_of_object = qnode_or_qedge.to_dict()
        stripped_dict = {property_name: value \
                         for property_name, value \
                         in dict_version_of_object.items()
                         if dict_version_of_object.get(property_name) \
                         not in [None, []]}
        return stripped_dict

    def _get_arax_edge_key(self, edge: Edge) -> str:
        qualifiers_dict = {qualifier.qualifier_type_id: qualifier.qualifier_value \
                           for qualifier in edge.qualifiers} if edge.qualifiers else {}
        qualified_predicate = qualifiers_dict.get("biolink:qualified_predicate")
        qualified_object_direction = qualifiers_dict.get("biolink:object_direction_qualifier")
        qualified_object_aspect = qualifiers_dict.get("biolink:object_aspect_qualifier")
        qualified_portion = \
            f"{qualified_predicate}--{qualified_object_direction}--{qualified_object_aspect}"
        primary_ks = eu.get_primary_knowledge_source(edge)
        kp_curie = self.kp_infores_curie
        edge_key = \
            f"{kp_curie}:{edge.subject}--{edge.predicate}--{qualified_portion}--{edge.object}--" \
            f"{primary_ks}"
        return edge_key

    def _get_query_timeout_length(self) -> int:
        # Returns the number of seconds we should wait for a response
        if self.kp_infores_curie == "infores:rtx-kg2":
            return 600
        elif self.kp_timeout:
            return self.kp_timeout
        else:
            return 120

    def _add_subclass_of_edges(self, answer_kg: QGOrganizedKnowledgeGraph) -> QGOrganizedKnowledgeGraph:
        for qnode_key in answer_kg.nodes_by_qg_id:
            nodes_with_non_empty_parent_query_ids = {node_key for node_key, node in answer_kg.nodes_by_qg_id[qnode_key].items()
                                                     if hasattr(node, "query_ids") and node.query_ids}
            initial_edge_count = sum([len(edges) for edges in answer_kg.edges_by_qg_id.values()])
            # Grab info for any parent nodes missing from the KG in bulk for easy access later
            all_parent_query_ids = {parent_id for node_key in nodes_with_non_empty_parent_query_ids
                                    for parent_id in answer_kg.nodes_by_qg_id[qnode_key][node_key].query_ids}
            parents_missing_from_kg = all_parent_query_ids.difference(set(answer_kg.nodes_by_qg_id[qnode_key]))

            # Build a lookup of existing nodes for parents missing under this qnode_key.
            # These nodes should already be in the answer KG — either as unbound nodes or
            # bound under a different qnode_key — so we reuse them instead of calling
            # NodeSynonymizer.
            existing_parent_nodes = {}
            for parent_curie in parents_missing_from_kg:
                if parent_curie in answer_kg.unbound_nodes:
                    existing_parent_nodes[parent_curie] = answer_kg.unbound_nodes[parent_curie].deepcopy()
                else:
                    for other_qnode_key, nodes_dict in answer_kg.nodes_by_qg_id.items():
                        if other_qnode_key != qnode_key and parent_curie in nodes_dict:
                            existing_parent_nodes[parent_curie] = nodes_dict[parent_curie].deepcopy()
                            break
                    if parent_curie not in existing_parent_nodes:
                        self.log.warning(f"{self.kp_infores_curie}: Parent node {parent_curie} not found "
                                         f"anywhere in the answer KG; creating an empty Node")
                        existing_parent_nodes[parent_curie] = Node()

            # Add subclass_of edges to the answer KG for any nodes that the KP provided query ID mappings for
            for node_key in nodes_with_non_empty_parent_query_ids:
                subclass_edges = []
                parent_query_ids = answer_kg.nodes_by_qg_id[qnode_key][node_key].query_ids
                for parent_query_id in parent_query_ids:
                    if parent_query_id is not None and parent_query_id != node_key:
                        subclass_edge = Edge(subject=node_key, object=parent_query_id, predicate="biolink:subclass_of")

                        # Add provenance info to this edge so it's clear where the assertion came from
                        kp_retrieval_source = RetrievalSource(resource_id=self.kp_infores_curie,
                                                              resource_role="primary_knowledge_source")
                        subclass_edge.sources = [kp_retrieval_source, self.arax_retrieval_source]

                        # Further describe in plain english where this edge comes from
                        edge_note = Attribute(attribute_type_id="biolink:description",
                                              value=f"ARAX created this edge to represent the fact "
                                                    f"that {self.kp_infores_curie} fulfilled {subclass_edge.object}"
                                                    f" (for {qnode_key}) with {subclass_edge.subject}.",
                                              value_type_id="metatype:String",
                                              attribute_source=self.arax_infores_curie)
                        subclass_edge.attributes = [edge_note]

                        subclass_edges.append(subclass_edge)
                if subclass_edges:
                    for edge in subclass_edges:
                        # Add the parent to the KG if it isn't in there already
                        if edge.object not in answer_kg.nodes_by_qg_id[qnode_key]:
                            parent_node = existing_parent_nodes[edge.object]
                            parent_node.query_ids = []   # Does not need a mapping since it appears in the QG
                            answer_kg.add_node(edge.object, parent_node, qnode_key)
                        edge_key = self._get_arax_edge_key(edge)
                        qedge_key = f"subclass:{qnode_key}--{qnode_key}"  # Technically someone could have used this key in their query, but seems highly unlikely..
                        answer_kg.add_edge(edge_key, edge, qedge_key)
            final_edge_count = sum([len(edges) for edges in answer_kg.edges_by_qg_id.values()])
            num_edges_added = final_edge_count - initial_edge_count
            if num_edges_added:
                self.log.debug(f"{self.kp_infores_curie}: Added {num_edges_added} subclass_of edges to the KG based on "
                               f"query ID mappings {self.kp_infores_curie} returned")
        return answer_kg

    @staticmethod
    def _remove_whitespace_from_curies(kp_message):
        kg = kp_message.knowledge_graph
        for node_key in set(kg.nodes):
            node = kg.nodes[node_key]
            del kg.nodes[node_key]
            kg.nodes[node_key.strip()] = node
        for edge in kg.edges.values():
            edge.subject = edge.subject.strip()
            edge.object = edge.object.strip()
        for result in kp_message.results:
            for qnode_key, node_bindings in result.node_bindings.items():
                for node_binding in node_bindings:
                    node_binding.id = node_binding.id.strip()
                    if node_binding.query_id:
                        node_binding.query_id = node_binding.query_id.strip()
