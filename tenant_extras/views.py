import os

from django.db import connection
from django.views.static import serve as base_serve

def serve(request, path, document_root=None, show_indexes=False):
    """ intercept requests for /static/cache and send them to
        the tenant cache dir
    """
    tpath = path.lstrip("/")
    if tpath.startswith("cache/") and connection.tenant:
        path = os.path.join('/' + connection.tenant.name, tpath)

    return base_serve(request, path, document_root, show_indexes)
