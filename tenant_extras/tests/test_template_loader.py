import os

from django.conf import settings
from django.db import connection
from django.template.loader import get_template

from django.test import SimpleTestCase, override_settings

from munch import munchify

@override_settings(
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.dummy.TemplateStrings',
        'APP_DIRS': True,
    }, {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
            'loaders': [
                'tenant_extras.template_loaders.FilesystemLoader',
            ]
        },
    }],
    MULTI_TENANT_DIR=os.path.join(settings.PROJECT_ROOT, 'tests', 'tenants'),
)
class TemplateLoaderTests(SimpleTestCase):

    def setUp(self):
        self.tenant1 = munchify({
            'name': 'My Test',
            'client_name': 'tenant1'
        })

        self.tenant2 = munchify({
            'name': 'My Test',
            'client_name': 'tenant2'
        })

    def test_get_template(self):
        connection.tenant = self.tenant1
        template = get_template('template_loader/hello.html')
        self.assertEqual(template.render(), 'Hello from tenant1\n')
