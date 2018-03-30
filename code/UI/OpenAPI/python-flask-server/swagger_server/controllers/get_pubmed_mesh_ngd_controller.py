import connexion
import six

from swagger_server.models.mesh_ngd_response import MeshNgdResponse  # noqa: E501
from swagger_server import util


def get_pubmed_mesh_ngd(term1, term2):  # noqa: E501
    """Query to get the Normalized Google Distance between two MeSH terms based on co-occurance in all PubMed article annotations

     # noqa: E501

    :param term1: First of two terms. Order not important.
    :type term1: str
    :param term2: Second of two terms. Order not important.
    :type term2: str

    :rtype: MeshNgdResponse
    """
    return 'do some magic!'
