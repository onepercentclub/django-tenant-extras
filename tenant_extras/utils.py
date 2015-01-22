from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model


def get_client_model():
    return get_model_class('CLIENT_MODEL')

def get_model_class(model_name=None):
    """
    Returns a model class
    model_name: The model eg 'User' or 'Project'
    """
    model_path = getattr(settings, model_name)
    try:
        app_label, model_class_name = model_path.split('.')
    except ValueError:
        raise ImproperlyConfigured(
            "{0} must be of the form 'app_label.model_name'").format(model_name)

    model = get_model(app_label, model_class_name)
    if model is None:
        raise ImproperlyConfigured(
            "{0} refers to model '{1}' that has not been "
            "installed".format(model_name, model_path))

    return model
