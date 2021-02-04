import connexion
import six

from openapi_server.models.mesh_ngd_response import MeshNgdResponse  # noqa: E501
from openapi_server import util

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../../reasoningtool/kg-construction/")
from NormGoogleDistance import NormGoogleDistance


def pubmed_mesh_ngd(term1, term2):  # noqa: E501
    """Query to get the Normalized Google Distance between two MeSH terms based on co-occurrence in all PubMed article annotations

     # noqa: E501

    :param term1: First of two terms. Order not important.
    :type term1: str
    :param term2: Second of two terms. Order not important.
    :type term2: str

    :rtype: MeshNgdResponse
    """
    cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.abspath(__file__))+"/../../../../../reasoningtool/kg-construction")
    ngd = NormGoogleDistance()
    response = ngd.api_ngd(term1,term2)
    os.chdir(cwd)
    return(response)

