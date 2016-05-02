"This is locale middleware on top of Django's default LocaleMiddleware."
import os
import sys
import re
import copy
import logging

import gettext as gettext_module

from django import http
from django.conf import settings
from django.core.urlresolvers import is_valid_path

from django.http import HttpResponseRedirect
from django.utils.importlib import import_module
from django.utils.cache import patch_vary_headers
from django.middleware.locale import LocaleMiddleware as _LocaleMiddleware
from django.utils.translation.trans_real import (
                            to_locale, DjangoTranslation, parse_accept_lang_header,
                            get_supported_language_variant)
from django.utils import translation
from django.utils.datastructures import SortedDict
from django.utils._os import upath
from django.db import connection

from .utils import get_tenant_properties

_tenants = {}

def _translation(path, loc, lang):
    try:
        t = gettext_module.translation('django', path, [loc], DjangoTranslation)
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


class TenantLocaleMiddleware(_LocaleMiddleware):

    def __init__(self):
        self.lang_code = None

    def _is_supported_language(self, language_code):
        """
        Returns True if language_code is supported by request tenant.
        """
        supported_languages = dict(getattr(get_tenant_properties(), 'LANGUAGES')).keys()
        try:
            lang_code = get_supported_language_variant(language_code, supported_languages)
            return True
        except LookupError:
            return False

    def _get_browser_language(self, request):
        """
        Return language based on browser accept setting. Only tenant supported languages
        will be matched.
        """
        browser_language_code = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        supported_languages = dict(getattr(get_tenant_properties(), 'LANGUAGES')).keys()

        for accept_lang, unused in parse_accept_lang_header(browser_language_code):
            if accept_lang == '*':
                break
            try:
                accept_lang = get_supported_language_variant(accept_lang, supported_languages)
            except LookupError:
                continue
            else:
                return accept_lang
        try:
            lang_code = getattr(get_tenant_properties(), 'LANGUAGE_CODE', None)
            return get_supported_language_variant(lang_code, supported_languages)
        except LookupError:
            return settings.LANGUAGE_CODE

    def _set_cookie(self, request, response):
        if self.lang_code != request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME):
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, self.lang_code)

    def process_request(self, request):
        tenant_name = connection.tenant.client_name
        site_locale = os.path.join(settings.MULTI_TENANT_DIR, tenant_name, 'locale')

        check_path = self.is_language_prefix_patterns_used()
        language = translation.get_language_from_request(
            request, check_path=check_path)
        translation._trans._active.value = tenant_translation(language, tenant_name, site_locale)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        """
        This builds strongly on django's Locale middleware, so check
        if it's enabled.

        This middleware is only relevant with i18n_patterns and the request
        is not to a 'docs', 'api' or 'go' endpoint.

        Options:
          Supported Language: respond without checking further
          User Authenticated:
            Unsupported Language or No Language (eg '/'):
              - redirect to cookie language
              - redirect to users primary language
              - redirect to default site language
          User Unauthenticated:
            Unsupported Language or No Language (eg '/'):
              - redirect to cookie language
              - redirect browser accepted language
              - redirect to default site language
        """

        if response.status_code in [301, 302]:
            # No need to check for a locale redirect if the response is already a redirect.
            return response

        ignore_paths = getattr(settings, 'LOCALE_REDIRECT_IGNORE', None)
        if not self.is_language_prefix_patterns_used() or (ignore_paths and request.path.startswith(ignore_paths)):
            return response

        _default_language = getattr(get_tenant_properties(), 'LANGUAGE_CODE', None)
        language_code_prefix_re = re.compile(r'^/(([a-z]{2})(-[A-Z]{2})?)(/|$)')
        regex_match = language_code_prefix_re.match(request.path)
        lang_code = ''

        if regex_match:
            current_url_lang_prefix = regex_match.group(2)
            try:
                # if the language requested is valid and supported then return early
                lang_code = get_supported_language_variant(current_url_lang_prefix)
                if self._is_supported_language(lang_code):
                  self.lang_code = lang_code
                  self._set_cookie(request, response)
                  return response
            except LookupError:
                pass
        else:
            current_url_lang_prefix = ''

        try:
            authenticated = request.user.is_authenticated()
        except AttributeError:
            authenticated = False

        lang_cookie = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

        if authenticated:
            # Options:
            # - redirect to cookie language
            # - redirect to users primary language
            primary_language = request.user.primary_language

            if lang_cookie:
                # use language in cookie if defined
                lang_code = lang_cookie

            elif self._is_supported_language(primary_language):
                lang_code = primary_language
        else:
            # Options:
            # - redirect to cookie language
            # - redirect browser accepted language
            browser_language = self._get_browser_language(request)

            if lang_cookie:
                # use language in cookie if defined
                lang_code = lang_cookie

            elif browser_language:
                lang_code = browser_language

        # Finally:
        # - set default site language if lang_code not already set
        if not lang_code:
            # fall back to site default
            lang_code = _default_language

        # Set the lang_code on the instance for use in the response / cookie
        self.lang_code = lang_code
        # If the lang_code is different to the current url prefix then redirect.
        if lang_code and lang_code != current_url_lang_prefix:
            if current_url_lang_prefix:
                # Replace current url language prefix
                expected_url_lang_prefix = '/{0}/'.format(lang_code)
                new_location = request.get_full_path().replace(
                    '/{0}/'.format(current_url_lang_prefix), expected_url_lang_prefix)
            else:
                new_location = '/{0}{1}'.format(lang_code, request.get_full_path())

            return http.HttpResponseRedirect(new_location)

        self._set_cookie(request, response)
        return super(TenantLocaleMiddleware, self).process_response(request, response)


    # re-use the original is_language_prefix_patterns_used function
    mw = _LocaleMiddleware()
    is_language_prefix_patterns_used = mw.is_language_prefix_patterns_used
