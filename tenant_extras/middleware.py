"This is locale middleware on top of Django's default LocaleMiddleware."
import os

from django import http
from django.conf import settings
from django.conf.urls.i18n import is_language_prefix_patterns_used
from django.db import connection

from django.middleware.locale import LocaleMiddleware
from django.utils.translation.trans_real import DjangoTranslation as DjangoTranslationOriginal
from django.utils import translation

from .utils import get_tenant_properties

_tenants = {}
_translations = {}


class DjangoTranslation(DjangoTranslationOriginal):
    """
    This class sets up the GNUTranslations context with regard to output
    charset.

    This translation object will be constructed out of multiple GNUTranslations
    objects by merging their catalogs. It will construct an object for the
    requested language and add a fallback to the default language, if it's
    different from the requested language.
    """
    def __init__(self, language, tenant_name):
        self.tenant_name = tenant_name
        DjangoTranslationOriginal.__init__(self, language)

    def _add_local_translations(self):
        """Merges translations defined for tenant and standard locale."""
        locale_paths = [os.path.join(settings.MULTI_TENANT_DIR, self.tenant_name, 'locale')]
        locale_paths.extend(settings.LOCALE_PATHS)

        for localedir in reversed(locale_paths):
            translation = self._new_gnu_trans(localedir)
            self.merge(translation)

    def _add_fallback(self, localdirs):
        """Sets the GNUTranslations() fallback with the default language."""
        # Don't set a fallback for the default language or any English variant
        # (as it's empty, so it'll ALWAYS fall back to the default language)
        lang_code = getattr(get_tenant_properties(), 'LANGUAGE_CODE', None)
        if self.__language == lang_code or self.__language.startswith('en'):
            return
        default_translation = tenant_translation(lang_code, self.tenant_name)
        self.add_fallback(default_translation)


def tenant_translation(language, tenant_name):
    """
    Returns a translation object for the given tenant name and language.
    """
    global _tenants
    if tenant_name not in _tenants:
        _tenants[tenant_name] = {}

    _translations = _tenants[tenant_name]

    t = _translations.get(language, None)
    if t is None:
        t = DjangoTranslation(language, tenant_name)
        _translations[language] = t

    return t


class TenantLocaleMiddleware(LocaleMiddleware):
    """
    NOTE:
    This class was severly stripped of logic because that has moved to nginx conf.
    It's main purpose is to redirect to

    """
    def process_request(self, request):
        tenant_name = connection.tenant.client_name
        site_locale = os.path.join(settings.MULTI_TENANT_DIR, tenant_name, 'locale')

        urlconf = getattr(request, 'urlconf', settings.ROOT_URLCONF)
        check_path = is_language_prefix_patterns_used(urlconf)
        language = translation.get_language_from_request(
            request, check_path=check_path)
        translation._trans._active.value = tenant_translation(language, tenant_name)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        """
        Redirect to default tenant language if none is set.
        """
        if response.status_code in [301, 302]:
            # No need to check for a locale redirect if the response is already a redirect.
            return response

        ignore_paths = getattr(settings, 'LOCALE_REDIRECT_IGNORE', None)

        # Get language from path
        urlconf = getattr(request, 'urlconf', settings.ROOT_URLCONF)
        if is_language_prefix_patterns_used(urlconf):
            language_from_path = translation.get_language_from_path(
                request.path_info
            )
            # If ignore paths or language set, then just pass the response
            if language_from_path or (ignore_paths and request.path.startswith(ignore_paths)):
                return response

        # Redirect to default tenant language
        lang_code = getattr(get_tenant_properties(), 'LANGUAGE_CODE', None)
        new_location = '/{0}{1}'.format(lang_code, request.get_full_path())

        return http.HttpResponseRedirect(new_location)
