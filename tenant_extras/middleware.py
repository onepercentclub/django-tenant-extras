"This is locale middleware on top of Django's default LocaleMiddleware."
import os
import sys
import copy

import gettext as gettext_module

from django import http
from django.conf import settings

from importlib import import_module
from django.middleware.locale import LocaleMiddleware
from django.utils.translation.trans_real import to_locale, DjangoTranslation
from django.utils import translation
from django.utils._os import upath

from .utils import get_tenant_properties

_tenants = {}


def _translation(path, loc, lang):
    try:
        t = gettext_module.translation('django', path, [loc],
                                       DjangoTranslation)
        # gettext will not give us a deep copy. This means _merge() will update
        # the original, global translation object.
        t = copy.deepcopy(t)
        t.set_language(lang)
        return t
    except IOError:
        return None


def tenant_translation(language, tenant_name, tenant_locale_path=None):
    """
    This is taken from the Django translation utils
    https://github.com/django/django/blob/1.6.8/django/utils/translation/trans_real.py#L101-L180

    It has been altered to handle tenant specific locale file paths.
    """

    global _tenants
    if tenant_name not in _tenants:
        _tenants[tenant_name] = {}

    _translations = _tenants[tenant_name]

    t = _translations.get(language, None)
    if t is not None:
        return t

    globalpath = os.path.join(os.path.dirname(upath(sys.modules[settings.__module__].__file__)), 'locale')

    def _fetch(lang, fallback=None):
        res = _translations.get(lang, None)
        if res is not None:
            return res

        loc = to_locale(lang)
        res = _translation(globalpath, loc, lang)

        # We want to ensure that, for example,  "en-gb" and "en-us" don't share
        # the same translation object (thus, merging en-us with a local update
        # doesn't affect en-gb), even though they will both use the core "en"
        # translation. So we have to subvert Python's internal gettext caching.
        base_lang = lambda x: x.split('-', 1)[0]
        if base_lang(lang) in [base_lang(trans) for trans in list(_translations)]:
            res._info = res._info.copy()
            res._catalog = res._catalog.copy()

        def _merge(path):
            t = _translation(path, loc, lang)
            if t is not None:
                if res is None:
                    return t
                else:
                    res.merge(t)
            return res

        for appname in reversed(settings.INSTALLED_APPS):
            app = import_module(appname)
            apppath = os.path.join(os.path.dirname(upath(app.__file__)), 'locale')

            if os.path.isdir(apppath):
                res = _merge(apppath)

        for localepath in reversed(settings.LOCALE_PATHS):
            if os.path.isdir(localepath):
                res = _merge(localepath)

        if tenant_locale_path:
            if os.path.isdir(tenant_locale_path):
                res = _merge(tenant_locale_path)

        if res is None:
            if fallback is not None:
                res = fallback
            else:
                return gettext_module.NullTranslations()
        _translations[lang] = res
        _tenants[tenant_name] = _translations

        return res

    default_translation = _fetch(getattr(get_tenant_properties(), 'LANGUAGE_CODE', None))
    current_translation = _fetch(language, fallback=default_translation)
    return current_translation


class TenantLocaleMiddleware(LocaleMiddleware):
    """
    NOTE:
    This class was severly stripped of logic because that has moved to nginx conf.
    It's main purpose is to redirect to

    """

    def process_response(self, request, response):
        """
        Redirect to default tenant language if none is set.
        """
        if response.status_code in [301, 302]:
            # No need to check for a locale redirect if the response is already a redirect.
            return response

        ignore_paths = getattr(settings, 'LOCALE_REDIRECT_IGNORE', None)

        supported_languages = dict(getattr(get_tenant_properties(), 'LANGUAGES')).keys()

        # Get language from path
        if self.is_language_prefix_patterns_used():
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
