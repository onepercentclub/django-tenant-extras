import os

from django.utils.datastructures import SortedDict
from django.contrib.staticfiles import finders, storage
from django.conf import settings
from django.db import connection

from django.contrib.staticfiles.management.commands.collectstatic import (Command as BaseCommand)

from tenant_extras.staticfiles_finders import TenantStaticFilesFinder
from tenant_schemas.utils import get_public_schema_name, get_tenant_model


class Command(BaseCommand):

    def collect(self):
         
        results = super(Command, self).collect()

        if self.symlink:
            handler = self.link_file
        else:
            handler = self.copy_file

        # Now check for static assets for each client.
        # If the asset is located in:
        #  - clients/gent/assets/images..
        # then the asset will be collected to 
        #  - static/assets/gent/images
        found_files = SortedDict()

        # TenantStaticFilesFinder
        tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)

        for finder in finders.get_finders():
            if isinstance(finder, TenantStaticFilesFinder):
                for path, storage in finder.list(self.ignore_patterns):
                    # Prefix the relative path if the source storage contains it
                    if getattr(storage, 'prefix', None):
                        prefixed_path = os.path.join(storage.prefix, path)
                    else:
                        prefixed_path = path

                    if prefixed_path not in found_files:
                        found_files[prefixed_path] = (storage, path)
                        handler(path, prefixed_path, storage)

        return {
            'modified': self.copied_files + self.symlinked_files,
            'unmodified': self.unmodified_files,
            'post_processed': self.post_processed_files,
        }
