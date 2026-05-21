import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ARAXQuery directory
from ARAX_response import ARAXResponse
from ARAX_resultify import analyze_message_get_referenced_IDs

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from openapi_server.models.auxiliary_graph import AuxiliaryGraph
from openapi_server.models.attribute import Attribute
from openapi_server.models.edge import Edge
from openapi_server.models.knowledge_graph import KnowledgeGraph


def _support_graph_breaks_without_inf_ngd(
        aux: AuxiliaryGraph,
        kg_edges: dict[str, Edge],
        src: str,
        dst: str,
) -> bool:
    """Return True if removing every inf-NGD edge from `aux` leaves `dst`
    unreachable from `src` over the remaining edges (treated as undirected).
    Used to decide whether an inferred edge's support graph is "critically
    dependent" on inf-NGD virtual edges; if so, the inferred edge is
    excludable under the creative-mode result filter."""
    if src == dst:
        return False
    adj: dict[str, list[str]] = defaultdict(list)
    for eid in (getattr(aux, 'edges', None) or []):
        e = kg_edges.get(eid)
        if e is None:
            continue
        is_inf_ngd = False
        for attr in (getattr(e, 'attributes', None) or []):
            if getattr(attr, 'original_attribute_name', None) == 'normalized_google_distance' \
               and getattr(attr, 'value', None) == 'inf':
                is_inf_ngd = True
                break
        if is_inf_ngd:
            continue
        adj[e.subject].append(e.object)
        adj[e.object].append(e.subject)
    seen = {src}
    stack = [src]
    while stack:
        n = stack.pop()
        if n == dst:
            return False
        for m in adj[n]:
            if m not in seen:
                seen.add(m)
                stack.append(m)
    return True

