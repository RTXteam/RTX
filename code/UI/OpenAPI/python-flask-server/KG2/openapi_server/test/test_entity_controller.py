# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.test import BaseTestCase


class TestEntityController(BaseTestCase):
    """EntityController integration test stubs"""

    def test_get_entity(self):
        """Test case for get_entity

        Obtain CURIE and synonym information about a search term
        """
        query_string = [('q', ["MESH:D014867","NCIT:C34373"])]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/rtxkg2/v1.0/entity',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
