import os

from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.contrib.sites.models import Site
from django.utils import translation


def get_tenant_properties(property=None):
    """
    Returns a tenant property, or all if none specified.
    """

    properties_path = getattr(settings, 'TENANT_PROPERTIES')

    parts = properties_path.split('.')
    module = '.'.join([parts[i] for i in range(0,len(parts)-1)])
    properties = parts[len(parts) - 1]

    try:
        m = __import__(module, fromlist=[''])
    except ImportError:
        raise ImproperlyConfigured(
            "Could not find module '{0}'".format(module))

    try:
        props = getattr(m, properties)
    except AttributeError:
        raise ImproperlyConfigured(
            "{0} needs attribute name '{1}'".format(module, properties))

    try:
        if property:
            return getattr(props, property)
    except AttributeError:
        raise ImproperlyConfigured(
            "Missing / undefined property '{0}'".format(property))

    return props

class TenantLanguage():

    def __init__(self, language):
        self.language = language
        self.prev = translation.get_language()

    def __enter__(self):
        from .middleware import tenant_translation

        tenant_name = connection.tenant.client_name
        site_locale = os.path.join(settings.MULTI_TENANT_DIR, tenant_name, 'locale')
        tenant_name = connection.tenant.client_name

        translation._trans._active.value = tenant_translation(self.language, tenant_name, site_locale)

        return True

    def __exit__(self, type, value, traceback):
        translation.activate(self.prev)
