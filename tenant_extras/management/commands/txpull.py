import os
import re
import shutil
import sys
import subprocess
import StringIO
import contextlib

from optparse import make_option, OptionParser

from django.conf import settings
from django.core.management.base import CommandError

from txclib.project import Project

from .base import Command as BaseCommand


@contextlib.contextmanager
def temp_chdir(path):
    starting_directory = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(starting_directory) 


class Command(BaseCommand):
    help = "Pull tenant translations from Transifex."

    options = BaseCommand.options + (
        make_option('--all', '-a', action='store_true', dest='all',
            default=False, help='Pull translation messages for all tenants.'),
        make_option('--tenant', '-t', dest='tenant', default=None,
            help='Pull translation messages for tenant.'),
        make_option('--deploy', '-d', dest='deploy', default=False, action='store_true',
            help='Deploy will rename the \'en_GB\' locale to \'en\'.'),
        make_option('--frontend', '-f', dest='frontend', default=False, action='store_true',
            help='Pull translations to frontend directory.'),
        make_option('--frontend-dir', '-e', dest='frontend_dir', default='frontend/lib',
            help='Pull translations to frontend directory.'),
    )

    def handle(self, *args, **options):
        process_all = options.get('all')
        tenant = options.get('tenant')
        deploy = options.get('deploy')
        frontend = options.get('frontend')
        frontend_dir = options.get('frontend_dir')

        if tenant is not None and process_all:
            raise CommandError("The --tenant option can't be used for --all.")

        if tenant is None and not process_all:
            raise CommandError("Type '%s help %s' for usage information." % (
                                os.path.basename(sys.argv[0]), sys.argv[1]))

        if process_all:
            # Even if we are pulling translations for the frontend we 
            # still use the backend MULTI_TENANT_DIR to work out 
            # the list of tenants as this dir will only contain
            # tenant names.
            tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)
            for tenant in [f for f in os.listdir(tenant_dir) if os.path.isdir(os.path.join(tenant_dir, f))]:
                self._pull(tenant, frontend, frontend_dir, deploy)
        else:
            self._pull(tenant, frontend, frontend_dir, deploy)

    def _pull(self, tenant, frontend, frontend_dir, deploy):
        self.stdout.write('> Pulling translations for {}...'.format(tenant))

        if (frontend and frontend_dir):
            tenant_dir = os.path.join(settings.PROJECT_ROOT, frontend_dir, tenant)
        else:
            tenant_dir = os.path.join(getattr(settings, 'MULTI_TENANT_DIR', None), tenant)

        with temp_chdir(tenant_dir):            
            # Pull latest translations from Transifex
            project = Project(tenant_dir)
            project.pull(fetchsource=False, force=True, overwrite=True, fetchall=True)

            # Move en_GB to en
            if deploy:
                self.stdout.write('--> Move en_GB to en directory for {}...'.format(tenant))
                if os.path.isdir('locale/en'):
                    shutil.rmtree('locale/en')
                os.rename('locale/en_GB', 'locale/en')