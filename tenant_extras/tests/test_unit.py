import os
import mock
from mock import patch

from bunch import bunchify

from django.utils.translation import ugettext as _
from django.conf import settings
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.db import connection

from ..drf_permissions import TenantConditionalOpenClose
from ..middleware import TenantLocaleMiddleware
from ..utils import TenantLanguage


@override_settings(MULTI_TENANT_DIR='/clients', INSTALLED_APPS=(),
                   LOCALE_PATHS=(), LOCALE_REDIRECT_IGNORE=('/api', '/go'))
class TenantLocaleMiddlewareRedirectTests(TestCase):
    def setUp(self):
        super(TenantLocaleMiddlewareRedirectTests, self).setUp()

        self.rf = RequestFactory()
        self.middleware = TenantLocaleMiddleware()

    @patch.object(TenantLocaleMiddleware, 'is_language_prefix_patterns_used')
    @patch.object(TenantLocaleMiddleware, 'process_request')
    def _process_response(self, request, mock_process_request, mock_other):
        mock_other.return_value = True
        response = HttpResponse()
        result = self.middleware.process_response(request, response)
        return result

    def test_go_path(self):
        request = self.rf.get('/go/projects')
        result = self._process_response(request)

        self.assertIsInstance(result, HttpResponse,
                    'Go paths should not redirect')

    def test_api_path(self):
        request = self.rf.get('/api/projects/1')
        result = self._process_response(request)

        self.assertIsInstance(result, HttpResponse,
                    'API paths should not redirect')

    def test_projects_path_with_anon_user(self):
        request = self.rf.get('/projects/1')
        result = self._process_response(request)

        self.assertEqual(result.url, '/en/projects/1')

    def test_slash_with_anon_user(self):
        request = self.rf.get('/')
        result = self._process_response(request)
        self.assertEqual(result.url, '/en/')

    def test_nl_with_anon_user(self):
        request = self.rf.get('/nl/')
        result = self._process_response(request)

        self.assertIsInstance(result, HttpResponse,
                   'Should not alter the request if language set in url')

    def test_admin_path_with_anon_user(self):
        request = self.rf.get('/admin')
        result = self._process_response(request)

        self.assertEqual(result.url, '/en/admin')


@mock.patch('django.db.connection',
            bunchify({'tenant': {'name': 'My Test', 'client_name': 'test'}}))
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


@override_settings(MULTI_TENANT_DIR=os.path.join(settings.PROJECT_ROOT,
                   'tests', 'tenants'),)
class TenantLocaleTestCase(TestCase):

    def setUp(self):
        self.tenant1 = bunchify({
            'name': 'My Test',
            'client_name': 'tenant1'
        })

        self.tenant2 = bunchify({
            'name': 'My Test',
            'client_name': 'tenant2'
        })

    def test_valid_tenant_language(self):
        connection.tenant = self.tenant1
        with TenantLanguage('en'):
            self.assertEqual(_('Tenant Name'), 'Tenant 1 EN')

        with TenantLanguage('nl'):
            self.assertEqual(_('Tenant Name'), 'Tenant 1 NL')

        with TenantLanguage('sp'):
            self.assertEqual(_('Tenant Name'), 'Tenant 1 EN')

    def test_tenant_language_fallback(self):
        connection.tenant = self.tenant1
        with TenantLanguage('sp'):
            self.assertEqual(_('Tenant Name'), 'Tenant 1 EN')

    def test_multi_tenant_languages(self):
        connection.tenant = self.tenant1
        with TenantLanguage('en'):
            # This will cache the en locale for tenant1
            pass

        connection.tenant = self.tenant2
        with TenantLanguage('en'):
            self.assertEqual(_('Tenant Name'), 'Tenant 2 EN',
                             'Tenant 2 should not have translations from Tenant 1')


@mock.patch('django.db.connection',
            bunchify({'tenant': {'name': 'My Test', 'client_name': 'test'}}))
