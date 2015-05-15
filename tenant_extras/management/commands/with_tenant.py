import importlib

from django.db import connection
from django.core.management import call_command

from tenant_schemas.management.commands.tenant_command import Command as TenantCommand

class Command(TenantCommand):

    def handle(self, *args, **options):
        tenant = self.get_tenant_from_options_or_interactive(**options)

        # Set tenant on database connection
        connection.set_tenant(tenant)

        # Also load tenant properties
        tenant_model_path = tenant.__module__
        tenant_app_path = tenant_model_path.replace('.models', '')
        properties = importlib.import_module(tenant_app_path).properties
        properties.set_tenant(tenant)

        call_command(*args, **options)

