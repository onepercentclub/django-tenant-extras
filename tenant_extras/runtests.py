#!/usr/bin/env python
import os
import sys

import coverage

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def runtests(args=None):
    test_dir = os.path.dirname(__file__)
    sys.path.insert(0, test_dir)

    import django
    from django.test.utils import get_runner
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            PROJECT_ROOT=os.path.abspath(test_dir),
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': os.path.join(BASE_DIR, 'db.sqlite3')
                }
            },
            INSTALLED_APPS=[
                'django.contrib.sites',
                'django_nose',
                'tenant_extras',
                'tenant_extras.tests'
            ],
            TENANT_PROPERTIES="tenant_extras.tests.properties.properties1",
            NOSE_ARGS=['--nocapture', '--nologcapture'],
            ROOT_URLCONF='tenant_extras.tests.urls'
        )

    django.setup()

    cov = coverage.Coverage()
    cov.start()

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True)
    args = args or ['.']
    failures = test_runner.run_tests(args)

    cov.stop()
    cov.save()
    if os.getenv('HTML_REPORT'):
        cov.html_report()

    sys.exit(failures)

if __name__ == '__main__':
    runtests(sys.argv[1:])
