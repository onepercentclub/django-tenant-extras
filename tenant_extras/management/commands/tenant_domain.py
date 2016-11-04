import os
import sys
from optparse import make_option, OptionParser

from django.core.management.base import CommandError

from tenant_schemas.utils import get_public_schema_name, get_tenant_model

from .base import Command as BaseCommand


class Command(BaseCommand):
    help = "Change tenant domain name."

    option_list = BaseCommand.options + (
        make_option('--tenant', dest='tenant', default=None,
                help="Change domain for tenant."),
        make_option('--domain', dest='domain', default=None,
                help="New domain for tenant."),
    )

    def handle(self, *args, **options):
        tenant_name = options.get('tenant')
        domain = options.get('domain')

        if tenant_name is None or domain is None:
            raise CommandError("Type '%s help %s' for usage information." % (
                                os.path.basename(sys.argv[0]), sys.argv[1]))

        tenant = get_tenant_model().objects.get(client_name=tenant_name)
        tenant.domain_url = domain.split(":", 1)[0]  # remove port, if any
        tenant.save()

        self.stdout.write('Updated {0} to use {1}'.format(tenant_name, domain))
