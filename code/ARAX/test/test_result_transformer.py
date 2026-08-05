import copy
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../UI/OpenAPI/python-flask-server")

from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse
from result_transformer import ResultTransformer

from openapi_server.models.analysis import Analysis
from openapi_server.models.attribute import Attribute
from openapi_server.models.auxiliary_graph import AuxiliaryGraph
from openapi_server.models.edge import Edge
from openapi_server.models.edge_binding import EdgeBinding
from openapi_server.models.knowledge_graph import KnowledgeGraph
from openapi_server.models.message import Message
from openapi_server.models.node import Node
from openapi_server.models.node_binding import NodeBinding
from openapi_server.models.q_edge import QEdge
from openapi_server.models.q_node import QNode
from openapi_server.models.query_graph import QueryGraph
from openapi_server.models.response import Response
from openapi_server.models.result import Result

def test_creative_noninf_ngd_only_support_graph_filters_result():
    """Programmatically construct a TRAPI message with one inferred-mode
    drug-treats-disease result whose only support graph contains a single
    finite-score-NGD edge, and confirm that ResultTransformer.transform filters
    the result out (because removing the inf-NGD edge leaves the support graph
    disconnected, making the inferred-edge binding excludable, which in turn
    leaves the original qedge with no surviving binding).

    """

    drug_id = "CHEBI:6809"            # metformin
    disease_id = "MONDO:0005015"      # diabetes
    qnode_drug, qnode_disease = "n_drug", "n_disease"
    qedge_treats = "e_treats"
    inferred_edge_id = "kg2:inferred_treats"
    ngd_edge_id = "kg2:ngd_co_occur"
    aux_graph_id = "aux_inf_ngd_only"

    # Original (input) query graph: drug --treats[inferred]--> diabetes
    original_qg = QueryGraph(
        nodes={
            qnode_drug: QNode(categories=["biolink:ChemicalEntity"]),
            qnode_disease: QNode(categories=["biolink:Disease"], ids=[disease_id]),
        },
        edges={
            qedge_treats: QEdge(
                knowledge_type="inferred",
                predicates=["biolink:treats"],
                subject=qnode_drug,
                object=qnode_disease,
            ),
        },
    )
    # ARAX may have edited the QG by the time transform() runs; pass an
    # independent copy as the message's working query_graph.
    working_qg = copy.deepcopy(original_qg)

    # Knowledge graph: the inferred treats edge (carrying a support_graphs
    # attribute that points at the lone aux graph) and the inf-NGD edge that
    # the aux graph contains.
    kg_nodes = {
        drug_id: Node(name="metformin", categories=["biolink:ChemicalEntity"]),
        disease_id: Node(name="diabetes mellitus", categories=["biolink:Disease"]),
    }
    inferred_edge = Edge(
        predicate="biolink:treats",
        subject=drug_id,
        object=disease_id,
        attributes=[
            Attribute(
                attribute_type_id="biolink:support_graphs",
                value=[aux_graph_id],
                attribute_source="infores:arax",
            ),
        ],
    )
    ngd_edge = Edge(
        predicate="biolink:occurs_together_in_literature_with",
        subject=drug_id,
        object=disease_id,
        attributes=[
            Attribute(
                attribute_type_id="biolink:Attribute",
                original_attribute_name="normalized_google_distance",
                value=0.5,
                attribute_source="infores:arax",
            ),
        ],
    )
    kg = KnowledgeGraph(nodes=kg_nodes,
                        edges={inferred_edge_id: inferred_edge,
                               ngd_edge_id: ngd_edge})

    # The lone aux graph contains only the inf-NGD edge: removing it leaves
    # no path from drug to disease, so the support graph "breaks".
    aux_graphs = {aux_graph_id: AuxiliaryGraph(edges=[ngd_edge_id], attributes=[])}

    # Single result binding the inferred edge to the original qedge.
    analysis = Analysis(
        resource_id="infores:arax",
        edge_bindings={qedge_treats: [EdgeBinding(id=inferred_edge_id)]},
    )
    result = Result(
        node_bindings={qnode_drug: [NodeBinding(id=drug_id)],
                       qnode_disease: [NodeBinding(id=disease_id)]},
        analyses=[analysis],
        essence="metformin",
    )

    message = Message(query_graph=working_qg, knowledge_graph=kg,
                      results=[result], auxiliary_graphs=aux_graphs)

    response = ARAXResponse()
    response.envelope = Response(message=message)
    response.original_query_graph = original_qg

    assert len(message.results) == 1, "precondition: one result before transform()"

    ResultTransformer.transform(response)

    assert message.results, (
        "expected the noninf-NGD-only-support-graph result to be not be filtered out, "
        "but it was in fact filtered out")
    # The inferred edge should also have been pruned from the KG by the
    # post-filter cleanup pass (no surviving result references it).
    assert inferred_edge_id in message.knowledge_graph.edges, (
        "expected the now-unreferenced inferred edge to be pruned from the KG")
    assert aux_graph_id in (message.auxiliary_graphs or {}), (
        "expected the now-unreferenced aux graph to be pruned")


