RECURRING_DONATIONS_ENABLED = {{ recurring_donations }}

CONTACT_EMAIL = '{{ contact_email }}'

TENANT_JWT_SECRET = '{{ jwt_secret}}'

DEFAULT_COUNTRY_CODE = '{{ country_code }}'

gettext_noop = lambda s: s

LANGUAGES = (
    {% if languages.nl %}('nl', gettext_noop('Dutch')),{% endif %}
    {% if languages.en %}('en', gettext_noop('English')),{% endif %}

)

LANGUAGE_CODE = '{{ language_code }}'

PROJECT_CREATE_TYPES = ['{{ project_type }}',]

MIXPANEL = '{{ mixpanel }}'
MAPS_API_KEY = '{{ maps }}'
ANALYTICS = '{{ ga_analytics }}'


