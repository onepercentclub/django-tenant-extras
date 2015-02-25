from __future__ import with_statement

import io
import os
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.utils.translation import to_locale, activate
from django.utils.encoding import force_text
from django.db import connection

from django.conf import settings

import django
from django.views.i18n import get_javascript_catalog, render_javascript_catalog

from tenant_schemas.utils import get_public_schema_name, get_tenant_model


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--tenant', dest='tenant', default=None, 
                    help="Create gettext js for tenant."),
        make_option('--locale', '-l', dest='locale',
                    help="The locale to process. Default is to process all."),
        make_option('-d', '--domain',
                    dest='domain', default='djangojs',
                    help="Override the gettext domain. By default, "
                         " the command uses the djangojs gettext domain."),
        make_option('-p', '--packages', action='append', default=[],
                    dest='packages',
                    help="A list of packages to check for translations. "
                         "Default is 'django.conf'. Use multiple times to "
                         "add more."),
        make_option('-o', '--output', dest='outputdir', default='static/jsi18n', 
                    metavar='OUTPUT_DIR',
                    help="Output directory to store generated catalogs. "
                         "Defaults to static/jsi18n."),
    )
    help = "Collect Javascript catalog files in a single location."

    def handle_noargs(self, **options):
        self.locale = options.get('locale')
        self.domain = options['domain']
        self.packages = options['packages']
        self.outputdir = options['outputdir']
        self.tenant_name = options['tenant']
        self.verbosity = int(options.get('verbosity'))
        self.tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)


        self.stdout.write('Generating js files:')
        if self.tenant_name:
            self._render_catalog(self.tenant_name)
        else:
            for tenant_name in [f for f in os.listdir(self.tenant_dir) if os.path.isdir(os.path.join(self.tenant_dir, f))]:
                self._render_catalog(tenant_name)

    def _render_catalog(self, tenant_name):
        self.stdout.write('> for {}...'.format(tenant_name))

        if self.locale is not None:
            languages = [self.locale]
        else:
            languages = [to_locale(lang_code)
                         for (lang_code, lang_name) in settings.LANGUAGES]

        outputdir = os.path.join(getattr(settings, 'MULTI_TENANT_DIR', None), 
                                 tenant_name,
                                 self.outputdir)

        # Update the LOCALE_PATHS setting to ensure the Django get_javascript_catalog 
        # method below checks the correct directories. 
        settings.LOCALE_PATHS = (
            os.path.join(self.tenant_dir, tenant_name, 'locale'),
        )
            
        client_cls = get_tenant_model()

        try:
            tenant = client_cls.objects.get(client_name=tenant_name)

            for locale in languages:
                if self.verbosity > 0:
                    self.stdout.write("processing language %s\n" % locale)

                jsfile = os.path.join(outputdir, _default_filename(locale, self.domain))
                basedir = os.path.dirname(jsfile)
                if not os.path.isdir(basedir):
                    os.makedirs(basedir)

                connection.set_tenant(tenant)
                activate(locale)
                
                catalog, plural = get_javascript_catalog(locale, self.domain, self.packages)
                response = render_javascript_catalog(catalog, plural)

                with io.open(jsfile, "w", encoding="utf-8") as fp:
                    fp.write(force_text(response.content))

        except client_cls.DoesNotExist:
            self.stdout.write("Skipping unconfigured client: {0}".format(tenant_name))

def _default_filename(locale, domain):
    from django.utils.translation.trans_real import to_language
    return os.path.join(to_language(locale), '%s.js' % domain)
