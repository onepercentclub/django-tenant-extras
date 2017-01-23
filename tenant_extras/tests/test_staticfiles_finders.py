import os
from django.test import TestCase
from django.test.utils import override_settings
import mock
from tenant_extras.staticfiles_finders import TenantStaticFilesFinder
import tenant_schemas.utils
from tenant_schemas.utils import get_tenant_model


class MockTenant(object):
    def __init__(self, client_name):
        self.client_name = client_name


class MockTenants(object):
    class objects(object):
        @classmethod
        def all(cls):
            return [MockTenant('tenant1'), MockTenant('tenant2')]


@override_settings(
    MULTI_TENANT_DIR=os.path.join(os.path.dirname(__file__), 'tenants'),
    TENANT_MODEL='app.Tenant'
)
class TestStaticFilesFinder(TestCase):
    def setUp(self):
        self.finder = TenantStaticFilesFinder()

    def test_find(self):
        with mock.patch.object(tenant_schemas.utils, 'get_tenant_model', return_value=MockTenants):
            result = self.finder.find('tenant1/test.txt')

        self.assertTrue(result)

    def test_find_nonexistant(self):
        with mock.patch.object(tenant_schemas.utils, 'get_tenant_model', return_value=MockTenants):
            result = self.finder.find('tenant1/does-not-exist.txt')

        self.assertFalse(result)
