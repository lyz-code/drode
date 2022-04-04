"""Test the representations of data."""

from typing import Any

from _pytest.capture import CaptureFixture

from drode import services, views
from drode.adapters.aws import AWS
from drode.config import Config


def test_print_autoscaling_group_happy_path(
    aws: AWS, capsys: CaptureFixture[Any]
) -> None:
    """
    Given: The information of an autoscaling group following the AutoscalerInfo schema.
    When: print_autoscaling_group_info is called.
    Then: The expected table is printed.
    """
    autoscaler_info = aws.get_autoscaling_group("autoscaler_name")

    views.print_autoscaling_group_info(autoscaler_info)  # act

    out, err = capsys.readouterr()
    assert out == (
        "Active Template: launch-config-name\n"
        "Instance             IP            Status             Created           Template\n"
        "-------------------  ------------  -----------------  ----------------  ----------------------\n"
        "i-xxxxxxxxxxxxxxxxx  192.168.1.13  Healthy/InService  2020-06-08T11:29  old-launch-config-name\n"
    )
    assert err == ""


def test_print_status_happy_path(
    aws: AWS, config: Config, capsys: CaptureFixture[Any]
) -> None:
    """
    Given: The information of an autoscaling group, assuming it's equal for both
        environments.
    When: print_status is called.
    Then: The expected result is printed.
    """
    project_status = services.project_status(config, aws)

    views.print_status(project_status)  # act

    out, err = capsys.readouterr()
    assert out == (
        "# Production\n"
        "Active Template: launch-config-name\n"
        "Instance             IP            Status             Created           Template\n"
        "-------------------  ------------  -----------------  ----------------  ----------------------\n"
        "i-xxxxxxxxxxxxxxxxx  192.168.1.13  Healthy/InService  2020-06-08T11:29  old-launch-config-name\n"
        "\n"
        "# Staging\n"
        "Active Template: launch-config-name\n"
        "Instance             IP            Status             Created           Template\n"
        "-------------------  ------------  -----------------  ----------------  ----------------------\n"
        "i-xxxxxxxxxxxxxxxxx  192.168.1.13  Healthy/InService  2020-06-08T11:29  old-launch-config-name\n"
        "\n"
    )
    assert err == ""


def test_print_status_no_staging_key(
    aws: AWS, config: Config, capsys: CaptureFixture[Any]
) -> None:
    """
    Given: The information of an autoscaling group, assuming it's equal for both
        environments.
    When: print_status is called.
    Then: The expected result is printed.
    """
    del config["projects"]["test_project_1"]["aws"]["autoscaling_groups"]["staging"]
    project_status = services.project_status(config, aws)

    views.print_status(project_status)  # act

    out, err = capsys.readouterr()
    assert out == (
        "# Production\n"
        "Active Template: launch-config-name\n"
        "Instance             IP            Status             Created           Template\n"
        "-------------------  ------------  -----------------  ----------------  ----------------------\n"
        "i-xxxxxxxxxxxxxxxxx  192.168.1.13  Healthy/InService  2020-06-08T11:29  old-launch-config-name\n"
        "\n"
    )
    assert err == ""
