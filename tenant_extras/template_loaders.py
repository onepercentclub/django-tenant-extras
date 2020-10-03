from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.loaders.filesystem import Loader
from django.utils._os import safe_join
from django.db import connection

from tenant_schemas.postgresql_backend.base import FakeTenant


class FilesystemLoader(Loader):
    """
    Based on FileSystemLoader from django-tenant-schemas:
    https://github.com/bernardopires/django-tenant-schemas/blob/master/tenant_schemas/template_loaders.py#L79
    Changes are:
    - Use MULTI_TENANT_DIR from config for path (not multiple paths in MULTITENANT_TEMPLATE_DIRS)
    - Use tenant.client_name not tenant.domain_url
    - Do not automatically include non-tenant filesystem template dirs
    """
    def get_dirs(self):
        if not connection.tenant or isinstance(connection.tenant, FakeTenant):
            return []

        try:
            template_dir = settings.MULTI_TENANT_DIR
        except AttributeError:
            raise ImproperlyConfigured('To use %s.%s you must define the MULTI_TENANT_DIR' %
                                       (__name__, FilesystemLoader.__name__))

        if '%' in template_dir:
            template_dir = safe_join(template_dir % connection.tenant.client_name, 'templates')
        else:
            template_dir = safe_join(template_dir, connection.tenant.client_name, 'templates')

        return [template_dir]
