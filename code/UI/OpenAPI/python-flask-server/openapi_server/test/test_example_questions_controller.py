# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.test import BaseTestCase


class TestExampleQuestionsController(BaseTestCase):
    """ExampleQuestionsController integration test stubs"""

    def test_example_questions(self):
        """Test case for example_questions

        Request a list of example questions that ARAX can answer
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/arax/v1/exampleQuestions',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
