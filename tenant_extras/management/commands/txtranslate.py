#-*- coding: utf-8 -*-

import os
import re
import sys
import subprocess
import StringIO

from optparse import make_option, OptionParser

from django.conf import settings
from .translate import Command as BaseCommand


class Command(BaseCommand):
    help = "Tenant translations with optional Transifex push."

    def add_arguments(self, parser):
        parser.add_argument('--push', '-p', dest='push', action='store_true',
                            default=False, help='Push translations to Transifex.'),

    def handle(self, *args, **options):
        self.push = options.get('push')

        super(Command, self).handle(*args, **options)

    def _handle_success(self, tenant, **options):
        if self.push:
            from txclib.project import Project

            self.stdout.write('> Pushing translations for {}...'.format(tenant))
            tenant_dir = os.path.join(getattr(settings, 'MULTI_TENANT_DIR', None), tenant)
            project = Project(path_to_tx=tenant_dir)
            project.push(source=True, no_interactive=True)
