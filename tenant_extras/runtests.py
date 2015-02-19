#!/usr/bin/env python
import sys, os

from django.conf import settings
from django.core.management import call_command

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

if not settings.configured:
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.path.join(BASE_DIR, 'db.sqlite3')}},
        INSTALLED_APPS=[
            'django_nose',
            'tenant_extras',
            'tenant_extras.tests'
        ],
        TENANT_PROPERTIES = "tenant_extras.tests.properties.properties",
        NOSE_ARGS = ['--nocapture', '--nologcapture',]
    )

from django_nose import NoseTestSuiteRunner

def runtests(*test_labels):
    runner = NoseTestSuiteRunner(verbosity=1, interactive=True)
    failures = runner.run_tests(test_labels)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])