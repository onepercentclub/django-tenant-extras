import mock

from django.test import TestCase
from django.test.utils import override_settings
from django.core.management import call_command
from ..management.commands.base import Command
from ..management.commands.compilepo import Command as CompileCommand


@override_settings(TENANT_APPS=('django_nose',),
                   TENANT_MODEL='client.clients',
                   DATABASE_ROUTERS=('tenant_schemas.routers.TenantSyncRouter',))
class ManagementCommandArgsTests(TestCase):
    def test_base(self):
        cmd = Command()

        self.assertEqual(cmd.option_list, [])

    def test_compile(self):
        cmd = CompileCommand()

        self.assertEqual(len(cmd.option_list), 2)
        self.assertEqual(cmd.option_list[0].dest, 'locale')
        self.assertEqual(cmd.option_list[1].dest, 'tenant')

    def test_tenant_domain(self):
        from ..management.commands.tenant_domain import Command as TenantDomainCommand
        cmd = TenantDomainCommand()

        self.assertEqual(len(cmd.option_list), 2)
        self.assertEqual(cmd.option_list[0].dest, 'tenant')
        self.assertEqual(cmd.option_list[1].dest, 'domain')

    def test_create_tenant(self):
        from ..management.commands.create_tenant import Command as CreateTenantCommand
        cmd = CreateTenantCommand()

        self.assertEqual(len(cmd.option_list), 5)
        self.assertEqual(cmd.option_list[0].dest, 'full_name')
        self.assertEqual(cmd.option_list[1].dest, 'schema_name')
        self.assertEqual(cmd.option_list[2].dest, 'domain_url')
        self.assertEqual(cmd.option_list[3].dest, 'client_name')
        self.assertEqual(cmd.option_list[4].dest, 'post_command')

    def test_txpull(self):
        from ..management.commands.txpull import Command as TxPullCommand
        cmd = TxPullCommand()

        self.assertEqual(len(cmd.option_list), 5)
        self.assertEqual(cmd.option_list[0].dest, 'all')
        self.assertEqual(cmd.option_list[1].dest, 'tenant')
        self.assertEqual(cmd.option_list[2].dest, 'deploy')
        self.assertEqual(cmd.option_list[3].dest, 'frontend')
        self.assertEqual(cmd.option_list[4].dest, 'frontend_dir')

    def test_translate(self):
        from ..management.commands.translate import Command as TranslateCommand
        cmd = TranslateCommand()

        self.assertEqual(len(cmd.option_list), 4)
        self.assertEqual(cmd.option_list[0].dest, 'tenant')
        self.assertEqual(cmd.option_list[1].dest, 'locale')
        self.assertEqual(cmd.option_list[2].dest, 'compile')
        self.assertEqual(cmd.option_list[3].dest, 'pocmd')

    def test_txtranslate(self):
        from ..management.commands.txtranslate import Command as TxTranslateCommand
        cmd = TxTranslateCommand()

        self.assertEqual(len(cmd.option_list), 5)
        self.assertEqual(cmd.option_list[0].dest, 'tenant')
        self.assertEqual(cmd.option_list[1].dest, 'locale')
        self.assertEqual(cmd.option_list[2].dest, 'compile')
        self.assertEqual(cmd.option_list[3].dest, 'pocmd')
        self.assertEqual(cmd.option_list[4].dest, 'push')


@override_settings(TENANT_APPS=('django_nose',),
                   TENANT_MODEL='client.clients',
                   DATABASE_ROUTERS=('tenant_schemas.routers.TenantSyncRouter',))
class ManagementCommandTests(TestCase):
    def test_tenant_domain(self):
        from ..management.commands.tenant_domain import Command as TenantDomainCommand
        cmd = TenantDomainCommand()

        with mock.patch('tenant_extras.management.commands.tenant_domain.Command.handle') as handle_mock:
            call_command(cmd, tenant='test', domain='test.localhost')
            args, kwargs = handle_mock.call_args_list[0]
            self.assertEqual(kwargs['tenant'], 'test')
            self.assertEqual(kwargs['domain'], 'test.localhost')

    def test_create_tenant(self):
        from ..management.commands.create_tenant import Command as CreateTenantCommand
        cmd = CreateTenantCommand()

        with mock.patch('tenant_extras.management.commands.create_tenant.Command.handle') as handle_mock:
            call_command(cmd, full_name='Test Client', schema_name='test_schema', domain_url='test.localhost', 
                         client_name='test')
            args, kwargs = handle_mock.call_args_list[0]
            self.assertEqual(kwargs['full_name'], 'Test Client')
            self.assertEqual(kwargs['schema_name'], 'test_schema')
            self.assertEqual(kwargs['client_name'], 'test')
            self.assertEqual(kwargs['domain_url'], 'test.localhost')