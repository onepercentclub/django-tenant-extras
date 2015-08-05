from django.core.cache.backends.memcached import MemcachedCache
from django.db import connection


class TenantAwareMemcachedCache(MemcachedCache):
    def make_key(self, key, version=None):
        if hasattr(connection, 'tenant'):
            key = '{}-{}'.format(connection.tenant.client_name, key)

        return super(TenantAwareMemcachedCache, self).make_key(key, version)
