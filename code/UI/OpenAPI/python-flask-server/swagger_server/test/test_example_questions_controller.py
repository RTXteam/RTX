# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.test import BaseTestCase


class TestExampleQuestionsController(BaseTestCase):
    """ExampleQuestionsController integration test stubs"""

    def test_example_questions(self):
        """Test case for example_questions

        Request a list of example questions that RTX can answer
        """
        response = self.client.open(
            '/api/rtx/v1/exampleQuestions',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
