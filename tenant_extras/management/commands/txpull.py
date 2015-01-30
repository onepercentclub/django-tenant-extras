import os
import re
import sys
import subprocess
import StringIO
import contextlib

from optparse import make_option, OptionParser

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from txclib.project import Project


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

    def __init__(self):
        self.option_list = self.option_list + (
            make_option('--all', '-a', action='store_true', dest='all',
                default=False, help='Pull translation messages for all tenants.'),
            make_option('--tenant', '-t', dest='tenant', default=None,
                help='Pull translation messages for tenant.'),
        )

        super(Command, self).__init__()

    def handle(self, *args, **options):
        process_all = options.get('all')
        tenant = options.get('tenant')

        if tenant is not None and process_all:
            raise CommandError("The --tenant option can't be used for --all.")

        if tenant is None and not process_all:
            raise CommandError("Type '%s help %s' for usage information." % (
                                os.path.basename(sys.argv[0]), sys.argv[1]))

        if process_all:
            tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)
            for tenant in [f for f in os.listdir(tenant_dir) if os.path.isdir(os.path.join(tenant_dir, f))]:
                self._pull(tenant)
        else:
            self._pull(tenant)

    def _pull(self, tenant):
        print '> Pulling translations for {}...'.format(tenant)

        tenant_dir = os.path.join(getattr(settings, 'MULTI_TENANT_DIR', None), tenant)
        with temp_chdir(tenant_dir):            
            # Pull latest translations from Transifex
            project = Project(tenant_dir)
            project.pull(fetchsource=False, force=True, overwrite=True, fetchall=True)
