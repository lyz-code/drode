"""Test the project_status service."""

import pytest

from drode import services
from drode.adapters.aws import AWS
from drode.config import Config, ConfigError


def test_project_status_happy_path(aws: AWS, config: Config) -> None:
    """
    Given: A configured drode program.
    When: project_status is called
    Then: The project status is gathered under the ProjectStatus schema.
    """
    result = services.project_status(config, aws)

    assert result == {
        "Production": {
            "template": "launch-config-name",
            "instances": [
                {
                    "Instance": "i-xxxxxxxxxxxxxxxxx",
                    "IP": "192.168.1.13",
                    "Status": "Healthy/InService",
                    "Created": "2020-06-08T11:29",
                    "Template": "old-launch-config-name",
                }
            ],
        },
        "Staging": {
            "template": "launch-config-name",
            "instances": [
                {
                    "Instance": "i-xxxxxxxxxxxxxxxxx",
                    "IP": "192.168.1.13",
                    "Status": "Healthy/InService",
                    "Created": "2020-06-08T11:29",
                    "Template": "old-launch-config-name",
                }
            ],
        },
    }


def test_project_status_works_for_undefined_autoscaling_groups(
    aws: AWS, config: Config
) -> None:
    """
    Given: A configured drode program with an active project without autoscaling groups.
    When: project_status is called
    Then: The project status is gathered under the ProjectStatus schema.
    """
    config["active_project"] = "test_project_2"

    result = services.project_status(config, aws)

    assert result == {
        "Production": {},
        "Staging": {},
    }


def test_project_status_unhappy_path(aws: AWS, config: Config) -> None:
    """
    Given: A wrong configured drode program.
    When: project_status is called
    Then: The exception is raised
    """
    del config["active_project"]

    with pytest.raises(ConfigError) as error:
        services.project_status(config, aws)

    assert "There are more than one project configured" in str(error.value)
