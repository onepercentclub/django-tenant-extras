from optparse import make_option
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.utils.encoding import force_str
from django.utils.six.moves import input
from tenant_schemas.utils import get_tenant_model
from django.conf import settings
from django.db.utils import IntegrityError


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

    def store_client(self, name, client_name, domain_url, schema_name):
        try:
            client = get_tenant_model().objects.create(
                name=name,
                client_name=client_name,
                domain_url=domain_url,
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