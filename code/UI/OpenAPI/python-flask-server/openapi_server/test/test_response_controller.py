# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.response import Response  # noqa: E501
from openapi_server.test import BaseTestCase


class TestResponseController(BaseTestCase):
    """ResponseController integration test stubs"""

    def test_get_response(self):
        """Test case for get_response

        Request a previously stored response from the server
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/arax/v1/response/{response_id}'.format(response_id=56),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