class TenantPropertiesContextProcessorTestCase(TestCase):

    def setUp(self):
        self.rf = RequestFactory()

    @override_settings(EXPOSED_TENANT_PROPERTIES=['test', 'this_is_a_snake'],
                       TEST='value-for-test',
                       THIS_IS_A_SNAKE=True)
    def test_default_settings_property_list(self):
        from ..context_processors import tenant_properties
        context = tenant_properties(self.rf)
        self.assertEqual(context['TEST'], 'value-for-test')
        # Check that the added value is in the context
        self.assertIn('"test": "value-for-test"', str(context['settings']))
        self.assertIn('"thisIsASnake": true', context['settings'])

    @override_settings(EXPOSED_TENANT_PROPERTIES=['test'],
                       TEST='value-for-test',
                       TENANT_PROPERTIES="tenant_extras.tests.properties.properties2")
    def test_tenant_specific_property_list(self):
        from ..context_processors import tenant_properties

        # Check that Tenant test-value specified in properties2 is used.
        context = tenant_properties(self.rf)
        self.assertEqual(context['TEST'], 'my-very-own-test-value')
        self.assertIn('"test": "my-very-own-test-value"', context['settings'])

    def test_no_exposed_tenant_properties_setting(self):
        with mock.patch('tenant_extras.utils.get_tenant_properties') as get_tenant_properties, \
                mock.patch('django.conf.settings', spec={}) as settings:

            from ..context_processors import tenant_properties

            get_tenant_properties.return_value = {}

            context = tenant_properties(self.rf)
            self.assertEqual(context, {})


class TestDRFTenantPermission(TestCase):
    """
        Verify the permission that can enable/disable API access based on a
        tenant property
    """

    auth_user = mock.Mock(**{"user.is_authenticated.return_value": True})
    unauth_user = mock.Mock(**{"user.is_authenticated.return_value": False})

    def test_missing_setting(self):
        """ No tenant property at all - default to public """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = False

            self.failUnless(TenantConditionalOpenClose().has_permission(self.unauth_user, None))

    def test_api_open(self):
        """ There is a tenant property and it's open """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = False
            self.failUnless(TenantConditionalOpenClose().has_permission(self.unauth_user, None))

    def test_api_closed_unauth(self):
        """ There is a tenant property and it's closed, user is not authenticated """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = True

            self.failIf(TenantConditionalOpenClose().has_permission(self.unauth_user, None))

    def test_api_closed_auth(self):
        """ There is a tenant property and it's closed, user IS authenticated """
        with mock.patch('tenant_extras.drf_permissions.get_tenant_properties') as get_tenant_properties:
            get_tenant_properties.return_value = True

            self.failUnless(TenantConditionalOpenClose().has_permission(self.auth_user, None))


class TestGetTenantProperties(TestCase):
    @override_settings(TENANT_PROPERTIES="foobar.ponies.properties")
    def test_module_import(self):
        from tenant_extras.utils import get_tenant_properties

        with self.assertRaises(ImproperlyConfigured) as e:
            get_tenant_properties()

        self.assertEquals(str(e.exception), "Could not find module 'foobar.ponies'")

    @override_settings(TENANT_PROPERTIES="tenant_extras.tests.properties.properties3")
    def test_missing_properties(self):
        from tenant_extras.utils import get_tenant_properties

        with self.assertRaises(ImproperlyConfigured) as e:
            get_tenant_properties()

        self.assertEquals(str(e.exception),
                          "tenant_extras.tests.properties needs attribute name 'properties3'")

    @override_settings(TENANT_PROPERTIES="tenant_extras.tests.properties.properties2")
    def test_missing_property(self):
        from tenant_extras.utils import get_tenant_properties

        with self.assertRaises(ImproperlyConfigured) as e:
            get_tenant_properties('NOT_DEFINED')

        self.assertEquals(str(e.exception),
                          "Missing / undefined property 'NOT_DEFINED'")

    @override_settings(TENANT_PROPERTIES="tenant_extras.tests.properties.properties2")
    @mock.patch("tenant_extras.tests.properties.properties2")
    def test_property_found(self, props):
        from tenant_extras.utils import get_tenant_properties

        props.I_AM_DEFINED = 42
        self.assertEquals(get_tenant_properties('I_AM_DEFINED'), 42)

    @override_settings(TENANT_PROPERTIES="tenant_extras.tests.properties.properties2")
    @mock.patch("tenant_extras.tests.properties.properties2")
    def test_default(self, props):
        from tenant_extras.utils import get_tenant_properties

        self.assertEquals(get_tenant_properties(), props)
