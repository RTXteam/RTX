# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.test import BaseTestCase


class TestPredicatesController(BaseTestCase):
    """PredicatesController integration test stubs"""

    def test_predicates_get(self):
        """Test case for predicates_get

        Get supported relationships by source and target
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/arax/v1/predicates',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
