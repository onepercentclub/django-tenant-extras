from django.utils._os import safe_join
import os

from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict
from django.conf import settings

from django.contrib.staticfiles.finders import FileSystemFinder
from django.core.files.storage import FileSystemStorage
from django.contrib.staticfiles import utils

from django_tenants.utils import get_tenant_model


class TenantStaticFilesFinder(FileSystemFinder):

    def __init__(self, apps=None, *args, **kwargs):
        # List of locations with static files
        self.locations = []
        
        # Maps dir paths to an appropriate storage instance
        self.storages = SortedDict()

        if not isinstance(settings.MULTI_TENANT_DIR, str):
            raise ImproperlyConfigured(
                "You need to set the MULTI_TENANT_DIR setting")

        tenant_dir = settings.MULTI_TENANT_DIR
        for tenant_name in [f for f in os.listdir(tenant_dir) if os.path.isdir(os.path.join(tenant_dir, f))]:
            tenant_static_dir = os.path.join(getattr(settings, 'MULTI_TENANT_DIR', None), 
                                        tenant_name,
                                        'static')
            self.locations.append((tenant_name, tenant_static_dir))

        for prefix, root in self.locations:
            filesystem_storage = FileSystemStorage(location=root)
            filesystem_storage.prefix = prefix
            self.storages[root] = filesystem_storage

        super(FileSystemFinder, self).__init__(*args, **kwargs)

    def find(self, path, all=False):
        """
        Looks for files in the client static directories.
        static/assets/greatbarier/images/logo.jpg
        will translate to
        MULTI_TENANT_DIR/greatbarier/static/images/logo.jpg

        """
        tenants = get_tenant_model().objects.all()
        tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)

        if not tenant_dir:
            return []

        for tenant in tenants:
            if "{0}/".format(tenant.client_name) in path:
                tenant_path = path.replace('{0}/'.format(tenant.client_name),
                                           '{0}/static/'.format(tenant.client_name))
                local_path = safe_join(tenant_dir, tenant_path)
                if os.path.exists(local_path):
                    if all:
                        return [local_path]
                    return local_path
        return []
