# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.expertise_levels import ExpertiseLevels  # noqa: E501
from openapi_server.models.feedback import Feedback  # noqa: E501
from openapi_server.models.ratings import Ratings  # noqa: E501
from openapi_server.test import BaseTestCase


class TestFeedbackController(BaseTestCase):
    """FeedbackController integration test stubs"""

    def test_get_feedback_all(self):
        """Test case for get_feedback_all

        Request a list of all feedback provided thus far
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/rtx/v1/feedback/all',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_feedback_expertise_levels(self):
        """Test case for get_feedback_expertise_levels

        Request a list of allowable expertise levels
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/rtx/v1/feedback/expertise_levels',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_feedback_ratings(self):
        """Test case for get_feedback_ratings

        Request a list of allowable ratings
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/rtx/v1/feedback/ratings',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
