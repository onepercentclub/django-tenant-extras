from django.conf import settings

class Mock1Properties():
    tenant_properties = {
        'RECURRING_DONATIONS_ENABLED': False,
        'DONATIONS_ENABLED': True,
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


properties1 = Mock1Properties()

class Mock2Properties():
    tenant_properties = {
        'RECURRING_DONATIONS_ENABLED': False,
        'DONATIONS_ENABLED': True,
        'LANGUAGE_CODE': "en",
        'TEST': "my-very-own-test-value",
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


properties2 = Mock2Properties()
