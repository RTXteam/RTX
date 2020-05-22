#!/bin/env python3
import sys
import os
import traceback
import ast

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../reasoningtool/QuestionAnswering/")
from KGNodeIndex import KGNodeIndex
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.node import Node
from swagger_server.models.edge import Edge
from swagger_server.models.node_attribute import NodeAttribute
from swagger_server.models.edge_attribute import EdgeAttribute


class KGQuerier:

    def __init__(self, response_object, kp_to_use):
        self.response = response_object
        self.kp = "KG2" if kp_to_use == "ARAX/KG2" else "KG1"
        self.query_graph = None
        self.cypher_query = None
        self.query_results = None
        self.edge_to_nodes_map = dict()
        self.final_kg = {'nodes': dict(), 'edges': dict()}

    def answer_one_hop_query(self, query_graph):
        """
        This function answers a one-hop (single-edge) query using either KG1 or KG2.
        :param query_graph: A Reasoner API standard query graph.
        :return: An (almost) Reasoner API standard knowledge graph containing all of the nodes and edges returned as
        results for that query. ('Almost' standard in that kg.edges and kg.nodes are dictionaries rather than lists.)
        """
        self.query_graph = query_graph
        dsl_parameters = self.response.data['parameters']
        kp = self.kp

        synonym_usages_dict = dict()
        if dsl_parameters['use_synonyms']:
            synonym_usages_dict = self.__add_curie_synonyms_to_query_nodes(self.query_graph.nodes, kp)
            if not self.response.status == 'OK':
                return self.final_kg

        self.__convert_query_graph_to_cypher_query(dsl_parameters['enforce_directionality'])
        if not self.response.status == 'OK':
            return self.final_kg

        self.__answer_query_using_kg_neo4j(kp, dsl_parameters['continue_if_no_results'])
        if not self.response.status == 'OK':
            return self.final_kg

        self.__add_answers_to_kg(dsl_parameters['synonym_handling'], synonym_usages_dict, kp, query_graph)
        if not self.response.status == 'OK':
            return self.final_kg

        return self.final_kg, self.edge_to_nodes_map

    def answer_single_node_query(self, qnode):
        if not qnode.curie:
            self.response.error(f"Cannot expand a single query node if it doesn't have a curie", error_code="InvalidQuery")
        else:
            # Gather synonyms as appropriate
            use_synonyms = self.response.data['parameters'].get('use_synonyms')
            synonym_handling = self.response.data['parameters'].get('synonym_handling')
            synonym_usages_dict = dict()
            if use_synonyms:
                synonym_usages_dict = self.__add_curie_synonyms_to_query_nodes([qnode], self.kp)
                if not self.response.status == 'OK':
                    return self.final_kg

            # Build and run a cypher query to get this node/nodes
            where_clause = f"{qnode.id}.id='{qnode.curie}'" if type(qnode.curie) is str else f"{qnode.id}.id in {qnode.curie}"
            cypher_query = f"MATCH {self.__get_cypher_for_query_node(qnode)} WHERE {where_clause} RETURN {qnode.id}"
            results = self.__run_cypher_query(cypher_query, self.kp)

            # Process the results and add to our answer knowledge graph, handling synonyms as appropriate
            for result in results:
                neo4j_node = result.get(qnode.id)
                swagger_node = self.__convert_neo4j_node_to_swagger_node(neo4j_node, qnode.id, self.kp)
                if qnode.id in synonym_usages_dict and synonym_handling == "map_back":
                    # Only add the original curie (discard synonym nodes)
                    if swagger_node.id == synonym_usages_dict[qnode.id].get('original_curie'):
                        self.__add_node_to_kg(swagger_node)
                else:
                    self.__add_node_to_kg(swagger_node)

        return self.final_kg

    def __add_curie_synonyms_to_query_nodes(self, query_nodes, kp):
        self.response.debug("Looking for query nodes to use curie synonyms for")
        KGNI = KGNodeIndex()
        synonym_usages_dict = dict()
        for node in query_nodes:
            original_curie = node.curie
            if original_curie and type(original_curie) is str:  # Important because sometimes lists of curies are passed behind the scenes (when expanding one edge at a time)
                equivalent_curies = KGNI.get_equivalent_curies(original_curie, kg_name=kp)
                if len(equivalent_curies) > 1:
                    self.response.info(f"Using equivalent curies for node {original_curie}: {equivalent_curies}")
                    node.curie = equivalent_curies
                    node.type = None  # Equivalent curie types may be different than the original, so we clear this
                    synonym_usages_dict[node.id] = {'original_curie': original_curie, 'synonym_curies': node.curie}
                elif len(equivalent_curies) == 1:
                    self.response.info(f"Could not find any equivalent curies in {kp} for {original_curie}")
                else:
                    self.response.error(f"{kp} does not contain a node with curie {original_curie}", error_code="UnknownCurie")
        return synonym_usages_dict

    def __convert_query_graph_to_cypher_query(self, enforce_directionality):
        if len(self.query_graph.edges) > 1:
            self.response.error(f"KGQuerier requires a single-edge query graph", error_code="InvalidQuery")
        else:
            self.response.debug(f"Generating cypher for edge {self.query_graph.edges[0].id} query graph")
            try:
                # Build the match clause
                edge = self.query_graph.edges[0]
                source_node = self.__get_query_node(edge.source_id)
                target_node = self.__get_query_node(edge.target_id)
                edge_cypher = self.__get_cypher_for_query_edge(edge, enforce_directionality)
                source_node_cypher = self.__get_cypher_for_query_node(source_node)
                target_node_cypher = self.__get_cypher_for_query_node(target_node)
                match_clause = f"MATCH {source_node_cypher}{edge_cypher}{target_node_cypher}"

                # Build the where clause
                where_fragments = []
                for node in [source_node, target_node]:
                    if node.curie:
                        if type(node.curie) is str:
                            where_fragment = f"{node.id}.id='{node.curie}'"
                        else:
                            where_fragment = f"{node.id}.id in {node.curie}"
                        where_fragments.append(where_fragment)
                if len(where_fragments):
                    where_clause = "WHERE "
                    where_clause += " AND ".join(where_fragments)
                else:
                    where_clause = ""

                # Build the with clause
                source_node_col_name = f"nodes_{source_node.id}"
                target_node_col_name = f"nodes_{target_node.id}"
                edge_col_name = f"edges_{edge.id}"
                extra_edge_properties = "{.*, " + f"id:ID({edge.id}), {source_node.id}:{source_node.id}.id, {target_node.id}:{target_node.id}.id" + "}"
                with_clause = f"WITH collect(distinct {source_node.id}) as {source_node_col_name}, " \
                              f"collect(distinct {target_node.id}) as {target_node_col_name}, " \
                              f"collect(distinct {edge.id}{extra_edge_properties}) as {edge_col_name}"

                # Build the return clause
                return_clause = f"RETURN {source_node_col_name}, {target_node_col_name}, {edge_col_name}"

                self.cypher_query = f"{match_clause} {where_clause} {with_clause} {return_clause}"
            except:
                tb = traceback.format_exc()
                error_type, error, _ = sys.exc_info()
                self.response.error(f"Problem generating cypher for query. {tb}", error_code=error_type.__name__)

    def __answer_query_using_kg_neo4j(self, kp, continue_if_no_results):
        self.response.info(f"Sending cypher query for edge {self.query_graph.edges[0].id} to {kp} neo4j")
        self.query_results = self.__run_cypher_query(self.cypher_query, kp)
        if self.response.status == 'OK':
            columns_with_lengths = dict()
            for column in self.query_results[0]:
                columns_with_lengths[column] = len(self.query_results[0].get(column))
            if any(length == 0 for length in columns_with_lengths.values()):
                if continue_if_no_results:
                    self.response.warning(f"No paths were found in {kp} satisfying this query graph")
                else:
                    self.response.error(f"No paths were found in {kp} satisfying this query graph", error_code="NoResults")
            else:
                num_results_string = ", ".join([f"{column.split('_')[1]}: {value}" for column, value in sorted(columns_with_lengths.items())])
                self.response.info(f"Query for edge {self.query_graph.edges[0].id} returned results ({num_results_string})")

    def __add_answers_to_kg(self, synonym_handling, synonym_usages_dict, kp, query_graph):
        self.response.debug(f"Processing query results for edge {self.query_graph.edges[0].id}")
        node_uuid_to_curie_dict = self.__build_node_uuid_to_curie_dict(self.query_results[0]) if kp == "KG1" else dict()

        results_table = self.query_results[0]
        column_names = [column_name for column_name in results_table]
        for column_name in column_names:
            # Load answer nodes into our knowledge graph
            if column_name.startswith('nodes'):  # Example column name: 'nodes_n00'
                qnode_id = column_name.replace("nodes_", "", 1)
                for node in results_table.get(column_name):
                    swagger_node = self.__convert_neo4j_node_to_swagger_node(node, qnode_id, kp)
                    if synonym_handling == 'map_back' and qnode_id in synonym_usages_dict:
                        # Only keep the node corresponding to the original curie (discard synonym nodes)
                        original_curie = synonym_usages_dict[qnode_id].get('original_curie')
                        if swagger_node.id == original_curie:
                            self.__add_node_to_kg(swagger_node)
                    else:
                        self.__add_node_to_kg(swagger_node)
            # Load answer edges into our knowledge graph
            elif column_name.startswith('edges'):  # Example column name: 'edges_e01'
                qedge_id = column_name.replace("edges_", "", 1)
                for edge in results_table.get(column_name):
                    if kp == "KG2":
                        swagger_edge = self.__convert_kg2_edge_to_swagger_edge(edge, qedge_id)
                    else:
                        swagger_edge = self.__convert_kg1_edge_to_swagger_edge(edge, qedge_id, node_uuid_to_curie_dict)

                    # Record which of this edge's nodes correspond to which qnode_id
                    qedge = query_graph.edges[0]
                    self.edge_to_nodes_map[swagger_edge.id] = dict()
                    for qnode_id in [qedge.source_id, qedge.target_id]:
                        node_curie = edge.get(qnode_id)
                        self.edge_to_nodes_map[swagger_edge.id][qnode_id] = node_curie

                    if synonym_handling == 'map_back':
                        # Edit edge to point to original curie, if it uses a synonym
                        for qnode_id, synonym_info in synonym_usages_dict.items():
                            curie_for_this_qnode_id = self.edge_to_nodes_map[swagger_edge.id].get(qnode_id)
                            original_curie = synonym_info.get('original_curie')
                            if curie_for_this_qnode_id in synonym_info.get('synonym_curies'):
                                if swagger_edge.source_id == curie_for_this_qnode_id:
                                    swagger_edge.source_id = original_curie
                                if swagger_edge.target_id == curie_for_this_qnode_id:
                                    swagger_edge.target_id = original_curie
                                self.edge_to_nodes_map[swagger_edge.id][qnode_id] = original_curie

                    self.__add_edge_to_kg(swagger_edge)

        # Make sure any original curie that synonyms were used for appears in the answer kg as appropriate
        if synonym_handling == 'map_back':
            for qnode_id, synonym_info in synonym_usages_dict.items():
                original_curie = synonym_info.get('original_curie')
                if qnode_id not in self.final_kg['nodes'] or original_curie not in self.final_kg['nodes'][qnode_id]:
                    # Get this node from neo4j and add it to the kg
                    cypher = f"match (n) where n.id='{original_curie}' return n limit 1"
                    original_node = self.__run_cypher_query(cypher, kp)[0].get('n')
                    swagger_node = self.__convert_neo4j_node_to_swagger_node(original_node, qnode_id, kp)
                    self.__add_node_to_kg(swagger_node)

        # Remove any self-edges
        edges_to_remove = []
        qedge_id = self.query_graph.edges[0]
        for qedge_id, edges in self.final_kg['edges'].items():
            for edge_key, edge in edges.items():
                if edge.source_id == edge.target_id:
                    edges_to_remove.append(edge_key)
        for edge_id in edges_to_remove:
            self.final_kg['edges'][qedge_id].pop(edge_id)

        # Remove any nodes that may have been orphaned
        for qnode_id in [node.id for node in self.query_graph.nodes]:
            node_ids_used_by_edges_for_this_qnode_id = set()
            for edge in self.final_kg['edges'][qedge_id].values():
                node_ids_used_by_edges_for_this_qnode_id.add(self.edge_to_nodes_map[edge.id][qnode_id])
            orphan_node_ids_for_this_qnode_id = set(self.final_kg['nodes'][qnode_id].keys()).difference(node_ids_used_by_edges_for_this_qnode_id)
            for node_id in orphan_node_ids_for_this_qnode_id:
                self.final_kg['nodes'][qnode_id].pop(node_id)

    def __convert_neo4j_node_to_swagger_node(self, neo4j_node, qnode_id, kp):
        if kp == "KG2":
            return self.__convert_kg2_node_to_swagger_node(neo4j_node, qnode_id)
        else:
            return self.__convert_kg1_node_to_swagger_node(neo4j_node, qnode_id)

    def __convert_kg2_node_to_swagger_node(self, neo4j_node, qnode_id):
        swagger_node = Node()
        swagger_node.qnode_id = qnode_id
        swagger_node.id = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('iri')
        swagger_node.node_attributes = []

        node_category = neo4j_node.get('category_label')
        swagger_node.type = node_category if type(node_category) is list else [node_category]

        # Fill out the 'symbol' property (only really relevant for nodes from UniProtKB)
        if swagger_node.symbol is None and swagger_node.id.lower().startswith("uniprot"):
            swagger_node.symbol = neo4j_node.get('name')
            swagger_node.name = neo4j_node.get('full_name')

        # Add all additional properties on KG2 nodes as swagger NodeAttribute objects
        additional_kg2_node_properties = ['publications', 'synonym', 'category', 'provided_by', 'deprecated',
                                          'update_date']
        node_attributes = self.__create_swagger_attributes("node", additional_kg2_node_properties, neo4j_node)
        swagger_node.node_attributes += node_attributes

        return swagger_node

    def __convert_kg1_node_to_swagger_node(self, neo4j_node, qnode_id):
        swagger_node = Node()
        swagger_node.qnode_id = qnode_id
        swagger_node.id = neo4j_node.get('id')
        swagger_node.name = neo4j_node.get('name')
        swagger_node.symbol = neo4j_node.get('symbol')
        swagger_node.description = neo4j_node.get('description')
        swagger_node.uri = neo4j_node.get('uri')
        swagger_node.node_attributes = []

        node_category = neo4j_node.get('category')
        swagger_node.type = node_category if type(node_category) is list else [node_category]

        return swagger_node

    def __convert_kg2_edge_to_swagger_edge(self, neo4j_edge, qedge_id):
        swagger_edge = Edge()
        swagger_edge.id = f"KG2:{neo4j_edge.get('id')}"
        swagger_edge.qedge_id = qedge_id
        swagger_edge.type = neo4j_edge.get('simplified_edge_label')
        swagger_edge.source_id = neo4j_edge.get('subject')
        swagger_edge.target_id = neo4j_edge.get('object')
        swagger_edge.relation = neo4j_edge.get('relation')
        swagger_edge.publications = ast.literal_eval(neo4j_edge.get('publications'))
        swagger_edge.provided_by = self.__convert_strange_provided_by_field_to_list(neo4j_edge.get('provided_by'))  # Temporary hack until provided_by is fixed in KG2
        swagger_edge.negated = ast.literal_eval(neo4j_edge.get('negated'))
        swagger_edge.is_defined_by = "ARAX/KG2"
        swagger_edge.edge_attributes = []

        # Add additional properties on KG2 edges as swagger EdgeAttribute objects
        # TODO: fix issues coming from strange characters in 'publications_info'! (EOF error)
        additional_kg2_edge_properties = ['relation_curie', 'simplified_relation_curie', 'simplified_relation',
                                          'edge_label']
        edge_attributes = self.__create_swagger_attributes("edge", additional_kg2_edge_properties, neo4j_edge)
        swagger_edge.edge_attributes += edge_attributes

        return swagger_edge

    def __convert_kg1_edge_to_swagger_edge(self, neo4j_edge, qedge_id, node_uuid_to_curie_dict):
        swagger_edge = Edge()
        swagger_edge.id = f"KG1:{neo4j_edge.get('id')}"
        swagger_edge.qedge_id = qedge_id
        swagger_edge.type = neo4j_edge.get('predicate')
        swagger_edge.source_id = node_uuid_to_curie_dict[neo4j_edge.get('source_node_uuid')]
        swagger_edge.target_id = node_uuid_to_curie_dict[neo4j_edge.get('target_node_uuid')]
        swagger_edge.relation = neo4j_edge.get('relation')
        swagger_edge.provided_by = neo4j_edge.get('provided_by')
        swagger_edge.is_defined_by = "ARAX/KG1"

        if neo4j_edge.get('probability'):
            swagger_edge.edge_attributes = self.__create_swagger_attributes("edge", ['probability'], neo4j_edge)
        return swagger_edge

    def __create_swagger_attributes(self, object_type, property_names, neo4j_object):
        new_attributes = []
        for property_name in property_names:
            property_value = neo4j_object.get(property_name)
            if type(property_value) is str:
                # Extract any lists, dicts, and booleans that are stored within strings
                if (property_value.startswith('[') and property_value.endswith(']')) or \
                        (property_value.startswith('{') and property_value.endswith('}')) or \
                        property_value.lower() == "true" or property_value.lower() == "false":
                    property_value = ast.literal_eval(property_value)

            if property_value is not None and property_value != {} and property_value != []:
                swagger_attribute = NodeAttribute() if object_type == "node" else EdgeAttribute()
                swagger_attribute.name = property_name

                # Figure out whether this is a url and store it appropriately
                if type(property_value) is str and (property_value.startswith("http:") or property_value.startswith("https:")):
                    swagger_attribute.url = property_value
                else:
                    swagger_attribute.value = property_value
                new_attributes.append(swagger_attribute)

        return new_attributes

    def __run_cypher_query(self, cypher_query, kp):
        rtxc = RTXConfiguration()
        if kp == "KG2":  # Flip into KG2 mode if that's our KP (rtx config is set to KG1 info by default)
            rtxc.live = "KG2"
        try:
            driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
            with driver.session() as session:
                query_results = session.run(cypher_query).data()
            driver.close()
        except:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            self.response.error(f"Encountered an error interacting with {kp} neo4j. {tb}", error_code=error_type.__name__)
            return []
        else:
            return query_results

    def __build_node_uuid_to_curie_dict(self, results_table):
        node_uuid_to_curie_dict = dict()
        nodes_columns = [column_name for column_name in results_table if column_name.startswith('nodes')]
        for column in nodes_columns:
            for node in results_table.get(column):
                node_uuid_to_curie_dict[node.get('UUID')] = node.get('id')
        return node_uuid_to_curie_dict

    def __get_query_node(self, qnode_id):
        for node in self.query_graph.nodes:
            if node.id == qnode_id:
                return node
        return None

    def __get_cypher_for_query_node(self, node):
        node_type_string = f":{node.type}" if node.type else ""
        final_node_string = f"({node.id}{node_type_string})"
        return final_node_string

    def __get_cypher_for_query_edge(self, edge, enforce_directionality):
        edge_type_string = f":{edge.type}" if edge.type else ""
        final_edge_string = f"-[{edge.id}{edge_type_string}]-"
        if enforce_directionality:
            final_edge_string += ">"
        return final_edge_string

    def __convert_strange_provided_by_field_to_list(self, provided_by_field):
        # Currently looks like: ["['https://identifiers.org/umls/NDFRT'", "'https://skr3.nlm.nih.gov/SemMedDB']"]
        provided_by_list = []
        unwanted_chars = ["[", "]", "'"]
        for item in provided_by_field:
            for unwanted_char in unwanted_chars:
                item = item.replace(unwanted_char, "")
            provided_by_list.append(item)
        return provided_by_list

    def __add_node_to_kg(self, swagger_node):
        if swagger_node.qnode_id not in self.final_kg['nodes']:
            self.final_kg['nodes'][swagger_node.qnode_id] = dict()
        self.final_kg['nodes'][swagger_node.qnode_id][swagger_node.id] = swagger_node

    def __add_edge_to_kg(self, swagger_edge):
        if swagger_edge.qedge_id not in self.final_kg['edges']:
            self.final_kg['edges'][swagger_edge.qedge_id] = dict()
        self.final_kg['edges'][swagger_edge.qedge_id][swagger_edge.id] = swagger_edge
