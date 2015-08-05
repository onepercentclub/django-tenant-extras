from django.test import TestCase
import mock
from ..cache import TenantAwareMemcachedCache


class TestCacheBackend(TestCase):
    def setUp(self):
        self.cache = TenantAwareMemcachedCache('localhost', {})

    def test_tenant(self):
        with mock.patch("tenant_extras.cache.connection") as c:
            c.tenant = mock.Mock(client_name="tenant_a")
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
