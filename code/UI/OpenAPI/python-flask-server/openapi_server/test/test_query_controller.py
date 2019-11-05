# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.message import Message  # noqa: E501
from openapi_server.test import BaseTestCase


class TestQueryController(BaseTestCase):
    """QueryController integration test stubs"""

    def test_query(self):
        """Test case for query

        Query reasoner via one of several inputs
        """
        request_body = None
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/api/rtx/v1/query',
            method='POST',
            headers=headers,
            data=json.dumps(request_body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
