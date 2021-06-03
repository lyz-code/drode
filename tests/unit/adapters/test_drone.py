"""Test the integration with the drone service."""

import logging

import pytest
from _pytest.logging import LogCaptureFixture
from requests_mock.mocker import Mocker

from drode.adapters.drone import (
    Drone,
    DroneAPIError,
    DroneBuildError,
    DroneConfigurationError,
)


@pytest.fixture(name="drone")
def drone_() -> Drone:
    """Prepare the Drone object to test."""
    return Drone("https://drone.url", "drone_token")


def test_check_config_happy_path(
    drone: Drone, caplog: LogCaptureFixture, requests_mock: Mocker
) -> None:
    """
    Given: A correctly configured Drone adapter object.
    When: Configuration is checked
    Then: The user is informed of the correct state.
    """
    requests_mock.get(f"{drone.drone_url}/api/user/repos", text="OK")

    drone.check_configuration()  # act

    assert ("drode.adapters.drone", logging.INFO, "Drone: OK") in caplog.record_tuples


def test_check_config_unauthorized_error(
    drone: Drone, caplog: LogCaptureFixture, requests_mock: Mocker
) -> None:
    """
    Given: An incorrectly configured Drone adapter object.
    When: Configuration is checked.
    Then: The user is informed of the incorrect state and an exception is raised.
    """
    requests_mock.get(f"{drone.drone_url}/api/user/repos", status_code=401)

    with pytest.raises(DroneConfigurationError):
        drone.check_configuration()

    assert ("drode.adapters.drone", logging.ERROR, "Drone: KO") in caplog.record_tuples


def test_build_info_returns_expected_json(drone: Drone, requests_mock: Mocker) -> None:
    """
    Given: A Drone adapter object.
    When: The build_info method is called for id 274.
    Then: The json of the 274 build is returned.
    """
    response_json = {
        "id": 879,
        "status": "success",
        "number": "209",
        "trigger": "trigger_author",
        "event": "promote",
        "message": "commit message",
        "source": "master",
        "after": "9d924b358sflwegk30bbfa0571f754ec2a0b7457",
        "target": "master",
        "author_name": "Commit Author",
        "deploy_to": "production",
        "started": 1591128214,
        "finished": 0,
        "stages": [],
    }
    requests_mock.get(
        f"{drone.drone_url}/api/repos/owner/repository/builds/274",
        json=response_json,
        status_code=200,
    )

    result = drone.build_info("owner/repository", 274)

    assert result == response_json


def test_build_info_raises_exception_if_build_number_doesnt_exist(
    drone: Drone, requests_mock: Mocker
) -> None:
    """
    Given: A Drone adapter object.
    When: The build_info method is called with an inexistent job id.
    Then: A DroneAPIError exception is raised
    """
    requests_mock.get(
        f"{drone.drone_url}/api/repos/owner/repository/builds/9999",
        status_code=404,
    )

    with pytest.raises(DroneBuildError) as error:
        drone.build_info("owner/repository", 9999)

    assert "The build 9999 was not found at the pipeline owner/repository" in str(
        error.value
    )


def test_last_build_info_returns_the_last_build_json(
    drone: Drone, requests_mock: Mocker
) -> None:
    """
    Given: A pipeline with multiple build jobs.
    When: The last_build_info is called.
    Then: The last job build information is returned.
    """
    response_json = [
        {
            "id": 882,
            "number": 209,
            "finished": 1,
            "status": "success",
            "source": "feat/1",
            "target": "feat/1",
        },
        {
            "id": 881,
            "number": 208,
            "finished": 1,
            "status": "success",
            "source": "master",
            "target": "master",
            "event": "promote",
        },
        {
            "id": 880,
            "number": 207,
            "finished": 1,
            "status": "success",
            "source": "master",
            "target": "master",
            "event": "push",
        },
    ]
    requests_mock.get(
        f"{drone.drone_url}/api/repos/owner/repository/builds",
        json=response_json,
    )

    result = drone.last_build_info("owner/repository")

    assert result == response_json[0]


def test_last_success_build_info_searches_master_and_push_events_by_default(
    drone: Drone, requests_mock: Mocker
) -> None:
    """
    Given: A Drone adapter object.
    When: The last_success_build_info is called.
    Then: The last successful push event to master build number is returned.
    """
    requests_mock.get(
        f"{drone.drone_url}/api/repos/owner/repository/builds",
        json=[
            {
                "id": 882,
                "number": 209,
                "finished": 1,
                "status": "success",
                "source": "feat/1",
                "target": "feat/1",
            },
            {
                "id": 881,
                "number": 208,
                "finished": 1,
                "status": "success",
                "source": "master",
                "target": "master",
                "event": "promote",
            },
            {
                "id": 880,
                "number": 207,
                "finished": 1,
                "status": "success",
                "source": "master",
                "target": "master",
                "event": "push",
            },
        ],
    )

    result = drone.last_success_build_info("owner/repository")["number"]

    assert result == 207


