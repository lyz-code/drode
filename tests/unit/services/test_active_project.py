"""Test the get_active_project and set_active_project services."""

import logging

import pytest
from _pytest.logging import LogCaptureFixture

from drode import services
from drode.config import Config, ConfigError


def test_project_returns_only_project_if_just_one(config: Config) -> None:
    """
    Given: A configuration with just one project.
    When: Asked for the project.
    Then: The project is returned.
    """
    config.data = {
        "projects": {"test_project_1": {}},
    }

    result = services.get_active_project(config)

    assert result == "test_project_1"


def test_project_returns_active_project_if_set(config: Config) -> None:
    """
    Given: A configuration with two projects and one activated.
    When: Asked for the project.
    Then: The activated project is returned.
    """
    config.data = {
        "active_project": "test_project_2",
        "projects": {
            "test_project_1": {},
            "test_project_2": {},
        },
    }

    result = services.get_active_project(config)

    assert result == "test_project_2"


def test_project_handles_undefined_projects(config: Config) -> None:
    """
    Given: A configuration with no projects key.
    When: Asked for the project.
    Then: A ConfigError exception is raised.
    """
    config.data.pop("projects")

    with pytest.raises(ConfigError):
        services.get_active_project(config)


def test_project_handles_none_projects(config: Config) -> None:
    """
    Given: A configuration with no configured projects.
    When: Asked for the project.
    Then: A ConfigError exception is raised.
    """
    config.data["projects"] = {}

    with pytest.raises(ConfigError):
        services.get_active_project(config)


def test_project_handles_several_projects_and_no_active(config: Config) -> None:
    """
    Given: A configuration with more than one projects but none activated.
    When: Asked for the project.
    Then: A ConfigError exception is raised.
    """
    config.data = {
        "active_project": None,
        "projects": {
            "test_project_1": {},
            "test_project_2": {},
        },
    }

    with pytest.raises(ConfigError):
        services.get_active_project(config)


def test_project_handles_inexistent_active_project(config: Config) -> None:
    """
    Given: A configuration with an active project that doesn't exist.
    When: Asked for the project.
    Then: A ConfigError exception is raised.
    """
    config.data = {
        "active_project": "inexistent_project",
        "projects": {"test_project_1": {}},
    }

    with pytest.raises(ConfigError):
        services.get_active_project(config)


def test_set_active_project_works_if_existent(
    config: Config, caplog: LogCaptureFixture
) -> None:
    """
    Given: A configuration with configured project.
    When: Set that project as active.
    Then: The project is activated and the configuration is saved.
    """
    config.data = {
        "projects": {"project_1": {}},
    }

    services.set_active_project(config, "project_1")  # act

    # Reload the config from the file
    Config(config.config_path)
    assert config["active_project"] == "project_1"
    assert (
        "drode.services",
        logging.INFO,
        "The project project_1 is now active",
    ) in caplog.record_tuples


def test_set_active_project_handles_inexistent(config: Config) -> None:
    """
    Given: A configuration without configured projects.
    When: Activating an inexistent project.
    Then: A ConfigError exception is raised.
    """
    config.data = {
        "projects": {"test_project_1": {}},
    }

    with pytest.raises(ConfigError):
        services.set_active_project(config, "inexistent_project")
