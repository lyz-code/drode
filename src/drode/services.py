"""Gather all the orchestration functionality required by the program to work.

Classes and functions that connect the different domain model objects with the adapters
and handlers to achieve the program's purpose.
"""

import logging
import time
from typing import Dict, Optional, Union

from drode.adapters import Drone
from drode.adapters.aws import AWS, AutoscalerInfo
from drode.adapters.drone import DronePromoteError
from drode.config import Config, ConfigError

log = logging.getLogger(__name__)


def wait(
    drone: Drone, project_pipeline: str, build_number: Optional[int] = None
) -> bool:
    """Wait for the pipeline build to finish.

    Args:
        project_pipeline: Drone pipeline identifier.
            In the format of `repo_owner/repo_name`.
        build_number: Number of drone build.

    Returns:
        True: When job has finished.

    Raises:
        DroneBuildError: if the job doesn't exist
        DroneAPIError: if the API returns a job with a "number" that is not an int.
    """
    if build_number is None:
        last_build = drone.last_build_info(project_pipeline)
        if last_build["finished"] != 0:
            log.info("There are no active jobs")
            return True
        last_build_number = last_build["number"]
        build_number = last_build_number

    first_time = True
    while True:
        build = drone.build_info(project_pipeline, build_number)

        try:
            if build["finished"] == 0:
                if first_time:
                    log.info(
                        f"Waiting for job #{build['number']} started by "
                        f"a {build['event']} event by {build['trigger']}."
                    )
                    first_time = False
                time.sleep(1)
                continue
            log.info(
                f"Job #{build['number']} has finished with status {build['status']}"
            )
        except KeyError:
            log.info(f"Job #{build_number} has not started yet")
        return True


def _check_project(config: Config, project_id: str) -> None:
    """Check if the project_id exists.

    Raises:
        ConfigError: if project doesn't exist
    """
    if project_id not in config["projects"].keys():
        raise ConfigError(f"The project {project_id} does not exist")


def get_active_project(config: Config) -> str:
    """Return the active project id.

    Returns:
        project_id: Active project id

    Raises:
        ConfigError: If there are no active projects, no configured projects or
            the active project doesn't exist.
    """
    try:
        if config["active_project"] is None:
            raise KeyError("There are no active projects.")
        _check_project(config, config["active_project"])
        return config["active_project"]
    except KeyError as error:
        try:
            if len(config["projects"].keys()) == 1:
                return [key for key, value in config["projects"].items()][0]
            raise ConfigError(
                "There are more than one project configured but none "
                "is marked as active. Please use drode set command to "
                "define one."
            ) from error
        except (KeyError, AttributeError):
            raise ConfigError("There are no projects configured.") from error


def set_active_project(config: Config, project_id: str) -> None:
    """Set the active project.

    Raises:
        ConfigError: If the project to activate doesn't exist.
    """
    _check_project(config, project_id)
    config["active_project"] = project_id
    config.save()
    log.info(f"The project {project_id} is now active")


def ask(question: str) -> bool:
    """Prompt the user to answer yes or no to a question.

    Returns:
        answer: User's answer
    """
    answer = input(question)
    if answer in ["yes", "y"]:
        return True
    return False


def promote(
    drone: Drone,
    project_pipeline: str,
    environment: str,
    build_number: Optional[int] = None,
) -> Union[int, None]:
    """Promote build_number or commit id to the desired environment.

    Args:
        drone: Drone adapter.
        build_number: Number of drone build or commit id.
        project_pipeline: Drone pipeline identifier.
            In the format of `repo_owner/repo_name`.
        environment: Environment one of ['production', 'staging']

    Returns:
        build_number: Job that promotes the desired build number.

    Raises:
        DroneAPIError: if the returned build information contains an after that is not
            a string.
    """
    if build_number is None:
        build = drone.last_success_build_info(project_pipeline)
        build_number = build["number"]
    else:
        build = drone.build_info(project_pipeline, build_number)

    if build["status"] != "success":
        raise DronePromoteError(
            f"You can't promote job #{build_number} to {environment} "
            f"as it's status is {build['status']}"
        )

    log.info(
        f"You're about to promote job #{build_number} "
        f"of the pipeline {project_pipeline} to {environment}\n\n"
        f"      With commit {build['after'][:8]}: {build['message']}"
    )
    if ask("Are you sure? [y/N]: "):
        return drone.promote(project_pipeline, build_number, environment)
    return None


ProjectStatus = Dict[str, AutoscalerInfo]


def project_status(config: Config, aws: AWS) -> ProjectStatus:
    """Fetch the status of the autoscaling groups of the active project.

    Raises:
        ConfigError: If there are no active projects, no configured projects or
            the active project doesn't exist.
    """
    project: ProjectStatus = {}
    active_project = get_active_project(config)

    for environment in ["Production", "Staging"]:
        try:
            autoscaler_name = config.get(
                f"projects.{active_project}."
                f"aws.autoscaling_groups.{environment.lower()}"
            )
            if not isinstance(autoscaler_name, str):
                raise ConfigError("The autoscaler name is not a string")
            autoscaler_info = aws.get_autoscaling_group(autoscaler_name)
        except ConfigError:
            autoscaler_info = {}

        project[environment] = autoscaler_info

    return project
