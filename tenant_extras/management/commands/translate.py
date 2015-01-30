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

    def __init__(self):
        self.option_list = self.option_list + (
            make_option('--tenant', dest='tenant', default=None, 
                    help="Generate translation messages for tenant."),
            make_option('--locale', '-l', dest='locale', action='append',
                    help='locale(s) to process (e.g. de_AT). Default is to process all. Can be used multiple times.'),
            make_option('--compile', '-c', dest='compile', action='store_true', default=False,
                    help='compile the .po to .mo files.'),
        )

        super(Command, self).__init__()

    def handle(self, *args, **options):
        default_ignore = ['*.orig', '.*', '.git', '*~', '*.pyc']
        default_ignore += ['tests', 'static', 'build', 'node_modules', 'bower_components', 'sass', 'static', 'private']

        self.verbosity = options.get('verbosity')
        self.compile = options.get('compile')
        self.locale = options.get('locale')
        if not self.locale:
            self.locale = ['en', 'en_GB', 'nl']

        # Find bb_location
        out = StringIO.StringIO()
        sys.stdout = out
        pip.main(['show', 'bluebottle'])
        sys.stdout = sys.__stdout__
        self.bb_location = os.path.join(re.search(r'^Location:\s(.*)$', out.getvalue(), re.MULTILINE).groups()[0], 'bluebottle')

        # find tenants
        tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)
        tenants = [f for f in os.listdir(tenant_dir) if os.path.isdir(os.path.join(tenant_dir, f))]

        if options.get('tenant'):
            tenant = options.get('tenant')

            ignore_patterns = default_ignore + [t for t in tenants if t != tenant]
            self._translate_tenant(tenant, ignore_patterns=ignore_patterns)

            self._handle_success(tenant)

        else:
            for tenant in tenants:
                ignore_patterns = default_ignore + [t for t in tenants if t != tenant]
                self._translate_tenant(tenant, ignore_patterns=ignore_patterns)

                self._handle_success(tenant)

    def _translate_tenant(self, tenant, ignore_patterns=None):
        # Generate translation file for django
        print 'Translating {}:\r\n> Making Django po files...'.format(tenant)

        # Create the locale directory for tenant if not present.
        tenant_locale_dir = os.path.join(getattr(settings, 'MULTI_TENANT_DIR', None), tenant, 'locale')
        if not os.path.isdir(tenant_locale_dir):
            os.mkdir(tenant_locale_dir)

        # Generate po file for tenant
        call_command('makepo',
            verbosity=self.verbosity,
            tenant=tenant,
            domain='django',
            all=True,
            no_wrap=True,
            no_obsolete=True,
            keep_pot=False,
            extensions=['html', 'py', 'hbs'],
            ignore_patterns=ignore_patterns,
            include_paths=[self.bb_location],
            locale=self.locale,)

        # Generate JS messages
        ignore_patterns = ignore_patterns + ['reef',]

        print '> Making JS po files...'
        call_command('makepo',
            verbosity=self.verbosity,
            tenant=tenant,
            domain='djangojs',
            all=True,
            no_wrap=True,
            no_obsolete=True,
            keep_pot=False,
            extensions=['js'],
            ignore_patterns=ignore_patterns,
            locale=self.locale,)

        if self.compile:
            # Compile .po files to .mo
            print '> Compiling po files...'
            call_command('compilepo',
                locale=self.locale,
                tenant=tenant)

    def _handle_success(self, tenant, **options):
        pass
