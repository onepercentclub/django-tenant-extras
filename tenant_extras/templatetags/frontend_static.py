import json
import os
import stat
from os.path import join

from django import template
from django.conf import settings
from django.templatetags.static import StaticNode
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import connection
from django.utils._os import safe_join


register = template.Library()

_asset_map_path = safe_join(
    getattr(settings, 'MULTI_TENANT_DIST_DIR'), 'assets', 'assetMap.json'
)
try:
    with open(_asset_map_path) as f:
        ASSET_MAP = json.load(f)['assets']
except IOError:
    ASSET_MAP = {}


class StaticFilesNode(StaticNode):
    def frontend_path(self, path):
        """ Returns the frontend path for `path`.

        Tries to map the path according to the assetMap.

        If a file in the current tenant dir exists return that,
        else just return the path.
        """
        if getattr(connection , 'tenant', None):
            # Check if it is a file in the client dir
            client_path = join(connection.tenant.client_name, path)
            client_path = ASSET_MAP.get(client_path, client_path)

            if os.path.isfile(safe_join(getattr(settings, 'MULTI_TENANT_DIST_DIR'), client_path)):
                return client_path

        # Not a client file: try to map it as a normal file
        return ASSET_MAP.get(path, path)

    def url(self, context):
        path = self.path.resolve(context)
        if not getattr(connection , 'tenant', None):
            return staticfiles_storage.url(path)


        frontend_path = self.frontend_path(path)
        full_frontend_path = safe_join(getattr(settings, 'MULTI_TENANT_DIST_DIR'), frontend_path)

        if os.path.isfile(full_frontend_path):
            static_path = staticfiles_storage.url("/".join(['frontend', frontend_path]))
            versioned_path = '%s?v=%s' % (static_path, os.stat(full_frontend_path)[stat.ST_MTIME])

            return versioned_path

        return staticfiles_storage.url(path)


@register.tag('frontend_static')
def do_static(parser, token):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend

    Usage::

        {% static path [as varname] %}

    Examples::
        {% tenant_static "css/screen.css" %}
        Will resolve to /static/assets/<client_name>/css/screen.css
        <client_name> will depend on the Tenant

    """
    return StaticFilesNode.handle_token(parser, token)

