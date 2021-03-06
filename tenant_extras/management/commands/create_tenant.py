from optparse import make_option
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.utils.encoding import force_str
from django.utils.six.moves import input
from tenant_schemas.utils import get_tenant_model
from django.conf import settings
from django.db.utils import IntegrityError
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Create a tenant'

    def add_arguments(self, parser):
        parser.add_argument('--full-name', help='Specifies the full name for the tenant (e.g. "Our New Tenant").'),
        parser.add_argument('--schema-name', help='Specifies the schema name for the tenant (e.g. "new_tenant").'),
        parser.add_argument('--domain-url', help='Specifies the domain_url for the tenant (e.g. "new-tenant.localhost").'),
        parser.add_argument('--client-name', help='Specifies the client name for the tenant (e.g. "new-tenant").'),
        parser.add_argument('--post-command', help='Calls another management command after the tenant is created.')

    def handle(self, *args, **options):
        name = options.get('full_name', None)
        client_name = options.get('client_name', None)
        schema_name = options.get('schema_name', None)
        domain_url = options.get('domain_url', None)
        post_command = options.get('post_command', None)

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
            if client is False:
                break

            if not client:
                name = None
                continue

        if client and client_name:
            self.load_fixtures(client_name=client_name)

        if client and post_command:
            call_command(post_command, *args, **options)

    def load_fixtures(self, client_name):
        from django.db import connection

        try:
            tenant = get_tenant_model().objects.get(client_name=client_name)
            connection.set_tenant(tenant)
            call_command('loaddata', 'skills')
            call_command('loaddata', 'redirects')
            call_command('loaddata', 'project_data')
            call_command('loaddata', 'geo_data')
        except get_tenant_model().DoesNotExist:
            self.stdout.write("Client not found. Skipping loading fixtures")

    def store_client(self, name, client_name, domain_url, schema_name):
        try:
            client = get_tenant_model().objects.create(
                name=name,
                client_name=client_name,
                domain_url=domain_url.split(":", 1)[0],  # strip optional port
                schema_name=schema_name
            )
            client.save()
            return client
        except exceptions.ValidationError as e:
            self.stderr.write("Error: %s" % '; '.join(e.messages))
            name = None
            return False
        except IntegrityError as e:
            self.stderr.write("Error: We've already got a tenant with that name or property.")
            return False
