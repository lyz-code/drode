"""Gather the integration with the Drone web application."""

import logging
from typing import Any, List

import requests
from mypy_extensions import TypedDict

log = logging.getLogger(__name__)


class DroneConfigurationError(Exception):
    """Exception to gather drone client configuration errors."""


class DroneBuildError(Exception):
    """Exception to gather drone pipeline build errors."""


class DroneAPIError(Exception):
    """Exception to gather drone API errors."""


class DronePromoteError(Exception):
    """Exception to gather job promotion errors."""


class BuildInfo(TypedDict, total=False):
    """Build information schema."""

    # VNE003: variables should not shadow builtins. As we're defining just the schema
    #   of a dictionary we can safely ignore it.
    id: int  # noqa: VNE003
    status: str
    number: int
    trigger: str
    event: str
    message: str
    source: str
    after: str
    target: str
    author_name: str
    deploy_to: str
    started: int
    finished: int
    stages: List[Any]


class Drone:
    """Drone adapter.

    Attributes:
        drone_url: Drone API server base url.
        drone_token: Drone token to interact with the API.
    """

    def __init__(self, drone_url: str, drone_token: str) -> None:
        """Configure the connection details."""
        self.drone_url = drone_url
        self.drone_token = drone_token

    def check_configuration(self) -> None:
        """Check if the client is able to interact with the server.

        Makes sure that an API call works as expected.

        Raises:
            DroneConfigurationError: if any of the checks fail.
        """
        try:
            self.get(f"{self.drone_url}/api/user/repos")
        except DroneAPIError as error:
            log.error("Drone: KO")
            raise DroneConfigurationError(
                "There was a problem contacting the Drone server. \n\n"
                "\t  Please make sure the DRONE_SERVER and DRONE_TOKEN "
                "environmental variables are set. \n"
                "\t  https://docs.drone.io/cli/configure/"
            ) from error
        log.info("Drone: OK")

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
            return self.get(
                f"{self.drone_url}/api/repos/{project_pipeline}/builds/{build_number}"
            ).json()
        except DroneAPIError as error:
            raise DroneBuildError(
                f"The build {build_number} was not found at "
                f"the pipeline {project_pipeline}"
            ) from error

    def get(
        self, url: str, method: str = "get", max_retries: int = 5
    ) -> requests.models.Response:
        """Fetch the content of an url.

        It's a requests wrapper to handle errors and configuration.

        Args:
            url: URL to fetch.
            method: HTTP method, one of ['get', 'post']

        Returns:
            response: Requests response

        Raises:
            DroneAPIError: If the drone API returns a response with status code != 200.
        """
        retry = 0
        while retry < max_retries:
            try:
                if method == "post":
                    response = requests.post(
                        url,
                        headers={"Authorization": f"Bearer {self.drone_token}"},
                    )
                else:
                    response = requests.get(
                        url,
                        headers={"Authorization": f"Bearer {self.drone_token}"},
                    )

                if response.status_code == 200:
                    return response
                retry += 1
                log.debug(f"There was an error fetching url {url}")
            except requests.exceptions.RequestException:
                retry += 1
                log.debug(f"There was an error fetching url {url}")

        raise DroneAPIError(
            f"{response.status_code} error while trying to access {url}"
        )

    def last_build_info(self, project_pipeline: str) -> BuildInfo:
        """Return the information of the last build.

        Args:
            project_pipeline: Drone pipeline identifier.
                In the format of `repo_owner/repo_name`.
        Returns:
            info: Last build information.
        """
        return self.get(f"{self.drone_url}/api/repos/{project_pipeline}/builds").json()[
            0
        ]

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
        build_history = self.get(
            f"{self.drone_url}/api/repos/{project_pipeline}/builds"
        ).json()

        for build in build_history:
            if (
                build["status"] == "success"
                and build["target"] == branch
                and build["event"] == "push"
            ):
                return build
        raise DroneBuildError(
            f"There are no successful jobs with target branch {branch}"
        )

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
        promote_url = (
            f"{self.drone_url}/api/repos/{project_pipeline}/builds/{build_number}/"
            f"promote?target={environment}"
        )
        response = self.get(promote_url, "post").json()
        log.info(f"Job #{response['number']} has started.")

        return response["number"]
