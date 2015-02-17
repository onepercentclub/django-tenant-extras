import sys

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from ..middleware import LocaleRedirectMiddleware


class LocaleRedirectMiddlewareTests(TestCase):

    def setUp(self):
        self.rf = RequestFactory()
        self.middleware = LocaleRedirectMiddleware()

    def test_slash_with_anon_user(self):
        request = self.rf.get('/')
        result = self.middleware.process_request(request)

        self.assertEqual(result.url, '/en/')

    def test_nl_with_anon_user(self):
        request = self.rf.get('/nl/')
        result = self.middleware.process_request(request)

        self.assertIsNone(result, 'Should not alter the request if language set in url')

    def test_cookie_with_anon_user(self):
        request = self.rf.get('/en/')
        request.COOKIES['django_language'] = 'nl'
        result = self.middleware.process_request(request)

        self.assertEqual(result.url, '/nl/')

    def test_full_path_with_anon_user(self):
        request = self.rf.get('/go/projects')
        result = self.middleware.process_request(request)

        self.assertEqual(result.url, '/en/go/projects')
