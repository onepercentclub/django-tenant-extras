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
from django.utils._os import upath

from django.db import connection

from bluebottle.clients import properties


_translations = {}

def tenant_translation(language, tenant_locale_path=None):
    """
    This is taken from the Django translation utils
    https://github.com/django/django/blob/1.6.8/django/utils/translation/trans_real.py#L101-L180

    It has been altered to handle tenant specific locale file paths. 
    """

    global _translations

    t = _translations.get(language, None)
    if t is not None:
        return t

    globalpath = os.path.join(os.path.dirname(upath(sys.modules[settings.__module__].__file__)), 'locale')

    def _fetch(lang, fallback=None):

        global _translations

        res = _translations.get(lang, None)
        if res is not None:
            return res

        loc = to_locale(lang)

        def _translation(path):
            try:
                t = gettext_module.translation('django', path, [loc], DjangoTranslation)
                t.set_language(lang)
                return t
            except IOError:
                return None

        res = _translation(globalpath)

        # We want to ensure that, for example,  "en-gb" and "en-us" don't share
        # the same translation object (thus, merging en-us with a local update
        # doesn't affect en-gb), even though they will both use the core "en"
        # translation. So we have to subvert Python's internal gettext caching.
        base_lang = lambda x: x.split('-', 1)[0]
        if base_lang(lang) in [base_lang(trans) for trans in list(_translations)]:
            res._info = res._info.copy()
            res._catalog = res._catalog.copy()

        def _merge(path):
            t = _translation(path)
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

    default_translation = _fetch(settings.LANGUAGE_CODE)
    current_translation = _fetch(language, fallback=default_translation)

    return current_translation


class TenantLocaleMiddleware(_LocaleMiddleware):

    def process_request(self, request):
        tenant_name = connection.tenant.client_name 
        site_locale = os.path.join(settings.MULTI_TENANT_DIR, tenant_name, 'locale')

        check_path = self.is_language_prefix_patterns_used()
        language = translation.get_language_from_request(
            request, check_path=check_path)
        translation._trans._active.value = tenant_translation(language, site_locale)
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
        url_parts = request.path.split('/')
        current_url_lang_prefix = url_parts[1]

        # Don't redirect on API requests
        if url_parts[1] == 'api':
            return

        try:
            authenticated = request.user.is_authenticated()
        except AttributeError:
            authenticated = False

        if authenticated:
            lang_code = request.user.primary_language

            if lang_code:
                # Early redirect based on language to prevent Ember from
                # finding out and redirect after loading a complete page
                # in the wrong language.
                expected_url_lang_prefix = '/{0}/'.format(lang_code)

                if len(url_parts) >= 2:
                    if current_url_lang_prefix in dict(properties.LANGUAGES).keys() and not request.path.startswith(
                            expected_url_lang_prefix):
                        new_location = request.get_full_path().replace(
                            '/{0}/'.format(current_url_lang_prefix), expected_url_lang_prefix)

                        return http.HttpResponseRedirect(new_location)
                # End early redirect.

        else:
            if hasattr(request, 'session'):
                """ Redirect to the language in the session if it is different """
                import ipdb; ipdb.set_trace()
                session_language = request.session['django_language']
                if session_language and session_language != current_url_lang_prefix:
                    expected_url_lang_prefix = '/{0}/'.format(session_language)
                    new_location = request.get_full_path().replace(
                                    '/{0}/'.format(current_url_lang_prefix), expected_url_lang_prefix)

                    return http.HttpResponseRedirect(new_location)

                else:
                    """ Fall back to language cookie """
                    import ipdb; ipdb.set_trace()
                    # response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)