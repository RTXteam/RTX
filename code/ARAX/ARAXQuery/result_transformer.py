import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.auxiliary_graph import AuxiliaryGraph
from openapi_server.models.attribute import Attribute



class ResultTransformer:

    @staticmethod
    def transform(response: ARAXResponse):
        message = response.envelope.message
        if message.results:
            if ( #Bypassing pathfinder queries
                    message.query_graph
                    and hasattr(message.query_graph, "paths")
                    and message.query_graph.paths
                    and len(message.query_graph.paths) > 0
            ):
                return #This would need to be changed if you wanted to mix connect with other DSL commands (like overlaying NGD and the like)
            if not hasattr(response, "original_query_graph") or not response.original_query_graph.nodes:
                response.error(f"The original QG was never saved before ARAX edited it! So we can't transform results "
                               f"to TRAPI 1.4 format (i.e., support_graphs).", error_code="NoOriginalQG")
                return

            response.info(f"Transforming results to TRAPI 1.5 format (moving 'virtual' nodes/edges to support graphs)")

            original_qedge_keys = {qedge_key for qedge_key, qedge in response.original_query_graph.edges.items()
                                   if not qedge.exclude}  # 'Exclude'/'kryptonite' edges shouldn't appear in results
            original_qnode_keys = set(response.original_query_graph.nodes)
            non_orphan_qnode_keys = {qnode_key for qedge_key in original_qedge_keys
                                     for qnode_key in {response.original_query_graph.edges[qedge_key].subject,
                                                       response.original_query_graph.edges[qedge_key].object}}
            response.debug(f"Original input QG contained qnodes {original_qnode_keys} and qedges {original_qedge_keys}")
            response.debug(f"Non-orphan qnodes in original QG are: {non_orphan_qnode_keys}")
            all_virtual_qedge_keys = set()

            new_results = []
            for result in message.results:
                # First figure out which edges in this result are 'virtual' and what option groups they belong to
                edge_bindings = result.analyses[0].edge_bindings
                qedge_keys_in_result = set(edge_bindings)
                virtual_qedge_keys = qedge_keys_in_result.difference(original_qedge_keys)
                all_virtual_qedge_keys = all_virtual_qedge_keys.union(virtual_qedge_keys)  # Record these for log info
                virtual_edge_groups_dict = defaultdict(set)
                for virtual_qedge_key in virtual_qedge_keys:
                    virtual_qedge = message.query_graph.edges[virtual_qedge_key]
                    option_group_id = virtual_qedge.option_group_id
                    virtual_edge_keys = {edge_binding.id for edge_binding in edge_bindings[virtual_qedge_key]}
                    virtual_edge_groups_dict[option_group_id] = virtual_edge_groups_dict[option_group_id].union(virtual_edge_keys)
                    # Note: All edges not belonging to an option group are lumped together under 'None' key

                # Create a support graph for each group
                if virtual_edge_groups_dict:
                    if message.auxiliary_graphs is None:
                        message.auxiliary_graphs = dict()
                    if result.analyses[0].support_graphs is None:
                        result.analyses[0].support_graphs = []
                for group_id, group_edge_keys in virtual_edge_groups_dict.items():
                    group_id_str = f"_{group_id}" if group_id else ""
                    ordered_edge_keys = sorted(list(group_edge_keys))
                    aux_graph_id_str = ";".join(ordered_edge_keys) if len(ordered_edge_keys) < 5 else f"{len(message.auxiliary_graphs)}"
                    aux_graph_key = f"aux_graph_{aux_graph_id_str}{group_id_str}"
                    # Create and save the aux graph in the central location (on Message), if it doesn't yet exist
                    if aux_graph_key not in message.auxiliary_graphs:
                        message.auxiliary_graphs[aux_graph_key] = AuxiliaryGraph(edges=list(group_edge_keys),attributes=[])

                    # Refer to this aux graph from the current Result or Edge (if this is an Infer support graph)
                    if group_id and group_id.startswith("creative_"):
                        # Figure out which creative tool/method we're dealing with (e.g. creative_DTD, creative_expand)
                        group_id_prefix = "_".join(group_id.split("_")[:2])

                        # Create an attribute for the support graph that we'll tack onto the treats edge for this result
                        support_graph_attribute = Attribute(attribute_type_id="biolink:support_graphs",
                                                            value=[aux_graph_key],
                                                            attribute_source="infores:arax")
                        # Find the 'treats' edge that this result is all about
                        inferred_qedge_keys = [qedge_key for qedge_key, qedge in response.original_query_graph.edges.items()
                                               if qedge.knowledge_type == "inferred"]
                        if not len(inferred_qedge_keys):
                            response.error(f"Result contains a {group_id} option group, but the query graph has no "
                                           f"inferred qedge! {result}", error_code="InvalidResult")
                            return
                        elif len(inferred_qedge_keys) > 1:
                            response.error(f"Query graph contains multiple 'inferred' qedges; don't know how to "
                                           f"properly form support graphs!", error_code="UnsupportedQG")
                            return
                        else:
                            inferred_qedge_key = inferred_qedge_keys[0]
                            inferred_edge_keys = {edge_binding.id for edge_binding in
                                                  result.analyses[0].edge_bindings[inferred_qedge_key]
                                                  if group_id_prefix in edge_binding.id}
                            # Refer to the support graph from the proper edge(s)
                            for inferred_edge_key in inferred_edge_keys:
                                inferred_edge = message.knowledge_graph.edges[inferred_edge_key]
                                if inferred_edge.attributes:
                                    existing_sg_attributes = [attribute for attribute in inferred_edge.attributes
                                                                if attribute.attribute_type_id == "biolink:support_graphs"]
                                    if existing_sg_attributes:
                                        # Refer to this support graph from the first existing support graph attribute
                                        existing_sg_attribute = existing_sg_attributes[0]
                                        if aux_graph_key not in existing_sg_attribute.value:
                                            existing_sg_attribute.value.append(aux_graph_key)
                                    else:
                                        inferred_edge.attributes.append(support_graph_attribute)
                                else:
                                    inferred_edge.attributes = [support_graph_attribute]
                    else:
                        # Tack the support graph onto the result
                        result.analyses[0].support_graphs.append(aux_graph_key)

                # Delete virtual edges (since we moved them to supporting_graphs)
                for virtual_qedge_key in virtual_qedge_keys:
                    del edge_bindings[virtual_qedge_key]

                # Delete any virtual node bindings (strangely, nodes aren't allowed in AuxGraphs; only live in KG)
                node_bindings = result.node_bindings
                qnode_keys_in_result = set(node_bindings)
                virtual_qnode_keys = qnode_keys_in_result.difference(original_qnode_keys)
                for virtual_qnode_key in virtual_qnode_keys:
                    del node_bindings[virtual_qnode_key]

                # Delete bindings for any subclass parent nodes that are now orphans (they'll still be in the KG)
                qedge_keys_in_result = set(result.analyses[0].edge_bindings)  # May not include 'optional' edges in QG
                for non_orphan_qnode_key in non_orphan_qnode_keys:
                    node_keys = {binding.id for binding in node_bindings[non_orphan_qnode_key]}
                    node_keys_used_by_result_edges = {node_key for qedge_key in qedge_keys_in_result
                                                      for binding in result.analyses[0].edge_bindings[qedge_key]
                                                      for node_key in {message.knowledge_graph.edges[binding.id].subject,
                                                                       message.knowledge_graph.edges[binding.id].object}}
                    orphan_node_keys = node_keys.difference(node_keys_used_by_result_edges)
                    non_orphan_node_bindings = [binding for binding in result.node_bindings[non_orphan_qnode_key]
                                                if binding.id not in orphan_node_keys]
                    result.node_bindings[non_orphan_qnode_key] = non_orphan_node_bindings

                # if the support graph of a xDTD edge has "normalized_google_distance" attribute and its value is "inf", remove this edge
                kg_edge_id_to_edge = {edge_key: edge for edge_key, edge in message.knowledge_graph.edges.items()}
                if result.analyses[0].support_graphs is not None:
                    invalid_support_graphs_dict = {}
                    for support_graph_id in result.analyses[0].support_graphs[0].split(';'):
                        edge_info = kg_edge_id_to_edge[support_graph_id.replace('aux_graph_', '')]
                        skip_flag = False
                        for attribute in edge_info.attributes:
                            if attribute.original_attribute_name == 'normalized_google_distance':
                                if attribute.value == 'inf':
                                    skip_flag = True
                                    break
                        if skip_flag:
                            invalid_support_graphs_dict[(edge_info.subject, edge_info.object)] = support_graph_id.replace('aux_graph_', '')

                    edge_groups = {}
                    node_count = {}
                    del_node_list = []
                    for qedge, edge_list in edge_bindings.items():
                        for edge in edge_list:
                            edge_info = kg_edge_id_to_edge[edge.id]
                            if edge_info.subject not in node_count:
                                node_count[edge_info.subject] = 0
                            if edge_info.object not in node_count:
                                node_count[edge_info.object] = 0
                            node_count[edge_info.subject] += 1
                            node_count[edge_info.object] += 1
                            
                            if (edge_info.subject, edge_info.object) in edge_groups:
                                edge_groups[(edge_info.subject, edge_info.object)].append(edge.id)
                            else:
                                edge_groups[(edge_info.subject, edge_info.object)] = []
                                edge_groups[(edge_info.subject, edge_info.object)].append(edge.id)
                                
                    for invalid_edge, support_graph_id in invalid_support_graphs_dict.items():
                        if (invalid_edge[0], invalid_edge[1]) in edge_groups:
                            edge_id_to_remove_list = edge_groups[(invalid_edge[0], invalid_edge[1])]
                        elif (invalid_edge[1], invalid_edge[0]) in edge_groups:
                            edge_id_to_remove_list = edge_groups[(invalid_edge[1], invalid_edge[0])]
                        else:
                            continue

                        new_edge_bindings = {}
                        if len(edge_id_to_remove_list) == 1:
                            if 'creative_' in edge_id_to_remove_list[0]:
                                for qedge, edge_list in edge_bindings.items():
                                    new_edge_bindings[qedge] = [edge for edge in edge_list if edge.id != edge_id_to_remove_list[0]]
                                    if len(new_edge_bindings[qedge]) == 0:
                                        del new_edge_bindings[qedge]
                                    
                                edge_bindings = new_edge_bindings
                                
                                result.analyses[0].support_graphs[0] = 'aux_graph_' + ";".join([x for x in result.analyses[0].support_graphs[0].replace('aux_graph_', '').split(';') if x != support_graph_id])
                                
                                node_count[kg_edge_id_to_edge[edge_id_to_remove_list[0]].subject] -= 1
                                node_count[kg_edge_id_to_edge[edge_id_to_remove_list[0]].object] -= 1
                                if node_count[kg_edge_id_to_edge[edge_id_to_remove_list[0]].subject] == 0:
                                    del_node_list.append(kg_edge_id_to_edge[edge_id_to_remove_list[0]].subject)
                                if node_count[kg_edge_id_to_edge[edge_id_to_remove_list[0]].object] == 0:
                                    del_node_list.append(kg_edge_id_to_edge[edge_id_to_remove_list[0]].object)
                                    
                        else:
                            for qedge, edge_list in edge_bindings.items():
                                temp_del_edge_list = []
                                new_edge_bindings[qedge] = []
                                for edge in edge_list:
                                    if edge.id in edge_id_to_remove_list and 'creative_' in edge.id:
                                        temp_del_edge_list.append(edge.id)
                                    else:
                                        new_edge_bindings[qedge].append(edge)
                                    if len(new_edge_bindings[qedge]) == 0:
                                        del new_edge_bindings[qedge]
                                edge_bindings = new_edge_bindings
                                
                                if len(temp_del_edge_list) == len(edge_id_to_remove_list):
                                    for edge_id in temp_del_edge_list:
                                        node_count[kg_edge_id_to_edge[edge_id].subject] -= 1
                                        node_count[kg_edge_id_to_edge[edge_id].object] -= 1
                                        if node_count[kg_edge_id_to_edge[edge_id].subject] == 0:
                                            del_node_list.append(kg_edge_id_to_edge[edge_id].subject)
                                        if node_count[kg_edge_id_to_edge[edge_id].object] == 0:
                                            del_node_list.append(kg_edge_id_to_edge[edge_id].object)
                                    
                                    result.analyses[0].support_graphs[0] = 'aux_graph_' + ";".join([x for x in result.analyses[0].support_graphs[0].replace('aux_graph_', '').split(';') if x != support_graph_id])
                                
                    if len(edge_bindings) != 0 and len([key for key in original_qedge_keys if key in edge_bindings]) != 0:                        
                        for key in original_qnode_keys:
                            result.node_bindings[key] = [binding for binding in result.node_bindings[key] if binding.id not in del_node_list]
                        new_results.append(result)
                    else:
                        continue
                    
            message.results = new_results

            # Return the original query graph in the response, rather than our edited version
            response.debug(f"Replacing ARAX's internal edited QG with the original input QG..")
            message.query_graph = response.original_query_graph

            # Log some final stats about result transformation
            response.debug(f"Virtual qedge keys moved to support_graphs were: {all_virtual_qedge_keys}")
            response.debug(f"There are a total of {len(message.auxiliary_graphs) if message.auxiliary_graphs else 0} AuxiliaryGraphs.")
            response.info(f"Done transforming results to TRAPI 1.5 format (i.e., using support_graphs)")
