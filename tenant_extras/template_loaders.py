import hashlib
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.base import TemplateDoesNotExist
from django.template.loader import BaseLoader
from django.utils._os import safe_join
from django.db import connection

from tenant_schemas.postgresql_backend.base import FakeTenant
from tenant_schemas.template_loaders import CachedLoader as BaseCachedLoader


class CachedLoader(BaseCachedLoader):
    """
    This is a copy of the Tenant Schemas CachedLoader with load_template
    altered to handle a FakeTenant, eg the tenant not being set on the 
    connection due an error early in the server load process.
    """

    def load_template(self, template_name, template_dirs=None):
        if connection.tenant:
            try:
                key = '-'.join([str(connection.tenant.pk), template_name])
            except AttributeError:
                # Tenant not found so use standard key and template_dirs
                key = template_name
                if not template_dirs:
                    template_dirs = settings.TEMPLATE_DIRS
        else:
            key = template_name
        if template_dirs:
            # If template directories were specified, use a hash to
            # differentiate
            if connection.tenant:
                try:
                    key = '-'.join([str(connection.tenant.pk), template_name,
                                hashlib.sha1(force_bytes('|'.join(template_dirs))).hexdigest()])
                except AttributeError:
                    key = '-'.join([template_name, hashlib.sha1(force_bytes('|'.join(template_dirs))).hexdigest()])
            else:
                key = '-'.join([template_name, hashlib.sha1(force_bytes('|'.join(template_dirs))).hexdigest()])

        if key not in self.template_cache:
            template, origin = self.find_template(template_name, template_dirs)
            if not hasattr(template, 'render'):
                try:
                    template = get_template_from_string(template, origin, template_name)
                except TemplateDoesNotExist:
                    # If compiling the template we found raises TemplateDoesNotExist,
                    # back off to returning the source and display name for the template
                    # we were asked to load. This allows for correct identification (later)
                    # of the actual template that does not exist.
                    return template, origin
            self.template_cache[key] = template
        return self.template_cache[key], None


class FilesystemLoader(BaseLoader):
    """
    Based on FileSystemLoader from django-tenant-schemas:
    https://github.com/bernardopires/django-tenant-schemas/blob/master/tenant_schemas/template_loaders.py#L79
    Changes are:
    - Use MULTI_TENANT_DIR from config for path (not multiple paths in MULTITENANT_TEMPLATE_DIRS)
    - Use tenant.client_name not tenant.domain_url
    """

    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):
        if not connection.tenant:
            return

        # We can get here when the app errors before the tenant can
        # be set on the connection, eg on 400 errors due to DEBUG = False
        # and ALLOWED_HOSTS hasn't been correctly set.
        elif isinstance(connection.tenant, FakeTenant):
            if not template_dirs:
                template_dirs = settings.TEMPLATE_DIRS
            for template_dir in template_dirs:
                try:
                    yield safe_join(template_dir, template_name)
                except UnicodeDecodeError:
                    raise
                except ValueError:
                    pass
            return

        if not template_dirs:
            try:
                template_dirs = [settings.MULTI_TENANT_DIR]
            except AttributeError:
                raise ImproperlyConfigured('To use %s.%s you must define the MULTI_TENANT_DIR' %
                                           (__name__, FilesystemLoader.__name__))

        for template_dir in template_dirs:
            try:
                if '%s' in template_dir:
                    yield safe_join(template_dir % connection.tenant.client_name, 'templates', template_name)
                else:
                    yield safe_join(template_dir, connection.tenant.client_name, 'templates', template_name)
            except UnicodeDecodeError:
                # The template dir name was a bytestring that wasn't valid UTF-8.
                raise
            except ValueError:
                # The joined path was located outside of this particular
                # template_dir (it might be inside another one, so this isn't
                # fatal).
                pass

    def load_template_source(self, template_name, template_dirs=None):
        tried = []
        for filepath in self.get_template_sources(template_name, template_dirs):
            try:
                with open(filepath, 'rb') as fp:
                    return (fp.read().decode(settings.FILE_CHARSET), filepath)
            except IOError:
                tried.append(filepath)
        if tried:
            error_msg = "Tried %s" % tried
        else:
            error_msg = "Your TEMPLATE_DIRS setting is empty. Change it to point to at least one template directory."
        raise TemplateDoesNotExist(error_msg)
    load_template_source.is_usable = True
