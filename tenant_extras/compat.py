try:
    from django.conf.urls.i18n import is_language_prefix_patterns_used
except ImportError:
    from django.middleware.locale import LocaleMiddleware

    def is_language_prefix_patterns_used(urlconf):
        LocaleMiddleware().is_language_prefix_patterns_used
