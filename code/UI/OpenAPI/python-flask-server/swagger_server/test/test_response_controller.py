# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.query import Query  # noqa: E501
from swagger_server.models.response import Response  # noqa: E501
from swagger_server.models.response_feedback import ResponseFeedback  # noqa: E501
from swagger_server.models.result import Result  # noqa: E501
from swagger_server.models.result_feedback import ResultFeedback  # noqa: E501
from swagger_server.test import BaseTestCase


class TestResponseController(BaseTestCase):
    """ResponseController integration test stubs"""

    def test_get_response(self):
        """Test case for get_response

        Request stored responses and results from RTX
        """
        response = self.client.open(
            '/api/rtx/v1/response/{response_id}'.format(response_id=56),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_response_feedback(self):
        """Test case for get_response_feedback

        Request stored feedback for this response from RTX
        """
        response = self.client.open(
            '/api/rtx/v1/response/{response_id}/feedback'.format(response_id=56),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_result(self):
        """Test case for get_result

        Request stored responses and results from RTX
        """
        response = self.client.open(
            '/api/rtx/v1/response/{response_id}/result/{result_id}'.format(response_id=56, result_id=56),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_result_feedback(self):
        """Test case for get_result_feedback

        Request stored feedback for this result from RTX
        """
        response = self.client.open(
            '/api/rtx/v1/response/{response_id}/result/{result_id}/feedback'.format(response_id=56, result_id=56),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_post_result_feedback(self):
        """Test case for post_result_feedback

        Store feedback for a particular result
        """
        body = Query()
        response = self.client.open(
            '/api/rtx/v1/response/{response_id}/result/{result_id}/feedback'.format(response_id=56, result_id=56),
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
