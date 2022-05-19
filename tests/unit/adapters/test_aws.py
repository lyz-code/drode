"""Test the AWS adapter."""

import datetime
import logging
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from _pytest.logging import LogCaptureFixture
from botocore.exceptions import NoRegionError

from drode.adapters.aws import AWS, AWSConfigurationError, AWSStateError


@pytest.fixture(name="boto")
def boto_() -> Generator[Mock, None, None]:
    """Prepare the boto mock."""
    boto_patch = patch("drode.adapters.aws.boto3", autospec=True)
    boto = boto_patch.start()

    yield boto

    boto_patch.stop()


# W0613: boto is not used, but it is, as we're using it to initialize the patch on each
# test.
@pytest.fixture(name="aws")
def aws_(boto: Mock) -> AWS:  # noqa: W0613
    """Prepare the AWS object to test."""
    return AWS()


def test_check_config_happy_path(aws: AWS, caplog: LogCaptureFixture) -> None:
    """
    Given: A correctly configured AWS adapter object.
    When: Configuration is checked
    Then: The user is informed of the correct state.
    """
    aws.check_configuration()  # act

    assert ("drode.adapters.aws", logging.INFO, "AWS: OK") in caplog.record_tuples


def test_check_config_unauthorized_error(
    aws: AWS, boto: Mock, caplog: LogCaptureFixture
) -> None:
    """
    Given: An incorrectly configured AWS adapter object.
    When: Configuration is checked.
    Then: The user is informed of the incorrect state and an exception is raised.
    """
    boto.client.side_effect = NoRegionError()

    with pytest.raises(AWSConfigurationError):
        aws.check_configuration()

    assert ("drode.adapters.aws", logging.ERROR, "AWS: KO") in caplog.record_tuples


def test_get_autoscaling_returns_instances_info(aws: AWS, boto: Mock) -> None:
    """
    Given: An AWS adapter.
    When: Using the get_autoscaling_group method.
    Then: The information of the autoscaling group and it's associated resources is
        returned.
    """
    boto = boto.client.return_value
    boto.describe_auto_scaling_groups.return_value = {
        "AutoScalingGroups": [
            {
                "AutoScalingGroupARN": "autoscaling_arn",
                "AutoScalingGroupName": "production_autoscaling_group_name",
                "AvailabilityZones": ["us-west-1a", "us-west-1b", "us-west-1c"],
                "CreatedTime": datetime.datetime(2020, 5, 19, 16, 8, 26, 535000),
                "DefaultCooldown": 300,
                "DesiredCapacity": 2,
                "EnabledMetrics": [],
                "HealthCheckGracePeriod": 300,
                "HealthCheckType": "ELB",
                "Instances": [
                    {
                        "AvailabilityZone": "us-west-1d",
                        "HealthStatus": "Healthy",
                        "InstanceId": "i-xxxxxxxxxxxxxxxxx",
                        "LaunchConfigurationName": "old-launch-config-name",
                        "LifecycleState": "InService",
                        "ProtectedFromScaleIn": False,
                    },
                ],
                "LaunchConfigurationName": "launch-config-name",
                "LoadBalancerNames": [],
                "MaxSize": 10,
                "MinSize": 2,
                "NewInstancesProtectedFromScaleIn": False,
                "ServiceLinkedRoleARN": "servicelinkedrolearn",
                "SuspendedProcesses": [],
                "TargetGroupARNs": ["target_group_arn"],
                "TerminationPolicies": ["Default"],
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    # ECE001: Expression is too complex (7.5 > 7). It's the way the API is defined.
    boto.describe_instances.return_value = {  # noqa: ECE001
        "Reservations": [
            {
                "Groups": [],
                "Instances": [
                    {
                        "InstanceType": "t2.medium",
                        "LaunchTime": datetime.datetime(2020, 6, 8, 11, 29, 27),
                        "PrivateIpAddress": "192.168.1.13",
                        "State": {"Code": 16, "Name": "running"},
                    }
                ],
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    desired_result = {
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
    }

    result = aws.get_autoscaling_group("production_autoscaling_group_name")

    assert result == desired_result


def test_get_autoscaling_handles_unexistent(aws: AWS, boto: Mock) -> None:
    """
    Given: An AWS adapter.
    When: Using the get_autoscaling_group on an inexistent autoscaling group.
    Then: An exception is raised.
    """
    boto = boto.client.return_value
    boto.describe_auto_scaling_groups.return_value = {
        "AutoScalingGroups": [],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    with pytest.raises(AWSStateError) as error:
        aws.get_autoscaling_group("inexistent_autoscaling_group")

    assert "There are no autoscaling groups named inexistent_autoscaling_group" in str(
        error.value
    )


def test_get_autoscaling_handles_launch_templates(aws: AWS, boto: Mock) -> None:
    """
    Given: An AWS adapter and an existing autoscaling group using launch templates.
    When: Using the get_autoscaling_group.
    Then: The information of the launch template is returned
    """
    boto = boto.client.return_value
    boto.describe_auto_scaling_groups.return_value = {
        "AutoScalingGroups": [
            {
                "AutoScalingGroupARN": "autoscaling_arn",
                "AutoScalingGroupName": "production_autoscaling_group_name",
                "AvailabilityZones": ["us-west-1a", "us-west-1b", "us-west-1c"],
                "CreatedTime": datetime.datetime(2020, 5, 19, 16, 8, 26, 535000),
                "DefaultCooldown": 300,
                "DesiredCapacity": 2,
                "EnabledMetrics": [],
                "HealthCheckGracePeriod": 300,
                "HealthCheckType": "ELB",
                "Instances": [
                    {
                        "AvailabilityZone": "us-west-1d",
                        "HealthStatus": "Healthy",
                        "InstanceId": "i-xxxxxxxxxxxxxxxxx",
                        "LaunchTemplate": {
                            "LaunchTemplateId": "lt-xxxxxxxxxxxxxxxxx",
                            "LaunchTemplateName": "old-launch-template-name",
                            "Version": "1",
                        },
                        "LifecycleState": "InService",
                        "ProtectedFromScaleIn": False,
                    },
                ],
                "LaunchTemplate": {
                    "LaunchTemplateId": "lt-xxxxxxxxxxxxxxxxx",
                    "LaunchTemplateName": "launch-template-name",
                    "Version": "1",
                },
                "LoadBalancerNames": [],
                "MaxSize": 10,
                "MinSize": 2,
                "NewInstancesProtectedFromScaleIn": False,
                "ServiceLinkedRoleARN": "servicelinkedrolearn",
                "SuspendedProcesses": [],
                "TargetGroupARNs": ["target_group_arn"],
                "TerminationPolicies": ["Default"],
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    # ECE001: Expression is too complex (7.5 > 7). It's the way the API is defined.
    boto.describe_instances.return_value = {  # noqa: ECE001
        "Reservations": [
            {
                "Groups": [],
                "Instances": [
                    {
                        "InstanceType": "t2.medium",
                        "LaunchTime": datetime.datetime(2020, 6, 8, 11, 29, 27),
                        "PrivateIpAddress": "192.168.1.13",
                        "State": {"Code": 16, "Name": "running"},
                    }
                ],
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    desired_result = {
        "template": "launch-template-name:1",
        "instances": [
            {
                "Instance": "i-xxxxxxxxxxxxxxxxx",
                "IP": "192.168.1.13",
                "Status": "Healthy/InService",
                "Created": "2020-06-08T11:29",
                "Template": "old-launch-template-name:1",
            }
        ],
    }

    result = aws.get_autoscaling_group("production_autoscaling_group_name")

    assert result == desired_result