def test_last_success_build_info_handles_no_result(
    drone: Drone, requests_mock: Mocker
) -> None:
    """
    Given: A drone pipeline with no successful builds.
    When: last_success_build_info is called.
    Then: DroneBuildError exception is raised.
    """
    requests_mock.get(
        f"{drone.drone_url}/api/repos/owner/repository/builds",
        json=[
            {
                "id": 882,
                "number": 209,
                "finished": 1,
                "status": "failure",
                "source": "feat/1",
                "target": "feat/1",
            },
        ],
    )

    with pytest.raises(DroneBuildError) as error:
        drone.last_success_build_info("owner/repository")

    assert "There are no successful jobs with target branch master" in str(error.value)


def test_get_generates_get_request(drone: Drone, requests_mock: Mocker) -> None:
    """
    Given: A Drone adapter
    When: Using the get method
    Then: a requests object is returned with the query result.
    """
    requests_mock.get("http://url", text="hi")

    result = drone.get("http://url")

    assert result.text == "hi"
    assert requests_mock.request_history[0].method == "GET"
    assert (
        requests_mock.request_history[0].headers["Authorization"]
        == "Bearer drone_token"
    )


def test_get_generates_post_request(drone: Drone, requests_mock: Mocker) -> None:
    """
    Given: A Drone adapter
    When: Using the get method with the post argument
    Then: a requests object is returned with the query result.
    """
    requests_mock.post("http://url", text="hi")

    result = drone.get("http://url", "post")

    assert result.text == "hi"
    assert requests_mock.request_history[0].method == "POST"
    assert (
        requests_mock.request_history[0].headers["Authorization"]
        == "Bearer drone_token"
    )


def test_get_retries_url_if_there_are_errors(
    drone: Drone, requests_mock: Mocker
) -> None:
    """
    Given: A Drone adapter.
    When: Using the get method and the API returns a 401 less than the maximum allowed.
    Then: A requests object is returned with the query result.
    """
    # ignore: Argument 2 to "get" of "MockerCore" has incompatible type
    #   "List[object]"; expected "int". The library doesn't have type hints so there's
    #   nothing we can do
    requests_mock.get(
        "http://url",
        [
            {"status_code": 401},
            {"status_code": 401},
            {"status_code": 401},
            {"status_code": 401},
            {"text": "hi", "status_code": 200},
        ],
    )

    result = drone.get("http://url")

    assert result.text == "hi"
    assert requests_mock.request_history[0].method == "GET"


def test_get_handles_url_errors(drone: Drone, requests_mock: Mocker) -> None:
    """
    Given: A Drone adapter.
    When: Using the get method and the API returns a 401 more than the allowed retries.
    Then: a DroneAPIError exception is raised.
    """
    # ignore: Argument 2 to "get" of "MockerCore" has incompatible type
    #   "List[object]"; expected "int". The library doesn't have type hints so there's
    #   nothing we can do
    requests_mock.get(
        "http://url",
        [
            {"status_code": 401},
            {"status_code": 401},
            {"status_code": 401},
            {"status_code": 401},
            {"status_code": 401},
            {"status_code": 401},
        ],
    )

    with pytest.raises(DroneAPIError) as error:
        drone.get("http://url")

    assert "401 error while trying to access http://url" in str(error.value)


def test_promote_launches_promote_drone_job(
    drone: Drone, requests_mock: Mocker, caplog: LogCaptureFixture
) -> None:
    """
    Given: A Drone adapter.
    When: Using the promote method.
    Then: Calls the promote API method with the desired build number.
    """
    requests_mock.get(
        f"{drone.drone_url}/api/repos/owner/repository/builds/172",
        json={
            "id": 882,
            "number": 172,
            "status": "success",
            "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
            "target": "master",
            "event": "push",
            "message": "updated README",
        },
    )
    promote_url = (
        f"{drone.drone_url}/api/repos/owner/repository/builds/172/promote"
        "?target=production"
    )
    requests_mock.post(
        promote_url,
        json={
            "id": 100207,
            "number": 174,
            "parent": 172,
            "status": "pending",
            "event": "promote",
            "message": "updated README",
            "before": "e3320539a4c03ccfda992641646deb67d8bf98f3",
            "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
            "source": "master",
            "target": "master",
            "author_login": "octocat",
            "author_name": "The Octocat",
            "sender": "bradrydzewski",
            "started": 0,
            "finished": 0,
            "stages": [],
        },
    )

    result = drone.promote("owner/repository", 172, "production")

    assert result == 174
    assert requests_mock.request_history[-1].method == "POST"
    assert requests_mock.request_history[-1].url == promote_url
    assert (
        "drode.adapters.drone",
        logging.INFO,
        "Job #174 has started.",
    ) in caplog.record_tuples
