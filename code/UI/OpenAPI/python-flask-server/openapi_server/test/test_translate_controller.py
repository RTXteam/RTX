# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.query import Query  # noqa: E501
from openapi_server.test import BaseTestCase


class TestTranslateController(BaseTestCase):
    """TranslateController integration test stubs"""

    def test_translate(self):
        """Test case for translate

        Translate natural language question into a standardized query
        """
        request_body = None
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/api/arax/v1/translate',
            method='POST',
            headers=headers,
            data=json.dumps(request_body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
