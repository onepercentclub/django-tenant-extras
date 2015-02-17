import json

from django.db import connection
from .utils import get_tenant_properties


def tenant(request):
    """
    Add tenant to request context
    """
    if connection.tenant:
        current_tenant = connection.tenant
        properties = get_tenant_properties()

        return {
            'DONATIONS_ENABLED': getattr(properties, 'DONATIONS_ENABLED'),
            'RECURRING_DONATIONS_ENABLED': getattr(properties, 'RECURRING_DONATIONS_ENABLED'),
            'TENANT': connection,
            'TENANT_LANGUAGE': '{0}{1}'.format(current_tenant.client_name, request.LANGUAGE_CODE),
            'LANGUAGES': json.dumps([{'code': lang[0], 'name': lang[1]} for lang in getattr(properties, 'LANGUAGES')])
        }
    return {}

