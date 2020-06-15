from drode.cli import load_parser, load_logger
from unittest.mock import patch, call

import logging
import pytest


class TestArgparse:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = load_parser()

    def test_can_specify_wait_subcommand(self):
        arguments = [
            'wait',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]

    def test_can_specify_wait_with_build_subcommand(self):
        arguments = [
            'wait',
            '172',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]
        assert parsed.build_number == int(arguments[1])

    def test_can_specify_set_subcommand(self):
        arguments = [
            'set',
            'project_id',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]
        assert parsed.project_id == arguments[1]

    def test_can_specify_active_subcommand(self):
        arguments = [
            'active',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]

    def test_can_specify_promote_subcommand(self):
        arguments = [
            'promote',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]
        assert parsed.environment == 'production'
        assert parsed.build_number is None

    def test_can_specify_promote_build_number(self):
        arguments = [
            'promote',
            '172',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]
        assert parsed.environment == 'production'
        assert parsed.build_number == 172

    def test_can_specify_promote_environment(self):
        arguments = [
            'promote',
            '172',
            'staging',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]
        assert parsed.environment == 'staging'
        assert parsed.build_number == 172

    def test_can_specify_verify_subcommand(self):
        arguments = [
            'verify',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]

    def test_can_specify_status_subcommand(self):
        arguments = [
            'status',
        ]
        parsed = self.parser.parse_args(arguments)
        assert parsed.subcommand == arguments[0]


class TestLogger:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.logging_patch = patch('drode.cli.logging', autospect=True)
        self.logging = self.logging_patch.start()

        self.logging.DEBUG = 10
        self.logging.INFO = 20
        self.logging.WARNING = 30
        self.logging.ERROR = 40

        yield 'setup'

        self.logging_patch.stop()

    def test_logger_is_configured_by_default(self):
        load_logger()
        self.logging.addLevelName.assert_has_calls(
                [
                    call(logging.INFO, '[\033[36mINFO\033[0m]'),
                    call(logging.ERROR, '[\033[31mERROR\033[0m]'),
                    call(logging.DEBUG, '[\033[32mDEBUG\033[0m]'),
                    call(logging.WARNING, '[\033[33mWARNING\033[0m]'),
                ]
        )
        self.logging.basicConfig.assert_called_with(
                level=logging.WARNING,
                format="  %(levelname)s %(message)s",
        )
