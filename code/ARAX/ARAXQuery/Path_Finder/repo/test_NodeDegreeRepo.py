from code.ARAX.ARAXQuery.Path_Finder.model.Node import Node
from code.ARAX.ARAXQuery.Path_Finder.repo.NodeDegreeRepo import NodeDegreeRepo


def test_get_node_degree():
    repo = NodeDegreeRepo()
    assert repo.get_node_degree(Node(id="PUBCHEM.COMPOUND:5105")) == 241
