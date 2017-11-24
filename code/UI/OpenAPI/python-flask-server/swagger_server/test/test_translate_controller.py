# coding: utf-8

from __future__ import absolute_import

from swagger_server.models.query import Query
from swagger_server.models.question import Question
from . import BaseTestCase
from six import BytesIO
from flask import json


class TestTranslateController(BaseTestCase):
    """ TranslateController integration test stubs """

    def test_translate(self):
        """
        Test case for translate

        Translate natural language question into a standardized query
        """
        body = Question()
        response = self.client.open('/api/rtx/v1/translate',
                                    method='POST',
                                    data=json.dumps(body),
                                    content_type='application/json')
        self.assert200(response, "Response body is : " + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