def test_creative_inf_ngd_only_support_graph_filters_result():
    """Programmatically construct a TRAPI message with one inferred-mode
    drug-treats-disease result whose only support graph contains a single
    inf-NGD edge, and confirm that ResultTransformer.transform filters the
    result out (because removing the inf-NGD edge leaves the support graph
    disconnected, making the inferred-edge binding excludable, which in turn
    leaves the original qedge with no surviving binding)."""

    drug_id = "CHEBI:6809"            # metformin
    disease_id = "MONDO:0005015"      # diabetes
    qnode_drug, qnode_disease = "n_drug", "n_disease"
    qedge_treats = "e_treats"
    inferred_edge_id = "kg2:inferred_treats"
    ngd_edge_id = "kg2:ngd_co_occur"
    aux_graph_id = "aux_inf_ngd_only"

    # Original (input) query graph: drug --treats[inferred]--> diabetes
    original_qg = QueryGraph(
        nodes={
            qnode_drug: QNode(categories=["biolink:ChemicalEntity"]),
            qnode_disease: QNode(categories=["biolink:Disease"], ids=[disease_id]),
        },
        edges={
            qedge_treats: QEdge(
                knowledge_type="inferred",
                predicates=["biolink:treats"],
                subject=qnode_drug,
                object=qnode_disease,
            ),
        },
    )
    # ARAX may have edited the QG by the time transform() runs; pass an
    # independent copy as the message's working query_graph.
    working_qg = copy.deepcopy(original_qg)

    # Knowledge graph: the inferred treats edge (carrying a support_graphs
    # attribute that points at the lone aux graph) and the inf-NGD edge that
    # the aux graph contains.
    kg_nodes = {
        drug_id: Node(name="metformin", categories=["biolink:ChemicalEntity"]),
        disease_id: Node(name="diabetes mellitus", categories=["biolink:Disease"]),
    }
    inferred_edge = Edge(
        predicate="biolink:treats",
        subject=drug_id,
        object=disease_id,
        attributes=[
            Attribute(
                attribute_type_id="biolink:support_graphs",
                value=[aux_graph_id],
                attribute_source="infores:arax",
            ),
        ],
    )
    ngd_edge = Edge(
        predicate="biolink:occurs_together_in_literature_with",
        subject=drug_id,
        object=disease_id,
        attributes=[
            Attribute(
                attribute_type_id="biolink:Attribute",
                original_attribute_name="normalized_google_distance",
                value="inf",
                attribute_source="infores:arax",
            ),
        ],
    )
    kg = KnowledgeGraph(nodes=kg_nodes,
                        edges={inferred_edge_id: inferred_edge,
                               ngd_edge_id: ngd_edge})

    # The lone aux graph contains only the inf-NGD edge: removing it leaves
    # no path from drug to disease, so the support graph "breaks".
    aux_graphs = {aux_graph_id: AuxiliaryGraph(edges=[ngd_edge_id], attributes=[])}

    # Single result binding the inferred edge to the original qedge.
    analysis = Analysis(
        resource_id="infores:arax",
        edge_bindings={qedge_treats: [EdgeBinding(id=inferred_edge_id)]},
    )
    result = Result(
        node_bindings={qnode_drug: [NodeBinding(id=drug_id)],
                       qnode_disease: [NodeBinding(id=disease_id)]},
        analyses=[analysis],
        essence="metformin",
    )

    message = Message(query_graph=working_qg, knowledge_graph=kg,
                      results=[result], auxiliary_graphs=aux_graphs)

    response = ARAXResponse()
    response.envelope = Response(message=message)
    response.original_query_graph = original_qg

    assert len(message.results) == 1, "precondition: one result before transform()"

    ResultTransformer.transform(response)

    assert message.results == [], (
        "expected the inf-NGD-only-support-graph result to be filtered out, "
        f"but {len(message.results)} result(s) remain")
    # The inferred edge should also have been pruned from the KG by the
    # post-filter cleanup pass (no surviving result references it).
    assert inferred_edge_id not in message.knowledge_graph.edges, (
        "expected the now-unreferenced inferred edge to be pruned from the KG")
    assert aux_graph_id not in (message.auxiliary_graphs or {}), (
        "expected the now-unreferenced aux graph to be pruned")


