"""Gather the Fake adapters for the e2e tests."""

import logging
from typing import Dict, List

from drode.adapters.aws import AWS, AutoscalerInfo, AWSConfigurationError
from drode.adapters.drone import (
    BuildInfo,
    Drone,
    DroneBuildError,
    DroneConfigurationError,
)

Builds = Dict[int, List[BuildInfo]]


log = logging.getLogger(__name__)


class FakeDrone(Drone):
    """Fake implementation of the Drone adapter."""

    def __init__(self, drone_url: str, drone_token: str) -> None:
        """Configure the connection details."""
        super().__init__(drone_url, drone_token)
        self.builds: Builds = {}
        self.correct_config = True

    def check_configuration(self) -> None:
        """Check if the client is able to interact with the server.

        Makes sure that an API call works as expected.

        Raises:
            DroneConfigurationError: if any of the checks fail.
        """
        if not self.correct_config:
            log.error("Drone: KO")
            raise DroneConfigurationError(
                "There was a problem contacting the Drone server. \n\n"
                "\t  Please make sure the DRONE_SERVER and DRONE_TOKEN "
                "environmental variables are set. \n"
                "\t  https://docs.drone.io/cli/configure/"
            )
        log.info("Drone: OK")

    def set_builds(self, builds: Builds) -> None:
        """Set the builds expected by the tests

        Args:
            builds: The builds definition required by the test.

                It expects a dictionary with the build number as keys, the values are
                a list of the different states of the build number each time it's
                queried.

                For example:

                builds = {
                    274: [
                        {"number": 209, "finished": 0},
                        {"number": 209, "finished": 1591129124},
                    ]
                }
        """
        self.builds = builds

    def build_info(self, project_pipeline: str, build_number: int) -> BuildInfo:
        """Return the information of the build.

        Args:
            project_pipeline: Drone pipeline identifier.
                In the format of `repo_owner/repo_name`.
            build_number: Number of drone build.

        Returns:
            info: build information.
        """
        try:
            return self.builds[build_number].pop(0)
        except KeyError as error:
            raise DroneBuildError(
                f"The build {build_number} was not found at "
                f"the pipeline {project_pipeline}"
            ) from error

    def last_build_info(self, project_pipeline: str) -> BuildInfo:
        """Return the information of the last build.

        Args:
            project_pipeline: Drone pipeline identifier.
                In the format of `repo_owner/repo_name`.
        Returns:
            info: Last build information.
        """
        try:
            last_build_number = sorted(self.builds.keys(), reverse=True)[0]
        except IndexError as error:
            raise ValueError("There are no builds") from error

        return self.build_info(project_pipeline, last_build_number)

    def last_success_build_info(
        self, project_pipeline: str, branch: str = "master"
    ) -> BuildInfo:
        """Return the information of the last successful build.

        Args:
            project_pipeline: Drone pipeline identifier.
                In the format of `repo_owner/repo_name`.
            branch: Branch to search the last build.

        Returns:
            info: last successful build number information.
        """
        build_candidates = [
            build_number
            for build_number, build in self.builds.items()
            if (
                build[0]["status"] == "success"
                and build[0]["target"] == branch
                and build[0]["event"] == "push"
            )
        ]
        try:
            last_build_number = sorted(build_candidates)[0]
        except IndexError as error:
            raise ValueError("There are no valid builds") from error

        return self.build_info(project_pipeline, last_build_number)

    def promote(
        self, project_pipeline: str, build_number: int, environment: str
    ) -> int:
        """Promotes the build_number or commit id to the desired environment.

        Args:
            project_pipeline: Drone pipeline identifier.
                In the format of `repo_owner/repo_name`.
            build_number: Number of drone build or commit id.
            environment: Environment one of ['production', 'staging']

        Returns:
            promote_build_number: Build number of the promote job.
        """
        last_build = self.last_build_info(project_pipeline)

        if not isinstance(last_build["number"], int):
            raise ValueError("You don't have defined correctly the build number")

        new_build_number = last_build["number"] + 1
        self.builds[new_build_number] = [{"number": new_build_number}]

        return new_build_number


class FakeAWS(AWS):
    """Fake implementation of the AWS adapter."""

    def __init__(self) -> None:
        """Configure the connection details."""
        super().__init__()
        self.correct_config = True

    # ignore and W0221: The parent is a static method, but we need the self here.
    #   As it's for testing there is no problem breaking the Liskov principle.
    def check_configuration(self) -> None:  # type: ignore # noqa: W0221
        """Check if the client is able to interact with the AWS server.

        Makes sure that the AWS is correctly configured.

        Raises:
            AWSConfigurationError: if any of the checks fail.
        """
        if not self.correct_config:
            log.error("AWS: KO")
            raise AWSConfigurationError()
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
                        'id': str
                        'private_ip': str
                        'status': str = Health status data in format
                            'f{HealthStatus}/{LifecycleState}'
                        'launch_time': str
                        'template': str = LaunchConfiguration or
                            LaunchTemplate:LaunchTemplateVersion that generated the
                            instance.
        Raises:
            AWSStateError: If no autoscaling groups are found with that name.
        """
        return {
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
