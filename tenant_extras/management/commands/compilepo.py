from __future__ import unicode_literals

import codecs
import os
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import find_command, popen_wrapper


class Command(BaseCommand):
    """
    Command taken from the standard compilemessages in Django with
    some extras added for handling multiple tenants.

    https://github.com/django/django/blob/1.6.8/django/core/management/commands/compilemessages.py
    """
    help = 'Compiles .po files to .mo files for use with builtin gettext support.'

    requires_model_validation = False
    leave_locale_alone = True

    def add_arguments(self, parser):
        parser.add_argument('--locale', '-l', dest='locale', action='append',
                            help='locale(s) to process (e.g. de_AT). Default is to process all. Can be used multiple times.'),
        parser.add_argument('--tenant', dest='tenant', default=None,
                            help="Compile .po files for tenant."),

    def handle(self, **options):
        locale = options.get('locale')
        tenant = options.get('tenant')
        compile_messages(self.stdout, locale=locale, tenant=tenant)


def compile_messages(stdout, locale=None, tenant=None):
    """
    Standard compile_messages updated to handle compiling po files for
    multiple tenants if MULTI_TENANT_DIR settings defined.
    """
    program = 'msgfmt'
    if find_command(program) is None:
        raise CommandError("Can't find %s. Make sure you have GNU gettext tools 0.15 or newer installed." % program)

    basedirs = [os.path.join('conf', 'locale'), 'locale']
    if os.environ.get('DJANGO_SETTINGS_MODULE'):
        from django.conf import settings
        basedirs.extend(settings.LOCALE_PATHS)

    # Check for tenant translations
    tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)
    if tenant and os.path.isdir(os.path.join(tenant_dir, tenant)):
        basedirs += [os.path.join(tenant_dir, tenant, 'locale')]
    else:
        # Compile all tenants
        basedirs += [os.path.join(tenant_dir, d) for d in os.listdir(tenant_dir) if os.path.isdir(os.path.join(tenant_dir, d))]

    # Gather existing directories.
    basedirs = set(map(os.path.abspath, filter(os.path.isdir, basedirs)))

    if not basedirs:
        raise CommandError("This script should be run from the Django Git checkout or your project or app tree, or with the settings module specified.")

    for basedir in basedirs:
        _compile(stdout, locale, basedir, program)


def _compile(stdout, locale, basedir, program):
    if locale:
        dirs = [os.path.join(basedir, l, 'LC_MESSAGES') for l in locale]
    else:
        dirs = [basedir]
    for ldir in dirs:
        for dirpath, dirnames, filenames in os.walk(ldir):
            for f in filenames:
                if not f.endswith('.po'):
                    continue
                stdout.write('processing file %s in %s\n' % (f, dirpath))
                fn = os.path.join(dirpath, f)
                pf = os.path.splitext(fn)[0]
                args = [program, '--check-format', '-o', pf + '.mo', pf + '.po']
                output, errors, status = popen_wrapper(args)
                if status:
                    if errors:
                        msg = "Execution of %s failed: %s" % (program, errors)
                    else:
                        msg = "Execution of %s failed" % program
                    raise CommandError(msg)
