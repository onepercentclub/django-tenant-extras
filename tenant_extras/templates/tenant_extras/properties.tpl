RECURRING_DONATIONS_ENABLED = {{ recurring_donations }}

CONTACT_EMAIL = '{{ contact_email }}''

TENANT_JWT_SECRET = '{{ jwt_secret}}''

DEFAULT_COUNTRY_CODE = '{{ country_code }}''

gettext_noop = lambda s: s

LANGUAGES = (
    ('nl', gettext_noop('Dutch')),
)

LANGUAGE_CODE = '{{ langauge_code }}''

PROJECT_CREATE_TYPES = ['{{ project_type }}']

MIXPANEL = '{{ mixpanel }}'
MAPS_API_KEY = '{{ maps }}'
ANALYTICS = '{{ ga_analytics }}'


