import os

from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.contrib.sites.models import Site
from django.utils import translation


def get_tenant_properties(model_name=None):
    """
    Returns a model class
    model_name: The model eg 'User' or 'Project'
    """

    properties_path = getattr(settings, 'TENANT_PROPERTIES')

    parts = properties_path.split('.')
    module = '.'.join([parts[i] for i in range(0,len(parts)-1)])
    properties = parts[len(parts) - 1]

    try:
        m = __import__(module, fromlist=[''])
    except ImportError:
        raise ImproperlyConfigured(
            "Could not find module '{1}'".format(module))

    try:
        return getattr(m, properties)
    except AttributeError:
        raise ImproperlyConfigured(
            "{0} needs attribute name '{1}'".format(module, properties))


def update_tenant_site(tenant, name, domain):
    """
        switch to the client's schema and update the primary
        site object
    """
    connection.set_tenant(tenant)
    site, _ = Site.objects.get_or_create(pk=1)
    site.name = name
    site.domain = domain
    site.save()
    connection.set_schema_to_public()


@contextmanager
def tenant_language(language):
    """Context manager that changes the current translation language for
    all code inside the following block to the correct tenant specific language
    """
    from .middleware import tenant_translation

    if language:
        prev = translation.get_language()

        site_locale = os.path.join(settings.MULTI_TENANT_DIR, tenant_name, 'locale')
        tenant_name = connection.tenant.client_name
        translation._trans._active.value = tenant_translation(language, tenant_name, site_locale)

        try:
            yield
        finally:
            translation.activate(prev)
    else:
        yield