from django.conf import settings


class MockProperties():
    tenant_properties = {
        'LANGUAGE_CODE': "en",
        'LANGUAGES': (
            ('nl', 'Nederlands'),
            ('en', 'English'),
        )
    }

    def __getattr__(self, k):
        try:
            return self.tenant_properties[k]
        except (AttributeError, KeyError):
            # May raise AttributeError which is the behaviour we expect
            return getattr(settings, k)


properties = MockProperties()
