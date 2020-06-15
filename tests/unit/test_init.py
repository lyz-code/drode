from drode import main
from unittest.mock import patch

import pytest


class TestMain:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser_patch = patch('drode.load_parser', autospect=True)
        self.parser = self.parser_patch.start()
        self.parser_args = self.parser.return_value.parse_args.return_value
        self.print_patch = patch('drode.print', autospect=True)
        self.print = self.print_patch.start()

        self.dm_patch = patch('drode.DeploymentManager', autospect=True)
        self.dm = self.dm_patch.start()

        yield 'setup'

        self.parser_patch.stop()
        self.print_patch.stop()
        self.dm_patch.stop()

    def test_main_loads_parser(self):
        self.parser.parse_args = True
        main()
        assert self.parser.called

    @patch('drode.load_logger')
    def test_main_loads_logger(self, loggerMock):
        self.parser.parse_args = True
        main()
        assert loggerMock.called

    @patch('drode.config')
    def test_set_subcommand_sets_project_id(self, configMock):
        self.parser_args.project_id = 'project_id'
        self.parser_args.subcommand = 'set'

        main()

        configMock.set_active_project.assert_called_once_with(
            'project_id'
        )

    @patch('drode.config')
    def test_active_subcommand_returns_active_project_id(self, configMock):
        self.parser_args.subcommand = 'active'

        main()

        self.print.assert_called_once_with(configMock.project)

    def test_wait_subcommand_waits_deployments(self):
        self.parser_args.subcommand = 'wait'
        self.parser_args.build_number = None

        main()

        self.dm.assert_called_once_with()
        self.dm.return_value.wait.assert_called_once_with(None)

    def test_wait_subcommand_runs_terminal_bell(self):
        self.parser_args.subcommand = 'wait'
        self.parser_args.build_number = None

        main()

        self.print.assert_called_once_with('\a')
        self.dm.return_value.wait.assert_called_once_with(None)

    def test_promote_subcommand_promotes_build(self):
        self.parser_args.subcommand = 'promote'
        self.parser_args.build_number = None
        self.parser_args.environment = 'production'
        self.parser_args.wait = False

        main()

        self.dm.return_value.promote.assert_called_once_with(
            None,
            'production'
        )

    def test_promote_subcommand_can_wait_build(self):
        self.parser_args.subcommand = 'promote'
        self.parser_args.build_number = None
        self.parser_args.environment = 'production'
        self.parser_args.wait = True

        main()

        self.dm.return_value.promote.assert_called_once_with(
            None,
            'production'
        )
        self.dm.return_value.wait.assert_called_once_with(
            self.dm.return_value.promote.return_value
        )
        self.print.assert_called_once_with('\a')

    def test_promote_subcommand_doesnt_wait_by_default(self):
        self.parser_args.subcommand = 'promote'
        self.parser_args.build_number = None
        self.parser_args.environment = 'production'
        self.parser_args.wait = False

        main()

        assert self.dm.return_value.wait.called is False

    def test_verify_subcommand_calls_manager_verify_tests(self):
        self.parser_args.subcommand = 'verify'

        main()

        self.dm.return_value.verify.assert_called_once_with()

    def test_status_subcommand_calls_manager_status(self):
        self.parser_args.subcommand = 'status'

        main()

        self.dm.return_value.status.assert_called_once_with()
