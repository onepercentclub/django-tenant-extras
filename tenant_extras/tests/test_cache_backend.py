from django.test.testcases import SimpleTestCase
import mock
from ..cache import TenantAwareMemcachedCache
from django.db import connection

class TestCacheBackend(SimpleTestCase):
    def setUp(self):
        self.cache = TenantAwareMemcachedCache('localhost', {})

    def test_tenant(self):
        connection.tenant = mock.Mock(client_name='tenant_a')
        self.assertTrue(
            'tenant_a' in self.cache.make_key('test')
        )
        self.assertTrue(
            'test' in self.cache.make_key('test')
        )

    def test_no_tenant(self):
        """ make sure everything works if there is no tenant """
        self.assertTrue(
            'test' in self.cache.make_key('test')
        )
