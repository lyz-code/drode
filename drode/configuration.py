"""
Module to define the configuration of the main program.

Classes:
    Config: Class to manipulate the configuration of the program.
"""

from collections import UserDict
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

import logging
import os
import sys

log = logging.getLogger(__name__)


class Config(UserDict):
    """
    Class to manipulate the configuration of the program.

    Arguments:
        config_path (str): Path to the configuration file.
            Default: ~/.local/share/drode/config.yaml

    Public methods:
        check_project: Checks if the project_id exists.
        get: Fetch the configuration value of the specified key.
            If there are nested dictionaries, a dot notation can be used.
        load: Loads configuration from configuration YAML file.
        save: Saves configuration in the configuration YAML file.

    Attributes and properties:
        config_path (str): Path to the configuration file.
        data(dict): Program configuration.
    """

    def __init__(self, config_path='~/.local/share/drode/config.yaml'):
        self.config_path = os.path.expanduser(config_path)
        self.load()

    def check_project(self, project_id):
        """
        Checks if the project_id exists.

        Returns:
            None
        """

        if project_id not in self['projects'].keys():
            log.error('The project {} does not exist'.format(project_id))
            sys.exit(1)

    def get(self, key):
        """
        Fetch the configuration value of the specified key. If there are nested
        dictionaries, a dot notation can be used.

        So if the configuration contents are:

        self.data = {
            'first': {
                'second': 'value'
            },
        }

        self.data.get('first.second') == 'value'

        Arguments:
            key(str): Configuration key to fetch
        """
        keys = key.split('.')
        value = self.data.copy()

        for key in keys:
            value = value[key]

        return value

    def load(self):
        """
        Loads configuration from configuration YAML file.
        """
        try:
            with open(os.path.expanduser(self.config_path), 'r') as f:
                try:
                    self.data = YAML().load(f)
                except ScannerError as e:
                    log.error(
                        'Error parsing yaml of configuration file '
                        '{}: {}'.format(
                            e.problem_mark,
                            e.problem,
                        )
                    )
                    sys.exit(1)
        except FileNotFoundError:
            log.error(
                'Error opening configuration file {}'.format(self.config_path)
            )
            sys.exit(1)

    @property
    def project(self):
        """
        Returns the active project id.

        Returns:
            project_id(str): Active project id
        """

        try:
            if self['active_project'] is None:
                raise KeyError()
            else:
                self.check_project(self['active_project'])
                return self['active_project']

        except KeyError:
            try:
                if len(self['projects'].keys()) == 1:
                    return [key for key, value in self['projects'].items()][0]
                else:
                    log.error(
                        'There are more than one project configured but none '
                        'is marked as active. Please use drode set command to '
                        'define one'
                    )
                    sys.exit(1)
            except (KeyError, AttributeError):
                log.error('There are no projects configured.')
                sys.exit(1)

    def save(self):
        """
        Saves configuration in the configuration YAML file.
        """

        with open(os.path.expanduser(self.config_path), 'w+') as f:
            yaml = YAML()
            yaml.default_flow_style = False
            yaml.dump(self.data, f)

    def set_active_project(self, project_id):
        """
        Sets the active project.

        Returns:
            None
        """
        self.check_project(project_id)
        self['active_project'] = project_id
        self.save()
