from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_tenant_properties(model_name=None):
    """
    Returns a model class
    model_name: The model eg 'User' or 'Project'
    """

    properties_path = getattr(settings, 'TENANT_PROPERTIES')

    parts = properties_path.split('.')
    module = '.'.join([parts[i] for i in range(0,len(parts)-1)])
    properties = parts[len(parts) - 1]

    try:
        m = __import__(module, fromlist=[''])
    except ImportError:
        raise ImproperlyConfigured(
            "Could not find module '{1}'".format(module))

    try:
        return getattr(m, properties)
    except AttributeError:
        raise ImproperlyConfigured(
            "{0} needs attribute name '{1}'".format(module, properties))