def test_creative_inferred_edge_without_support_graph_filters_result():
    """Programmatically construct a TRAPI message with one creative-mode
    (inferred-qedge) drug-treats-disease result whose inferred KG edge has
    no `biolink:support_graphs` attribute at all, and confirm that
    ResultTransformer.transform filters the result out.

    Per the new filter rule, an inferred-edge binding with no support graph
    is "excludable" via case (a). With this result's only inferred-edge
    binding excludable, the original qedge ends up with zero surviving
    bindings, so the result no longer covers the QG and is dropped."""

    drug_id = "CHEBI:6809"            # metformin
    disease_id = "MONDO:0005015"      # diabetes
    qnode_drug, qnode_disease = "n_drug", "n_disease"
    qedge_treats = "e_treats"
    inferred_edge_id = "kg2:inferred_treats_no_support"

    # Original (input) query graph: drug --treats[inferred]--> diabetes
    original_qg = QueryGraph(
        nodes={
            qnode_drug: QNode(categories=["biolink:ChemicalEntity"]),
            qnode_disease: QNode(categories=["biolink:Disease"], ids=[disease_id]),
        },
        edges={
            qedge_treats: QEdge(
                knowledge_type="inferred",
                predicates=["biolink:treats"],
                subject=qnode_drug,
                object=qnode_disease,
            ),
        },
    )
    working_qg = copy.deepcopy(original_qg)

    # Knowledge graph: just the inferred treats edge with NO support_graphs
    # attribute. (A non-support-graphs attribute is included to confirm the
    # filter checks attribute_type_id, not just the presence of attributes.)
    kg_nodes = {
        drug_id: Node(name="metformin", categories=["biolink:ChemicalEntity"]),
        disease_id: Node(name="diabetes mellitus", categories=["biolink:Disease"]),
    }
    inferred_edge = Edge(
        predicate="biolink:treats",
        subject=drug_id,
        object=disease_id,
        attributes=[
            Attribute(
                attribute_type_id="biolink:agent_type",
                value="computational_model",
                attribute_source="infores:arax",
            ),
        ],
    )
    kg = KnowledgeGraph(nodes=kg_nodes, edges={inferred_edge_id: inferred_edge})

    # No aux graphs needed for this scenario.
    aux_graphs: dict = {}

    analysis = Analysis(
        resource_id="infores:arax",
        edge_bindings={qedge_treats: [EdgeBinding(id=inferred_edge_id)]},
    )
    result = Result(
        node_bindings={qnode_drug: [NodeBinding(id=drug_id)],
                       qnode_disease: [NodeBinding(id=disease_id)]},
        analyses=[analysis],
        essence="metformin",
    )

    message = Message(query_graph=working_qg, knowledge_graph=kg,
                      results=[result], auxiliary_graphs=aux_graphs)

    response = ARAXResponse()
    response.envelope = Response(message=message)
    response.original_query_graph = original_qg

    assert len(message.results) == 1, "precondition: one result before transform()"

    ResultTransformer.transform(response)

    assert message.results == [], (
        "expected the result with a support-graph-less inferred edge to be "
        f"filtered out, but {len(message.results)} result(s) remain")
    # The inferred edge should have been pruned from the KG by the
    # post-filter cleanup pass (no surviving result references it).
    assert inferred_edge_id not in message.knowledge_graph.edges, (
        "expected the now-unreferenced inferred edge to be pruned from the KG")



    
