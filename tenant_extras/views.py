import os

from django.db import connection
from django.views.static import serve as base_serve

def serve(request, path, document_root=None, show_indexes=False):
    """ intercept requests for /static/cache and send them to
        the tenant cache dir
    """
    tpath = path.lstrip("/")
    if connection.tenant and (tpath.startswith("cache/") or
       request.META.get('PATH_INFO', '').startswith('/media/')):
        path = os.path.join('/' + connection.tenant.schema_name, tpath)

    return base_serve(request, path, document_root, show_indexes)
