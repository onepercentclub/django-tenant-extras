from django.core.cache.backends.memcached import PyMemcacheCache
from django.db import connection


class TenantAwareMemcachedCache(PyMemcacheCache):
    def make_key(self, key, version=None):
        if hasattr(connection, 'tenant'):
            key = '{}-{}'.format(connection.tenant.client_name, key)

        return super(TenantAwareMemcachedCache, self).make_key(key, version)
