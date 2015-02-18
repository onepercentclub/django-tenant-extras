import json

from django.db import connection
from django.conf import settings
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
            'LANGUAGES': json.dumps([{'code': lang[0], 'name': lang[1]} for lang in getattr(properties, 'LANGUAGES')]),
         }
    return {}


def exposed_tenant_properties(request):
    """ 
        Dynamically populate the tenant context with exposed tenant specific properties 
        from reef/clients/client_name/properties.py
    """ 
    from .utils import get_tenant_properties
    from django.conf import settings

    context = {}

    properties = get_tenant_properties()

    props = None

    try:
        props = getattr(properties, 'EXPOSED_TENANT_PROPERTIES')
    except AttributeError:
        pass

    if not props:
        try:
            props = getattr(settings, 'EXPOSED_TENANT_PROPERTIES')
        except AttributeError:
            return context

    # Provide list of exposed arguments to create dynamic JS hooks
    context['attrs'] = props

    for item in props:
        try:
            context[item.upper()] = getattr(properties, item.upper())
        except AttributeError:
            pass

    return context

