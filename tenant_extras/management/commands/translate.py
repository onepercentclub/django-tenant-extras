#-*- coding: utf-8 -*-
import os
import re
import sys
import subprocess
import StringIO

from optparse import make_option, OptionParser

import pip

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Scan i18n messages for per tenant translations."

    def add_arguments(self, parser):
        parser.add_argument('--tenant', dest='tenant', default=None,
                    help="Generate translation messages for tenant."),
        parser.add_argument('--locale', '-l', dest='locale', action='append',
                    help='locale(s) to process (e.g. de_AT). Default is to process all. Can be used multiple times.'),
        parser.add_argument('--compile', '-c', dest='compile', action='store_true', default=False,
                    help='compile the .po to .mo files.'),
        parser.add_argument('--pocmd', '-d', dest='pocmd', default='makepo',
                    help='alternative command to generate po files'),

    def handle(self, *args, **options):
        default_ignore = ['*.orig', '.*', '.git', '*~', '*.pyc', '*.egg', '*.egg-info']
        default_ignore += ['tests', 'static', 'build', 'node_modules', 'bower_components', 'sass', 'static', 'private', 'env', 'build', 'dist', 'frontend', 'tenants']

        self.verbosity = options.get('verbosity')
        self.compile = options.get('compile')
        self.locale = options.get('locale')
        self.pocmd = options.get('pocmd')

        if not self.locale:
            self.locale = ['en', 'en_GB', 'nl', 'fr']

        # find tenants
        tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)
        tenants = [f for f in os.listdir(tenant_dir) if os.path.isdir(os.path.join(tenant_dir, f))]

        # Generate translation file for django
        self.stdout.write('Translating:\r\n> Making Django po files...')

        # Ensure locale directories are created
        for locale in self.locale:
            locale_dir = os.path.join(settings.PROJECT_ROOT, 'locale', locale)
            if not os.path.exists(locale_dir):
                os.makedirs(locale_dir)

        # Generate po file for tenant
        call_command(self.pocmd,
                     verbosity=self.verbosity,
                     domain='django',
                     all=True,
                     no_wrap=True,
                     no_obsolete=True,
                     keep_pot=False,
                     extensions=['html', 'py', 'hbs', 'txt'],
                     ignore_patterns=default_ignore,
                     include_paths=['bluebottle'],
                     locale=self.locale)

        if options.get('tenant'):
            tenant = options.get('tenant')
            self._handle_success(tenant)

        else:
            for tenant in tenants:
                self._handle_success(tenant)

    def _handle_success(self, tenant, **options):
        pass
