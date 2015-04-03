import json

from django.db import connection
from django.conf import settings
from .utils import get_tenant_properties

def conf_settings(request):
    """
    Some settings we want to make available in templates.
    """
    context = {}
    context['DEBUG'] = getattr(settings, 'DEBUG', False)
    context['COMPRESS_TEMPLATES'] = getattr(settings, 'COMPRESS_TEMPLATES', False)

    return context


def tenant_properties(request):
    """ 

        Dynamically populate a tenant context with exposed tenant specific properties 
        from reef/clients/client_name/properties.py. 

        The context processor looks in tenant settings for the uppercased variable names that are defined in 
        "EXPOSED_TENANT_PROPERTIES" to generate the context.

        Example:

        EXPOSED_TENANT_PROPERTIES = ['mixpanel', 'analytics']

        This adds the value of the keys MIXPANEL and ANALYTICS from the settings file to the context. 

        The values are also added to a 'settings' JSON key so a JS object can be generated from the context.

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

    # First load tenant settings that should always be exposed
    if connection.tenant:
        current_tenant = connection.tenant
        properties = get_tenant_properties()
        context['settings'] =  {
            'mapsApiKey': getattr(properties, 'MAPS_API_KEY'),
            'donationsEnabled': getattr(properties, 'DONATIONS_ENABLED'),
            'recurringDonationsEnabled': getattr(properties, 'RECURRING_DONATIONS_ENABLED'),
            'siteName': current_tenant.name,
            'tenantLanguage': '{0}{1}'.format(current_tenant.client_name, getattr(properties, 'LANGUAGE_CODE')),
            'languageCode': '{0}{1}'.format(current_tenant.client_name, request.LANGUAGE_CODE),
            'languages': [{'code': lang[0], 'name': lang[1]} for lang in getattr(properties, 'LANGUAGES')]
         }
    else:
        context['settings'] = {}

    # Now load the tenant specific properties
    for item in props:
        try:
            context[item.upper()] = getattr(properties, item.upper())
            context['settings'][item.upper()] = getattr(properties, item.upper())
        except AttributeError:
            pass

    context['settings'] = json.dumps(context['settings'])
    return context

