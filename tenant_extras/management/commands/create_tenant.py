import os
import random
import string
from optparse import make_option
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.utils.encoding import force_str
from django.utils.six.moves import input
from tenant_schemas.utils import get_tenant_model
from django.conf import settings
from django.db.utils import IntegrityError
from django.template.loader import render_to_string
from django.core.management import call_command
from tenant_extras.utils import update_tenant_site


class Command(BaseCommand):
    help = 'Create a tenant'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.option_list = BaseCommand.option_list + (
            make_option('--full-name', help='Specifies the full name for the tenant (e.g. "Our New Tenant").'),
            make_option('--schema-name', help='Specifies the schema name for the tenant (e.g. "new_tenant").'),
            make_option('--domain-url', help='Specifies the domain_url for the tenant (e.g. "new-tenant.localhost").'),
            make_option('--client-name', help='Specifies the client name for the tenant (e.g. "new-tenant").'),
        )


    def handle(self, *args, **options):
        name = options.get('full_name', None)
        client_name = options.get('client_name', None)
        schema_name = options.get('schema_name', None)
        domain_url = options.get('domain_url', None)

        # If full-name is specified then don't prompt for any values.
        if name:
            if not client_name:
                client_name=''.join(ch  if ch.isalnum() else '-' for ch in name).lower()
            if not schema_name:
                schema_name=client_name.replace('-', '_')
            if not domain_url:
                base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'localhost')
                domain_url='{0}.{1}'.format(client_name, base_domain)

            client = self.store_client(
                name=name,
                client_name=client_name,
                domain_url=domain_url,
                schema_name=schema_name
            )
            if not client:
                name = None

        while name is None:
            if not name:
                input_msg = 'Tenant name'
                name = input(force_str('%s: ' % input_msg))

            default_client_name=''.join(ch  if ch.isalnum() else '-' for ch in name).lower()
            default_schema_name=default_client_name.replace('-', '_')
            base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'localhost')
            default_domain_url='{0}.{1}'.format(default_client_name, base_domain)

            while client_name is None:
                if not client_name:
                    input_msg = 'Client name'
                    input_msg = "%s (leave blank to use '%s')" % (input_msg, default_client_name)
                    client_name = input(force_str('%s: ' % input_msg)) or default_client_name

            while schema_name is None:
                if not schema_name:
                    input_msg = 'Database schema name'
                    input_msg = "%s (leave blank to use '%s')" % (input_msg, default_schema_name)
                    schema_name = input(force_str('%s: ' % input_msg)) or default_schema_name

            while domain_url is None:
                if not domain_url:
                    input_msg = 'Domain url'
                    input_msg = "%s (leave blank to use '%s')" % (input_msg, default_domain_url)
                    domain_url = input(force_str('%s: ' % input_msg)) or default_domain_url

            client = self.store_client(
                name=name,
                client_name=client_name,
                domain_url=domain_url,
                schema_name=schema_name
            )
            if not client:
                name = None
                continue

        self.create_client_file_structure(client_name)
        self.create_properties_file(client_name)
        self.create_tx_config_file(client_name)
        self.load_fixtures(client_name)

    def load_fixtures(self, client_name):
        from django.db import connection

        try:
            tenant = get_tenant_model().objects.get(client_name=client_name)
            connection.set_tenant(tenant)
            call_command('loaddata', 'skills')
            call_command('loaddata', 'redirects')
            call_command('loaddata', 'project_data')
            call_command('loaddata', 'geo_data')
        except get_tenant_model.DoesNotExist:
            self.stdout("Client not found. Skipping loading fixtures")

    def create_client_file_structure(self, client_name):
        """ Create the bare directory structure for a client in Reef """
        tenant_dir = ''.join([getattr(settings, 'MULTI_TENANT_DIR', None),
                             '/', client_name])

        tx_dir = "/.tx/"
        locale_en = "/locale/en/LC_MESSAGES/"
        locale_nl = "/locale/nl/LC_MESSAGES/"
        locale_en_gb = "/locale/en_GB/LC_MESSAGES/"
        crawlable_templates = "/templates/crawlable/"

        new_dirs = [tx_dir, locale_en, locale_nl,
                    locale_en_gb, crawlable_templates]
        for new_dir in new_dirs:
            new_path = tenant_dir + new_dir
            if not os.path.exists(new_path):
                os.makedirs(new_path)

        return True

    def get_properties_information(self, client_name):

        default_project_type = 'sourcing'
        default_contact_email = 'info@onepercentclub.com'
        default_country_code = 'NL'
        default_english = 'yes'
        default_dutch = 'no'
        default_recurring_donations = 'no'

        info = {'project_type': '',
                'contact_email': '',
                'country_code': '',
                'languages': {'en': '',
                              'nl': ''},
                'language_code': '',
                'mixpanel': '',
                'maps': '',
                'ga_analytics': '',
                'recurring_donations': ''}

        while info['project_type'] is '':
            if not info['project_type']:
                input_msg = "Project type? ['funding', 'sourcing']"
                input_msg = "%s (leave blank to use '%s')" % (input_msg, default_project_type)
                user_input = input(force_str('%s: ' % input_msg)) or default_project_type

                if user_input in ['funding', 'sourcing']:
                    if user_input == 'funding':
                        input('Ask more payment details here')
                        info['project_type'] = user_input
                    else:
                        info['project_type'] = user_input
                else:
                    input(force_str("Please specify 'funding' or 'sourcing':"))

        while info['contact_email'] is '':
            if not info['contact_email']:
                input_msg = "Contact email?"
                input_msg = "%s (leave blank to use '%s')" % (input_msg, default_contact_email)
                info['contact_email'] = input(force_str('%s: ' % input_msg)) or default_contact_email

        while info['languages']['en'] is '':
            if not info['languages']['en']:
                input_msg = "Use English?"
                input_msg = "%s (leave blank to use '%s')" % (input_msg, default_english)
                info['languages']['en'] = input(force_str('%s: ' % input_msg)) or default_english

        while info['languages']['nl'] is '':
            if not info['languages']['nl']:
                input_msg = "Use Dutch?"
                input_msg = "%s (leave blank to use '%s')" % (input_msg, default_dutch)
                info['languages']['nl'] = input(force_str('%s: ' % input_msg)) or default_dutch

        while info['country_code'] is '':
            if not info['country_code']:
                input_msg = "Default country code?"
                input_msg = "%s (leave blank to use '%s')" % (input_msg, default_country_code)
                user_input = input(force_str('%s: ' % input_msg)) or default_country_code
                info['country_code'] = user_input.upper()
                info['language_code'] = user_input.lower()

        while info['recurring_donations'] is '':
            if not info['mixpanel']:
                input_msg = "Use recurring donations?"
                input_msg = "%s (leave blank to use '%s')" % (input_msg, default_recurring_donations)
                user_input = input(force_str('%s: ' % input_msg)) or default_recurring_donations

                if user_input.lower() in ['yes', 'y']:
                    info['recurring_donations'] = True
                else:
                    info['recurring_donations'] = False

        while info['mixpanel'] is '':
            if not info['mixpanel']:
                input_msg = "Mixpanel API key?"
                input_msg = "%s ('n' for no key)" % (input_msg)
                info['mixpanel'] = input(force_str('%s: ' % input_msg))

        while info['maps'] is '':
            if not info['maps']:
                input_msg = "Google Maps API key?"
                input_msg = "%s ('n' for no key)" % (input_msg)
                info['maps'] = input(force_str('%s: ' % input_msg))

        while info['ga_analytics'] is '':
            if not info['ga_analytics']:
                input_msg = "Google Analytics API key?"
                input_msg = "%s ('n' for no key)" % (input_msg)
                info['ga_analytics'] = input(force_str('%s: ' % input_msg))

        return info

    def create_properties_file(self, client_name):
        """ Write a properties.py file for the tenant """
        info = self.get_properties_information(client_name)

        info.update({'jwt_secret': self.generate_jwt_key()})

        string = render_to_string('tenant_extras/properties.tpl', info)

        properties_path = ''.join([getattr(settings, 'MULTI_TENANT_DIR', None),
                                  '/', client_name, '/properties.py'])

        with open(properties_path, "w") as properties_file:
            properties_file.write(string)

    def generate_jwt_key(self):
        """ Generate a 50 char random key"""
        return ''.join(random.choice(string.ascii_uppercase +
                                     string.digits +
                                     string.ascii_lowercase) for _ in range(50))

    def create_tx_config_file(self, client_name):
        """ Create a client-specific tx-config file """

        string = render_to_string('tenant_extras/txconfig.tpl',
                                  {'client_name': client_name})

        config_path = ''.join([getattr(settings, 'MULTI_TENANT_DIR', None),
                              '/', client_name, '/.tx/config'])

        with open(config_path, "w") as config_file:
            config_file.write(string)

    def store_client(self, name, client_name, domain_url, schema_name):
        try:
            client = get_tenant_model().objects.create(
                name=name,
                client_name=client_name,
                domain_url=domain_url.split(":", 1)[0],  # strip optional port
                schema_name=schema_name
            )
            client.save()
            update_tenant_site(client, name, domain_url)
            return client
        except exceptions.ValidationError as e:
            self.stderr.write("Error: %s" % '; '.join(e.messages))
            name = None
            return False
        except IntegrityError as e:
            self.stderr.write("Error: We've already got a tenant with that name or property.")
            return False
