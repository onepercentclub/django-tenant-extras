"This is locale middleware on top of Django's default LocaleMiddleware."
import os
import sys

import gettext as gettext_module

from django import http
from django.conf import settings
from django.utils.importlib import import_module
from django.middleware.locale import LocaleMiddleware as _LocaleMiddleware
from django.utils.translation.trans_real import to_locale, DjangoTranslation
from django.utils import translation
from django.utils.datastructures import SortedDict
from django.utils._os import upath
from django.core.urlresolvers import LocaleRegexURLResolver, get_resolver

from django.db import connection

from .utils import get_tenant_properties

_tenants = {}

def _translation(path, loc, lang):
    try:
        t = gettext_module.translation('django', path, [loc], DjangoTranslation)
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
    _translations = _tenants.get(tenant_name, {})

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
        return res

    default_translation = _fetch(getattr(get_tenant_properties(), 'LANGUAGE_CODE', None))
    current_translation = _fetch(language, fallback=default_translation)

    return current_translation


class TenantLocaleMiddleware(_LocaleMiddleware):

    def process_request(self, request):
        tenant_name = connection.tenant.client_name 
        site_locale = os.path.join(settings.MULTI_TENANT_DIR, tenant_name, 'locale')

        check_path = self.is_language_prefix_patterns_used()
        language = translation.get_language_from_request(
            request, check_path=check_path)
        translation._trans._active.value = tenant_translation(language, tenant_name, site_locale)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        response = super(TenantLocaleMiddleware, self).process_response(request, response)

        """ Store the language in the session """
        lang_code = translation.get_language()

        if hasattr(request, 'session'):
            """ Set the language in the session if it has changed """
            if (request.session.get('django_language', False) and 
                    request.session['django_language'] != lang_code):
                request.session['django_language'] = lang_code
        else:
            """ Fall back to language cookie """
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
            
        response['Content-Language'] = translation.get_language()
        translation.deactivate()
        
        return response


class LocaleRedirectMiddleware(object):
    """
    If i18n_patterns are used, the language is not set in the session.
    This causes the middleware to potentially set an incorrect language on the
    current request when the frontend language differs from the browser language.

    This middleware fixes this in two ways:
        * first, a check is performed if the user is logged in. The preferred
          language is taken from his/her preferences.

        TODO: set the language in session for anonymous users.

        TODO: another workaround: when users (logged in or anonymous) select the
        language, is firing an API call which eventually calls Django's
        set_language view. This forces the language into the session.
    """

    def process_request(self, request):
        """ 
        This builds strongly on django's Locale middleware, so check 
        if it's enabled.

        This middleware is only relevant with i18n_patterns.
        """
        _supported_languages = SortedDict(getattr(get_tenant_properties(), 'LANGUAGES'))
        _default_language = getattr(get_tenant_properties(), 'LANGUAGE_CODE', None)

        url_parts = request.path.split('/')
        current_url_lang_prefix = url_parts[1]

        valid_prefixes = dict(_supported_languages).keys() + ['', 'admin',]
        if not current_url_lang_prefix in valid_prefixes: return

        try:
            authenticated = request.user.is_authenticated()
        except AttributeError:
            authenticated = False

        if authenticated:
            lang_code = request.user.primary_language
        else:
            if hasattr(request, 'session'):
                # Redirect to the language in the session if it is different
                lang_code = request.session['django_language']

            else:
                # Fall back to language cookie
                lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

        # If language code not supported then clear the value.
        if not lang_code in dict(_supported_languages).keys():
            lang_code = ''

        prefix_is_lang = (current_url_lang_prefix in dict(_supported_languages).keys())

        # If no language found and the request doesn't already set a
        # language code then set the default language
        if not lang_code and not prefix_is_lang:
            if _default_language:
                lang_code = _default_language
            else:
                lang_code = 'en'

        if lang_code and lang_code != current_url_lang_prefix:
            if prefix_is_lang:
                # Replace current url language prefix
                expected_url_lang_prefix = '/{0}/'.format(lang_code)                    
                new_location = request.get_full_path().replace(
                            '/{0}/'.format(current_url_lang_prefix), expected_url_lang_prefix)
            else:
                # Add url language prefix
                new_location = '/{0}{1}'.format(lang_code, request.get_full_path())

            return http.HttpResponseRedirect(new_location)

    def process_response(self, request, response):
        """ Store the language in the session """

        # if redirect then reset the language in the session/cookie
        if response.status_code == 302:
            if hasattr(request, 'session'):
                request.session['django_language'] = None
            else:
                response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)

        return response
