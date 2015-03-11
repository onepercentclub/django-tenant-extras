import fnmatch
import glob
import os
import sys
import re
from optparse import make_option

import django
from django.core.management.base import CommandError
from django.core.management.utils import handle_extensions

from django.utils.text import get_text_list
from django.core.management.commands.makemessages import (TranslatableFile, Command as BaseCommand, check_programs)


class Command(BaseCommand):

    def __init__(self):
        self.option_list = self.option_list + (
            make_option('--tenant', dest='tenant', default=None, 
                help="Create pot for tenant."),
            make_option('--include', action='append', dest='include_paths', default=[], 
                help="Include additional paths."),
        )

        super(Command, self).__init__()

    def handle_noargs(self, *args, **options):
        """
        Function taken from the standard handler in Django with
        some extras added for handling multiple tenants.

        https://github.com/django/django/blob/1.6.8/django/core/management/commands/makemessages.py
        """

        locale = options.get('locale')
        self.domain = options.get('domain')
        self.verbosity = int(options.get('verbosity'))
        process_all = options.get('all')
        extensions = options.get('extensions')
        self.symlinks = options.get('symlinks')
        ignore_patterns = options.get('ignore_patterns')
        if options.get('use_default_ignore_patterns'):
            ignore_patterns += ['CVS', '.*', '*~', '*.pyc']
        self.ignore_patterns = list(set(ignore_patterns))
        self.wrap = '--no-wrap' if options.get('no_wrap') else ''
        self.location = '--no-location' if options.get('no_location') else ''
        self.no_obsolete = options.get('no_obsolete')
        self.keep_pot = options.get('keep_pot')
        self.tenant = options.get('tenant')

        if self.domain not in ('django', 'djangojs'):
            raise CommandError("currently makemessages only supports domains "
                               "'django' and 'djangojs'")
        if self.domain == 'djangojs':
            exts = extensions if extensions else ['js']
        else:
            exts = extensions if extensions else ['html', 'txt']
        self.extensions = handle_extensions(exts)

        if (locale is None and not process_all) or self.domain is None:
            raise CommandError("Type '%s help %s' for usage information." % (
                                os.path.basename(sys.argv[0]), sys.argv[1]))

        if self.verbosity > 1:
            self.stdout.write('examining files with the extensions: %s\n'
                             % get_text_list(list(self.extensions), 'and'))

        # Need to ensure that the i18n framework is enabled
        from django.conf import settings
        if settings.configured:
            settings.USE_I18N = True
        else:
            settings.configure(USE_I18N = True)

        self.invoked_for_django = False
        tenant_dir = getattr(settings, 'MULTI_TENANT_DIR', None)

        ###
        # Added check here to handle tenant specific translations
        if self.tenant and tenant_dir and os.path.isdir(os.path.join(tenant_dir, self.tenant, 'locale')):
            localedir = os.path.abspath(os.path.join(tenant_dir, self.tenant, 'locale'))
        elif os.path.isdir(os.path.join('conf', 'locale')):
            localedir = os.path.abspath(os.path.join('conf', 'locale'))
            self.invoked_for_django = True
            # Ignoring all contrib apps
            self.ignore_patterns += ['contrib/*']
        elif os.path.isdir('locale'):
            localedir = os.path.abspath('locale')
        else:
            raise CommandError("This script should be run from the Django Git "
                    "tree or your project or app tree. If you did indeed run it "
                    "from the Git checkout or your project or application, "
                    "maybe you are just missing the conf/locale (in the django "
                    "tree) or locale (for project and application) directory? It "
                    "is not created automatically, you have to create it by hand "
                    "if you want to enable i18n for your project or application.")

        check_programs('xgettext')

        potfile = self.build_pot_file(localedir, include_paths=options.get('include_paths'))

        # Build po files for each selected locale
        locales = []
        if locale is not None:
            locales = locale
        elif process_all:
            locale_dirs = filter(os.path.isdir, glob.glob('%s/*' % localedir))
            locales = [os.path.basename(l) for l in locale_dirs]

        if locales:
            check_programs('msguniq', 'msgmerge', 'msgattrib')

        try:
            for locale in locales:
                if self.verbosity > 0:
                    self.stdout.write("processing locale %s\n" % locale)
                self.write_po_file(potfile, locale)
        finally:
            if not self.keep_pot and os.path.exists(potfile):
                os.unlink(potfile)

    def build_pot_file(self, localedir, include_paths=None):
        """
        Standard build_pot_file updated to handle multiple include paths for
        generating tenant specific translations.
        """
        paths = ["."]
        if include_paths is not None:
            paths += include_paths

        file_list = self.find_files(paths)

        potfile = os.path.join(localedir, '%s.pot' % str(self.domain))
        if os.path.exists(potfile):
            # Remove a previous undeleted potfile, if any
            os.unlink(potfile)

        for f in file_list:
            try:
                f.process(self, potfile, self.domain, self.keep_pot)
            except UnicodeDecodeError:
                self.stdout.write("UnicodeDecodeError: skipped file %s in %s" % (f.file, f.dirpath))

        msgs, message = self._additional_msgs()
        if msgs:
            # If the new message doesn't exist in the pot file then it should
            # be appended to the end.
            with open(potfile, "r") as pot_file:
                lines = pot_file.read()

            with open(potfile, "a") as pot_file:
                # lines = pot_file.read()
                for msg in msgs:
                    expr = re.compile(u"msgid \"{}\"".format(msg), re.M)
                    if not expr.findall(lines):
                        if not message:
                            message = "Additional translation message"
                        # pot_file.write('asdasd')
                        pot_file.write(u"\n\n#: {0}\n\nmsgid \"{1}\"\n\nmsgstr \"\"".format(message, msg).encode('utf-8'))

        return potfile

    def find_files(self, paths):
        """
        Helper method to get all files in the given paths.
        """

        def is_ignored(path, ignore_patterns):
            """
            Check if the given path should be ignored or not.
            """
            filename = os.path.basename(path)
            ignore = lambda pattern: fnmatch.fnmatchcase(filename, pattern)
            return any(ignore(pattern) for pattern in ignore_patterns)

        dir_suffix = '%s*' % os.sep
        norm_patterns = [p[:-len(dir_suffix)] if p.endswith(dir_suffix) else p for p in self.ignore_patterns]
        all_files = []

        ###
        # Added check here to handle tenant specific translations
        for path in paths:
            for dirpath, dirnames, filenames in os.walk(path, topdown=True, followlinks=self.symlinks):
                for dirname in dirnames[:]:
                    if is_ignored(os.path.normpath(os.path.join(dirpath, dirname)), norm_patterns):
                        dirnames.remove(dirname)
                        if self.verbosity > 1:
                            self.stdout.write('ignoring directory %s\n' % dirname)
                for filename in filenames:
                    if is_ignored(os.path.normpath(os.path.join(dirpath, filename)), self.ignore_patterns):
                        if self.verbosity > 1:
                            self.stdout.write('ignoring file %s in %s\n' % (filename, dirpath))
                    else:
                        all_files.append(TranslatableFile(dirpath, filename))
        return sorted(all_files)

    # Additional data to be appended to pot file.
    # This can include strings from the database.
    def _additional_msgs(self):
        return (), "Nothing to see here."
