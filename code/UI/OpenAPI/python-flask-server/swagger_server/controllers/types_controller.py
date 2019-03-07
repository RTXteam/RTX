import connexion
import six

from swagger_server import util

from RTXQuery import RTXQuery


def get_all_edge_types():  # noqa: E501
    """Obtain all possible types of edges

     # noqa: E501


    :rtype: None
    """
    rtxq = RTXQuery()
    return(rtxq.get_all_edge_types())    


def get_node_edge_types(node_type):  # noqa: E501
    """Obtain all possible types of edges linked to a node_type

     # noqa: E501

    :param node_type: Node type to filter possible edges by
    :type node_type: str

    :rtype: None
    """
    rtxq = RTXQuery()
    return(rtxq.get_node_edge_types(node_type))    


def get_node_to_node_edge_types(node_type1, node_type2):  # noqa: E501
    """Obtain all possible types of edges linking node_type1 and node_type2

     # noqa: E501

    :param node_type1: Node type 1 to filter possible edges by
    :type node_type1: str
    :param node_type2: Node type 2 to filter possible edges by
    :type node_type2: str

    :rtype: None
    """
    rtxq = RTXQuery()
    return(rtxq.get_node_to_node_edge_types(node_type1,node_type2))    


def get_node_types():  # noqa: E501
    """Obtain all possible types of nodes

     # noqa: E501


    :rtype: None
    """
    rtxq = RTXQuery()
    return(rtxq.get_node_types())    
