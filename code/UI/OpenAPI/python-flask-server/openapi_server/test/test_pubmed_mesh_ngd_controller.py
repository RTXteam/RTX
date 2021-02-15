# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.mesh_ngd_response import MeshNgdResponse  # noqa: E501
from openapi_server.test import BaseTestCase


class TestPubmedMeshNgdController(BaseTestCase):
    """PubmedMeshNgdController integration test stubs"""

    def test_pubmed_mesh_ngd(self):
        """Test case for pubmed_mesh_ngd

        Query to get the Normalized Google Distance between two MeSH terms based on co-occurrence in all PubMed article annotations
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/arax/v1/PubmedMeshNgd/{term1}/{term2}'.format(term1='term1_example', term2='term2_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
