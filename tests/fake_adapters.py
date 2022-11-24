"""Gather the Fake adapters for the e2e tests."""

import logging
from typing import List

from drode.adapters.aws import AWS, AutoscalerInfo, AWSConfigurationError
from drode.adapters.drone import (
    BuildInfo,
    Drone,
    DroneBuildError,
    DroneConfigurationError,
)

from .factories import BuildInfoFactory

log = logging.getLogger(__name__)


class FakeDrone(Drone):
    """Fake implementation of the Drone adapter."""

    def __init__(self, drone_url: str, drone_token: str) -> None:
        """Configure the connection details."""
        super().__init__(drone_url, drone_token)
        self._builds: List[BuildInfo] = []
        self._build_infos: List[BuildInfo] = []
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

    def set_builds(self, builds: List[BuildInfo]) -> None:
        """Set the builds expected by the tests.

        Args:
            builds: The builds definition required by the test.

                For example:

                builds = [
                    BuildInfo("number": 209, "finished": 0),
                    BuildInfo("number": 209, "finished": 1591129124),
                ]
        """
        self._builds = builds

    def builds(self, project_pipeline: str) -> List[BuildInfo]:
        """Return the builds of a project pipeline.

        Args:
            project_pipeline: Drone pipeline identifier.
                In the format of `repo_owner/repo_name`.

        Returns:
            info: all builds information.
        """
        return self._builds

    def set_build_infos(self, builds: List[BuildInfo]) -> None:
        """Set the build info expected by the tests.

        Each element will be returned each time you call build_info.

        Args:
            builds: The builds definition required by the test.

                For example:

                builds = [
                    BuildInfo("number": 209, "finished": 0),
                    BuildInfo("number": 209, "finished": 1591129124),
                ]
        """
        self._build_infos = builds
        self._builds = builds

    def build_info(self, project_pipeline: str, build_number: int) -> BuildInfo:
        """Return the information of the build.

        Args:
            project_pipeline: Drone pipeline identifier.
                In the format of `repo_owner/repo_name`.
            build_number: Number of drone build.

        Returns:
            info: build information.
        """
        if self._build_infos:
            return self._build_infos.pop(0)
        try:
            return [build for build in self._builds if build.number == build_number][0]
        except IndexError as error:
            raise DroneBuildError(
                f"The build {build_number} was not found at "
                f"the pipeline {project_pipeline}"
            ) from error

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

        if not isinstance(last_build.number, int):
            raise ValueError("You don't have defined correctly the build number")

        new_build_number = last_build.number + 1
        self._builds.append(BuildInfoFactory.build(number=new_build_number))

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
        return AutoscalerInfo(
            template="launch-config-name",
            instances=[
                {
                    "Instance": "i-xxxxxxxxxxxxxxxxx",
                    "IP": "192.168.1.13",
                    "Status": "Healthy/InService",
                    "Created": "2020-06-08T11:29",
                    "Template": "old-launch-config-name",
                }
            ],
        )
