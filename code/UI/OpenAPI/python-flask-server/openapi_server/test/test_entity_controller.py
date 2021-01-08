# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.test import BaseTestCase


class TestEntityController(BaseTestCase):
    """EntityController integration test stubs"""

    def test_get_entity_by_string(self):
        """Test case for get_entity_by_string

        Obtain the CURIE and type of some entity by name
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/arax/v1/entity/{search_string}'.format(search_string='search_string_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
