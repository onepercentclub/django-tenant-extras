import sys
import mock
import json

from collections import namedtuple

from bunch import bunchify

from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.db.backends.sqlite3.base import DatabaseWrapper


from ..middleware import LocaleRedirectMiddleware, TenantLocaleMiddleware

@override_settings(MULTI_TENANT_DIR='/clients', INSTALLED_APPS=(), LOCALE_PATHS=())
class TenantLocaleMiddlewareTests(TestCase):
    def setUp(self):
        super(TenantLocaleMiddlewareTests, self).setUp()

        self.rf = RequestFactory()
        self.middleware = TenantLocaleMiddleware()

    def test_valid_tenant_locale(self):
        with mock.patch("tenant_extras.middleware.connection") as mock_c, \
             mock.patch("tenant_extras.middleware._translation") as mock_t, \
             mock.patch("os.path.isdir", return_value=True):

            mock_c.tenant = mock.Mock(client_name="tenant_a")
            request = self.rf.get('/nl/')
            result = self.middleware.process_request(request)

            last_call_path = mock_t.call_args_list[-1][0][0]
            self.assertEquals(last_call_path, '/clients/tenant_a/locale')

            mock_c.tenant = mock.Mock(client_name="tenant_b")
            request = self.rf.get('/nl/')
            result = self.middleware.process_request(request)

            last_call_path = mock_t.call_args_list[-1][0][0]
            self.assertEquals(last_call_path, '/clients/tenant_b/locale')

                    
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

    def test_go_path_with_anon_user(self):
        request = self.rf.get('/go/projects')
        result = self.middleware.process_request(request)

        self.assertIsNone(result, 'Go paths should not redirect')

    def test_admin_path_with_anon_user(self):
        request = self.rf.get('/admin')
        result = self.middleware.process_request(request)

        self.assertEqual(result.url, '/en/admin')


@mock.patch('django.db.connection', bunchify({'tenant': {'name': 'My Test', 'client_name': 'test'}}))
class ConfContextProcessorTestCase(TestCase):

    def setUp(self):
        self.rf = RequestFactory()
        self.rf.LANGUAGE_CODE = 'nl'

    def test_default_settings_property_list(self):
        from ..context_processors import conf_settings
        context = conf_settings(self.rf)

        self.assertEqual(context['DEBUG'], False)
        self.assertEqual(context['TENANT_LANGUAGE'], 'testnl')
        self.assertEqual(context['COMPRESS_TEMPLATES'], False)
    

@mock.patch('django.db.connection', bunchify({'tenant': {'name': 'My Test', 'client_name': 'test'}}))
class TenantPropertiesContextProcessorTestCase(TestCase):

    def setUp(self):
        self.rf = RequestFactory()

    @override_settings(EXPOSED_TENANT_PROPERTIES=['test'], TEST='value-for-test')
    def test_default_settings_property_list(self):
        from ..context_processors import tenant_properties
        context = tenant_properties(self.rf)
        self.assertEqual(context['TEST'], 'value-for-test')
        # Check that the added value is in the context
        self.assertIn('"TEST": "value-for-test"', str(context['settings']))
    
    @override_settings(EXPOSED_TENANT_PROPERTIES=['test'], TEST='value-for-test',
                       TENANT_PROPERTIES="tenant_extras.tests.properties.properties2")
    def test_tenant_specific_property_list(self):
        from ..context_processors import tenant_properties

        # Check that Tenant test-value specified in properties2 is used.
        context = tenant_properties(self.rf)
        self.assertEqual(context['TEST'], 'my-very-own-test-value')
        self.assertIn('"TEST": "my-very-own-test-value"', context['settings'])

    def test_no_exposed_tenant_properties_setting(self):
        with mock.patch('tenant_extras.utils.get_tenant_properties') as get_tenant_properties, \
                mock.patch('django.conf.settings', spec={}) as settings:
            
            from ..context_processors import tenant_properties
            
            get_tenant_properties.return_value = {}

            context = tenant_properties(self.rf)
            self.assertEqual(context, {})

from ..drf_permissions import TenantConditionalOpenClose

class TestDRFTenantPermission(TestCase):
    """
        Verify the permission that can enable/disable API access based on a
        tenant property
    """

    auth_user = mock.Mock(**{"user.is_authenticated.return_value":True})
    unauth_user = mock.Mock(**{"user.is_authenticated.return_value":False})

    def test_missing_setting(self):
        """ No tenant property at all - default to public """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = object()

            self.failUnless(TenantConditionalOpenClose().has_permission(self.unauth_user, None))

    def test_api_open(self):
        """ There is a tenant property and it's open """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = namedtuple('props', ['CLOSED_SITE'])(False)

            self.failUnless(TenantConditionalOpenClose().has_permission(self.unauth_user, None))

    def test_api_closed_unauth(self):
        """ There is a tenant property and it's closed, user is not authenticated """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = namedtuple('props', ['CLOSED_SITE'])(True)


            self.failIf(TenantConditionalOpenClose().has_permission(self.unauth_user, None))

    def test_api_closed_auth(self):
        """ There is a tenant property and it's closed, user IS authenticated """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = namedtuple('props', ['CLOSED_SITE'])(True)

            self.failUnless(TenantConditionalOpenClose().has_permission(self.auth_user, None))
