# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.test import BaseTestCase


class TestEntityController(BaseTestCase):
    """EntityController integration test stubs"""

    def test_get_entity_by_string(self):
        """Test case for get_entity_by_string

        Obtain the CURIE and type of some entity by name
        """
        response = self.client.open(
            '/api/rtx/v1/entity/{search_string}'.format(search_string='search_string_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
