# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.me_shngd_response import MeSHNGDResponse  # noqa: E501
from swagger_server.test import BaseTestCase


class TestGetPubMedMeSHNGDController(BaseTestCase):
    """GetPubMedMeSHNGDController integration test stubs"""

    def test_get_pub_med_me_shngd(self):
        """Test case for get_pub_med_me_shngd

        Query to get the Normalized Google Distance between two MeSH terms based on co-occurance in all PubMed article annotations
        """
        response = self.client.open(
            '/api/rtx/v1/getPubMedMeSHNGD/{term1}/{term2}'.format(term1='term1_example', term2='term2_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
