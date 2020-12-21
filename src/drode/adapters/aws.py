"""Gather the integration with the AWS boto library."""

import logging
from typing import Dict, List

import boto3
from botocore.exceptions import ClientError, NoRegionError
from mypy_extensions import TypedDict

log = logging.getLogger(__name__)


class AWSConfigurationError(Exception):
    """Exception to gather AWS client configuration errors."""


class AWSStateError(Exception):
    """Exception to gather AWS unexpected resource states."""


InstanceInfo = Dict[str, str]
AutoscalerInfo = TypedDict(
    "AutoscalerInfo", {"template": str, "instances": List[InstanceInfo]}, total=False
)


class AWS:
    """AWS adapter."""

    @staticmethod
    def check_configuration() -> None:
        """Check if the client is able to interact with the AWS server.

        Makes sure that the AWS is correctly configured.

        Raises:
            AWSConfigurationError: if any of the checks fail.
        """
        try:
            ec2 = boto3.client("ec2")
            ec2.describe_regions()
        except (NoRegionError, ClientError) as error:
            log.error("AWS: KO")
            raise AWSConfigurationError(error) from error
        log.info("AWS: OK")

    @staticmethod
    def get_autoscaling_group(autoscaling_name: str) -> AutoscalerInfo:
        """Get information of the autoscaling group and associated resources.

        Args:
            autoscaling_name: Autoscaling group name

        Returns:
            autoscaler_info: Dictionary with the following schema:
                'template': srt = LaunchConfiguration or
                    LaunchTemplate:LaunchTemplateVersion
                'instances': List[InstanceInfo] = List of instance dictionaries with
                    the following structure:
                        'Instance': str
                        'IP': str
                        'Status': str = Health status data in format
                            'f{HealthStatus}/{LifecycleState}'
                        'Created': str
                        'Template': str = LaunchConfiguration or
                            LaunchTemplate:LaunchTemplateVersion that generated the
                            instance.
        Raises:
            AWSStateError: If no autoscaling groups are found with that name.
        """
        ec2 = boto3.client("ec2")
        autoscaling = boto3.client("autoscaling")

        autoscaler_info: AutoscalerInfo = {
            "template": "",
            "instances": [],
        }

        try:
            autoscaling_group = autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[autoscaling_name]
            )["AutoScalingGroups"][0]
            try:
                autoscaler_info["template"] = autoscaling_group[
                    "LaunchConfigurationName"
                ]
            except KeyError:
                autoscaler_info["template"] = (
                    f'{autoscaling_group["LaunchTemplate"]["LaunchTemplateName"][:35]}'
                    f':{autoscaling_group["LaunchTemplate"]["Version"]}'
                )

        except IndexError as error:
            raise AWSStateError(
                f"There are no autoscaling groups named {autoscaling_name}"
            ) from error

        for instance_data in autoscaling_group["Instances"]:
            ec2_data = ec2.describe_instances(
                InstanceIds=[instance_data["InstanceId"]]
            )["Reservations"][0]["Instances"][0]
            try:
                instance_template = instance_data["LaunchConfigurationName"][:35]
            except KeyError:
                instance_template = (
                    f'{instance_data["LaunchTemplate"]["LaunchTemplateName"][:35]}'
                    f':{instance_data["LaunchTemplate"]["Version"]}'
                )

            autoscaler_info["instances"].append(
                {
                    "Instance": instance_data["InstanceId"],
                    "IP": ec2_data["PrivateIpAddress"],
                    "Status": (
                        f"{instance_data['HealthStatus']}/"
                        f"{instance_data['LifecycleState']}"
                    ),
                    "Created": ec2_data["LaunchTime"].strftime("%Y-%m-%dT%H:%M"),
                    "Template": instance_template,
                }
            )

        return autoscaler_info
