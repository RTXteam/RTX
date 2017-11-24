# coding: utf-8

from __future__ import absolute_import

from swagger_server.models.query import Query
from swagger_server.models.response import Response
from . import BaseTestCase
from six import BytesIO
from flask import json


class TestQueryController(BaseTestCase):
    """ QueryController integration test stubs """

    def test_query(self):
        """
        Test case for query

        Query RTX using a predefined question type
        """
        body = Query()
        response = self.client.open('/api/rtx/v1/query',
                                    method='POST',
                                    data=json.dumps(body),
                                    content_type='application/json')
        self.assert200(response, "Response body is : " + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