class ResultTransformer:

    @staticmethod
    def transform(response: ARAXResponse):
        message = response.envelope.message
        if not message.results:
            return
        if ( #Bypassing pathfinder queries
                message.query_graph
                and hasattr(message.query_graph, "paths")
                and message.query_graph.paths
                and len(message.query_graph.paths) > 0
        ):
            return #This would need to be changed if you wanted to mix connect with other DSL commands (like overlaying NGD and the like)

        if not hasattr(response, "original_query_graph") or not response.original_query_graph.nodes:
            response.error("The original QG was never saved before ARAX edited it! So we can't transform results "
                           "to TRAPI 1.4 format (i.e., support_graphs).", error_code="NoOriginalQG")
            return

        response.info("Transforming results to TRAPI 1.5 format (moving 'virtual' nodes/edges to support graphs)")

        original_qedge_keys = {qedge_key for qedge_key, qedge in response.original_query_graph.edges.items()
                               if not qedge.exclude}  # 'Exclude'/'kryptonite' edges shouldn't appear in results
        original_qnode_keys = set(response.original_query_graph.nodes)
        non_orphan_qnode_keys = {qnode_key for qedge_key in original_qedge_keys
                                 for qnode_key in {response.original_query_graph.edges[qedge_key].subject,
                                                   response.original_query_graph.edges[qedge_key].object}}
        response.debug(f"Original input QG contained qnodes {original_qnode_keys} and qedges {original_qedge_keys}")
        response.debug(f"Non-orphan qnodes in original QG are: {non_orphan_qnode_keys}")
        all_virtual_qedge_keys: set[str] = set()

        # A "creative-mode" QG has at least one inferred qedge (e.g. xDTD,
        # xCRG). The NGD-inf filter applied below only touches results from
        # creative-mode QGs; ordinary lookup-style QGs are passed through.
        inferred_qedge_keys = [qk for qk, q in response.original_query_graph.edges.items()
                               if q.knowledge_type == "inferred"]
        is_creative_qg = bool(inferred_qedge_keys)

        new_results = []

        kg = message.knowledge_graph
        kg_edges = kg.edges
        aux_graphs = message.auxiliary_graphs
        if aux_graphs is None:
            aux_graphs = {}
            message.auxiliary_graphs = aux_graphs

        for result in message.results:
            if not result.analyses:
                response.error(f"For result {result.essence}, there is no analysis support graph; "
                               "cannot transform this result")
                return
            analyses = result.analyses
            first_analysis = analyses[0]
            # First figure out which edges in this result are 'virtual' and what option groups they belong to
            edge_bindings = first_analysis.edge_bindings
            qedge_keys_in_result = set(edge_bindings)
            virtual_qedge_keys = qedge_keys_in_result.difference(original_qedge_keys)
            all_virtual_qedge_keys = all_virtual_qedge_keys.union(virtual_qedge_keys)  # Record these for log info
            virtual_edge_groups_dict: defaultdict[str | None, set[str]] = defaultdict(set)
            for virtual_qedge_key in virtual_qedge_keys:
                virtual_qedge = message.query_graph.edges[virtual_qedge_key]
                option_group_id = virtual_qedge.option_group_id
                virtual_edge_keys = {edge_binding.id for edge_binding in edge_bindings[virtual_qedge_key]}
                virtual_edge_groups_dict[option_group_id] = \
                    virtual_edge_groups_dict[option_group_id].union(virtual_edge_keys)
                # Note: All edges not belonging to an option group are lumped together under 'None' key

            # Create a support graph for each group
            if virtual_edge_groups_dict:
                if first_analysis.support_graphs is None:
                    first_analysis.support_graphs = []
            for group_id, group_edge_keys in virtual_edge_groups_dict.items():
                group_id_str = f"_{group_id}" if group_id else ""
                ordered_edge_keys = sorted(list(group_edge_keys))
                aux_graph_id_str = ";".join(ordered_edge_keys) \
                    if len(ordered_edge_keys) < 5 \
                    else f"{len(message.auxiliary_graphs)}"
                aux_graph_key = f"aux_graph_{aux_graph_id_str}{group_id_str}"
                # Create and save the aux graph in the central location (on Message), if it doesn't yet exist
                if aux_graph_key not in message.auxiliary_graphs:
                    message.auxiliary_graphs[aux_graph_key] = AuxiliaryGraph(edges=list(group_edge_keys),attributes=[])

                # Refer to this aux graph from the current Result or Edge (if this is an Infer support graph)
                if group_id and group_id.startswith("creative_"):
                    # Figure out which creative tool/method we're dealing with (e.g. creative_DTD, creative_expand)
                    group_id_prefix = "_".join(group_id.split("_")[:2])

                    # Create an attribute for the support graph that we'll tack onto the treats edge for this result
                    if group_id_prefix == "creative_DTD":
                        support_graph_attribute = Attribute(attribute_type_id="biolink:support_graphs",
                                                            value=[aux_graph_key],
                                                            attribute_source="infores:arax-xdtd")
                    else:
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
                        response.error("Query graph contains multiple 'inferred' qedges; don't know how to "
                                       "properly form support graphs!", error_code="UnsupportedQG")
                        return
                    else:
                        inferred_qedge_key = inferred_qedge_keys[0]
                        inferred_edge_keys = {edge_binding.id for edge_binding in
                                              first_analysis.edge_bindings[inferred_qedge_key]
                                              if group_id_prefix in edge_binding.id}
                        # Refer to the support graph from the proper edge(s)
                        for inferred_edge_key in inferred_edge_keys:
                            inferred_edge = kg_edges[inferred_edge_key]
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
                    first_analysis.support_graphs.append(aux_graph_key)

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
            qedge_keys_in_result = set(first_analysis.edge_bindings)  # May not include 'optional' edges in QG
            for non_orphan_qnode_key in non_orphan_qnode_keys:
                node_keys = {binding.id for binding in node_bindings[non_orphan_qnode_key]}
                node_keys_used_by_result_edges = {node_key for qedge_key in qedge_keys_in_result
                                                  for binding in first_analysis.edge_bindings[qedge_key]
                                                  for node_key in {kg_edges[binding.id].subject,
                                                                   kg_edges[binding.id].object}}
                orphan_node_keys = node_keys.difference(node_keys_used_by_result_edges)
                non_orphan_node_bindings = [binding for binding in node_bindings[non_orphan_qnode_key]
                                            if binding.id not in orphan_node_keys]
                node_bindings[non_orphan_qnode_key] = non_orphan_node_bindings


            # Creative-mode-only NGD-inf filter.
            #
            # An inferred-edge binding is "excludable" when either:
            #   (a) the inferred KG edge has no `biolink:support_graphs`
            #       attribute (or the value list is empty), or
            #   (b) the inferred edge has at least one support graph and
            #       removing every inf-NGD virtual edge from that support
            #       graph leaves the inferred edge's `subject` unable to
            #       reach its `object` (i.e. the support graph is critically
            #       dependent on those inf-NGD edges).
            #
            # We tentatively drop all excludable bindings; if doing so leaves
            # any original-QG qedge with no bindings, the result no longer
            # covers the QG and is dropped entirely. Otherwise the result is
            # kept with the excludable bindings removed and any orphaned node
            # bindings pruned.
            #
            # Non-creative-mode QGs (no inferred qedge) skip this filter
            # altogether.
            if is_creative_qg:
                excludable_edge_ids: set[str] = set()
                for inferred_qedge_key in inferred_qedge_keys:
                    for binding in first_analysis.edge_bindings.get(inferred_qedge_key, []):
                        inferred_edge = kg_edges.get(binding.id)
                        if inferred_edge is None:
                            continue
                        sg_keys: list[str] = []
                        for attr in (inferred_edge.attributes or []):
                            if getattr(attr, 'attribute_type_id', None) == "biolink:support_graphs":
                                for v in (attr.value or []):
                                    sg_keys.append(str(v))
                        if not sg_keys:
                            # case (a): inferred edge has no support graph at all
                            excludable_edge_ids.add(binding.id)
                            continue
                        # case (b): a support graph breaks under inf-NGD removal
                        for sg_key in sg_keys:
                            aux = aux_graphs.get(sg_key)
                            if aux is None:
                                continue
                            if _support_graph_breaks_without_inf_ngd(
                                    aux, kg_edges,
                                    src=inferred_edge.subject,
                                    dst=inferred_edge.object):
                                excludable_edge_ids.add(binding.id)
                                break

                # Tentatively prune excludable bindings from every qedge
                surviving_bindings = {qk: [b for b in bs if b.id not in excludable_edge_ids]
                                      for qk, bs in first_analysis.edge_bindings.items()}

                # Cover check: drop the result if any original qedge has no
                # surviving binding (then it no longer answers the user's QG)
                if not all(surviving_bindings.get(qk) for qk in original_qedge_keys):
                    continue

                first_analysis.edge_bindings = surviving_bindings

                # Re-prune any node bindings that no surviving edge references
                qedge_keys_after_filter = set(surviving_bindings)
                for non_orphan_qnode_key in non_orphan_qnode_keys:
                    node_keys = {b.id for b in node_bindings[non_orphan_qnode_key]}
                    node_keys_used = {nk
                                      for qk in qedge_keys_after_filter
                                      for binding in surviving_bindings[qk]
                                      for nk in (kg_edges[binding.id].subject,
                                                 kg_edges[binding.id].object)}
                    orphan_node_keys = node_keys - node_keys_used
                    node_bindings[non_orphan_qnode_key] = [
                        b for b in node_bindings[non_orphan_qnode_key]
                        if b.id not in orphan_node_keys]

                new_results.append(result)
            else:
                # Not a creative-mode QG: pass through unchanged
                new_results.append(result)

        # Report how many results were dropped by the creative-mode NGD-inf filter
        num_removed_results = len(message.results) - len(new_results)
        response.debug(f"Number of results eliminated by the creative-mode "
                       f"NGD-inf cover filter: {num_removed_results}")
        message.results = new_results
        if not message.results:
            response.warning("After creative-mode NGD-inf filtering, no results remain")

        # Update response's `total_results_count` field
        response.total_results_count = len(message.results)

        # Clean up the knowledge graph and auxiliary_graphs: with results
        # filtered (and inferred edges potentially removed from bindings),
        # some KG nodes/edges and aux graphs may now be unreferenced. Use the
        # shared resultify helper to compute the live reference closure
        # (following both `biolink:support_graphs` attributes on KG edges and
        # `Analysis.support_graphs` on results), then rebuild the KG and aux
        # graphs to contain only what is reachable.
        ref_nodes, ref_edges, ref_aux_graphs, _ref_results = \
            analyze_message_get_referenced_IDs(message, response)
        message.knowledge_graph = KnowledgeGraph(
            {nid: n for nid, n in message.knowledge_graph.nodes.items()
             if nid in ref_nodes},
            {eid: e for eid, e in message.knowledge_graph.edges.items()
             if eid in ref_edges})
        message.auxiliary_graphs = {aid: a
                                    for aid, a in message.auxiliary_graphs.items()
                                    if aid in ref_aux_graphs}

        # Return the original query graph in the response, rather than our edited version
        response.debug("Replacing ARAX's internal edited QG with the original input QG..")
        message.query_graph = response.original_query_graph

        # Log some final stats about result transformation
        response.debug(f"Virtual qedge keys moved to support_graphs were: {all_virtual_qedge_keys}")
        response.debug(f"There are a total of {len(message.auxiliary_graphs) if message.auxiliary_graphs else 0} AuxiliaryGraphs.")
        response.info("Done transforming results to TRAPI 1.5 format (i.e., using support_graphs)")
