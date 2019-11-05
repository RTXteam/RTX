# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.message import Message  # noqa: E501
from swagger_server.models.query import Query  # noqa: E501
from swagger_server.test import BaseTestCase


class TestQueryController(BaseTestCase):
    """QueryController integration test stubs"""

    def test_query(self):
        """Test case for query

        Query RTX via one of several inputs
        """
        body = Query()
        response = self.client.open(
            '/api/rtx/v1/query',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
