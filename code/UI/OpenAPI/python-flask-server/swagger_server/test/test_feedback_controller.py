# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.test import BaseTestCase


class TestFeedbackController(BaseTestCase):
    """FeedbackController integration test stubs"""

    def test_get_feedback_all(self):
        """Test case for get_feedback_all

        Request a list of all feedback provided thus far
        """
        response = self.client.open(
            '/api/rtx/v1/feedback/all',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_feedback_expertise_levels(self):
        """Test case for get_feedback_expertise_levels

        Request a list of allowable expertise levels
        """
        response = self.client.open(
            '/api/rtx/v1/feedback/expertise_levels',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_feedback_ratings(self):
        """Test case for get_feedback_ratings

        Request a list of allowable ratings
        """
        response = self.client.open(
            '/api/rtx/v1/feedback/ratings',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
