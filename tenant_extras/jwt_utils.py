import jwt

from rest_framework_jwt.settings import api_settings

from bluebottle.clients import properties

def jwt_secret_key():
    try:
        return properties.TENANT_JWT_SECRET
    except AttributeError:
        return api_settings.JWT_SECRET_KEY

def jwt_encode_handler(payload):
    return jwt.encode(
        payload,
        jwt_secret_key(),
        api_settings.JWT_ALGORITHM
    ).decode('utf-8')


def jwt_decode_handler(token):
    return jwt.decode(
        token,
        jwt_secret_key(),
        api_settings.JWT_VERIFY,
        verify_expiration=api_settings.JWT_VERIFY_EXPIRATION,
        leeway=api_settings.JWT_LEEWAY
    )
