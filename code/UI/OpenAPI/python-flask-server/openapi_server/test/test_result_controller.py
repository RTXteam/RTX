# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.feedback import Feedback  # noqa: E501
from openapi_server.models.feedback_response import FeedbackResponse  # noqa: E501
from openapi_server.models.result import Result  # noqa: E501
from openapi_server.models.result_feedback import ResultFeedback  # noqa: E501
from openapi_server.test import BaseTestCase


class TestResultController(BaseTestCase):
    """ResultController integration test stubs"""

    def test_get_result(self):
        """Test case for get_result

        Request stored result
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/rtx/v1/result/{result_id}'.format(result_id=56),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_result_feedback(self):
        """Test case for get_result_feedback

        Request stored feedback for this result
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/rtx/v1/result/{result_id}/feedback'.format(result_id=56),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_post_result_feedback(self):
        """Test case for post_result_feedback

        Store feedback for a particular result
        """
        feedback = {
  "commenter_id" : 1,
  "datetime" : "2018-05-08 12:00",
  "rating_id" : 1,
  "result_id" : "https://rtx.ncats.io/api/rtx/v1/result/234",
  "expertise_level_id" : 1,
  "comment" : "This is a great result because...",
  "id" : "https://rtx.ncats.io/api/rtx/v1/result/234/feedback/56",
  "commenter_full_name" : "John Smith"
}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/api/rtx/v1/result/{result_id}/feedback'.format(result_id=56),
            method='POST',
            headers=headers,
            data=json.dumps(feedback),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
