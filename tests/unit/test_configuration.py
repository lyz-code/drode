from drode.configuration import Config
from unittest.mock import patch
from ruamel.yaml.scanner import ScannerError

import os
import pytest
import shutil
import tempfile


class TestConfig:
    """
    Class to test the Config object.

    Public attributes:
        config (Config object): Config object to test
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.config_path = 'assets/config.yaml'
        self.log_patch = patch('drode.configuration.log', autospect=True)
        self.log = self.log_patch.start()
        self.sys_patch = patch('drode.configuration.sys', autospect=True)
        self.sys = self.sys_patch.start()

        self.config = Config(self.config_path)
        yield 'setup'

        self.log_patch.stop()
        self.sys_patch.stop()

    def test_config_path_attribute_exists(self):
        assert self.config.config_path == self.config_path

    def test_get_can_fetch_nested_items_with_dots(self):
        self.config.data = {
            'first': {
                'second': 'value'
            },
        }

        assert self.config.get('first.second') == 'value'

    def test_config_can_fetch_nested_items_with_dictionary_notation(self):
        self.config.data = {
            'first': {
                'second': 'value'
            },
        }

        assert self.config['first']['second'] == 'value'

    def test_config_load(self):
        self.config.load()
        assert len(self.config.data) > 0

    @patch('drode.configuration.YAML')
    def test_load_handles_wrong_file_format(self, yamlMock):
        yamlMock.return_value.load.side_effect = ScannerError(
            'error',
            '',
            'problem',
            'mark',
        )

        self.config.load()
        self.log.error.assert_called_once_with(
            'Error parsing yaml of configuration file mark: problem'
        )
        self.sys.exit.assert_called_once_with(1)

    @patch('drode.configuration.open')
    def test_load_handles_file_not_found(self, openMock):
        openMock.side_effect = FileNotFoundError()

        self.config.load()
        self.log.error.assert_called_once_with(
            'Error opening configuration file {}'.format(
                self.config_path
            )
        )
        self.sys.exit.assert_called_once_with(1)

    @patch('drode.configuration.Config.load')
    def test_init_calls_config_load(self, loadMock):
        Config()
        loadMock.assert_called_once_with()

    def test_save_config(self):
        tmp = tempfile.mkdtemp()
        save_file = os.path.join(tmp, 'yaml_save_test.yaml')
        self.config = Config(save_file)
        self.config.data = {'a': 'b'}

        self.config.save()
        with open(save_file, 'r') as f:
            assert "a:" in f.read()

        shutil.rmtree(tmp)

    def test_project_returns_only_project_if_just_one(self):
        self.config.data = {
            'projects': {
                'test_project_1': {}
            },
        }
        assert self.config.project == 'test_project_1'

    def test_project_returns_active_project_if_set(self):
        self.config.data = {
            'active_project': 'test_project_2',
            'projects': {
                'test_project_1': {},
                'test_project_2': {},
            },
        }
        assert self.config.project == 'test_project_2'

    def test_project_handles_undefined_projects(self):
        self.config.data.pop('projects')

        self.config.project

        self.log.error.assert_called_once_with(
            'There are no projects configured.'
        )
        self.sys.exit.assert_called_once_with(1)

    def test_project_handles_none_projects(self):
        self.config.project

        self.log.error.assert_called_once_with(
            'There are no projects configured.'
        )
        self.sys.exit.assert_called_once_with(1)

    def test_project_handles_several_projects_and_no_active(self):
        self.config.data = {
            'projects': {
                'test_project_1': {},
                'test_project_2': {},
            },
        }

        self.config.project

        self.log.error.assert_called_once_with(
            'There are more than one project configured but none is marked as '
            'active. Please use drode set command to define one'
        )
        self.sys.exit.assert_called_once_with(1)

    def test_project_handles_unexistent_active_project(self):
        self.config.data = {
            'active_project': 'unexistent_project',
            'projects': {
                'test_project_1': {}
            },
        }

        self.config.project

        self.log.error.assert_called_once_with(
            'The project {} does not exist'.format(
                'unexistent_project'
            )
        )
        self.sys.exit.assert_called_once_with(1)

    @patch('drode.configuration.Config.save')
    def test_set_active_project_works_if_existent(self, saveMock):
        self.config.data = {
            'projects': {
                'test_project_1': {}
            },
        }

        self.config.set_active_project('project_1')

        assert self.config['active_project'] == 'project_1'
        assert saveMock.called

    @patch('drode.configuration.Config.save')
    def test_set_active_project_handles_unexistent(self, saveMock):
        self.config.data = {
            'projects': {
                'test_project_1': {}
            },
        }

        self.config.set_active_project('unexistent_project')

        self.log.error.assert_called_once_with(
            'The project {} does not exist'.format(
                'unexistent_project'
            )
        )
        self.sys.exit.assert_called_once_with(1)
