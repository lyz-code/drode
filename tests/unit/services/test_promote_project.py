"""Test the promote service."""

import logging
from unittest.mock import call, patch

import pytest
from _pytest.logging import LogCaptureFixture
from tests.fake_adapters import FakeDrone

from drode import services
from drode.adapters.drone import DronePromoteError


def test_promote_promotes_desired_build_number(
    drone: FakeDrone, caplog: LogCaptureFixture
) -> None:
    """
    Given: A series of successful pipelines.
    When: the promote service is called with a valid build number.
    Then: The build is promoted.
    """
    drone.set_builds(
        {
            209: [
                {
                    "number": 209,
                    "finished": 1,
                    "target": "feat/1",
                    "status": "success",
                    "event": "push",
                }
            ],
            208: [
                {
                    "number": 208,
                    "finished": 1,
                    "target": "master",
                    "status": "success",
                    "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                    "message": "updated README",
                    "event": "push",
                }
            ],
        }
    )
    with patch("drode.services.ask", return_value=True) as ask_mock:

        result = services.promote(drone, "owner/repository", "production", 208)

    assert result == 210
    assert [call("Are you sure? [y/N]: ")] == ask_mock.mock_calls
    assert (
        "drode.services",
        logging.INFO,
        "You're about to promote job #208 of the pipeline owner/repository to "
        "production\n\n      With commit 9fc1ad6e: updated README",
    ) in caplog.record_tuples


def test_promote_does_nothing_if_user_doesnt_confirm(
    drone: FakeDrone, caplog: LogCaptureFixture
) -> None:
    """
    Given: A successful pipeline.
    When: the promote service is called with a valid build number but the user doesn't
        confirm the operation.
    Then: The build is not promoted.
    """
    drone.set_builds(
        {
            208: [
                {
                    "number": 208,
                    "finished": 1,
                    "target": "master",
                    "status": "success",
                    "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                    "message": "updated README",
                    "event": "push",
                }
            ],
        }
    )
    with patch("drode.services.ask", return_value=False) as ask_mock:

        result = services.promote(drone, "owner/repository", "production", 208)

    assert result is None
    assert [call("Are you sure? [y/N]: ")] == ask_mock.mock_calls
    assert (
        "drode.services",
        logging.INFO,
        "Job #209 has started.",
    ) not in caplog.record_tuples


def test_promote_doesnt_promote_failed_jobs(drone: FakeDrone) -> None:
    """
    Given: A failed build job
    When: the promote service is called on the failing build.
    Then: An exception is raised
    """
    drone.set_builds(
        {
            209: [
                {
                    "number": 209,
                    "status": "killed",
                }
            ]
        }
    )

    with pytest.raises(DronePromoteError) as error:
        services.promote(drone, "owner/repository", "production", 209)

    assert "You can't promote job #209 to production as it's status is killed" in str(
        error.value
    )


def test_promote_launches_last_successful_master_job_if_none(
    drone: FakeDrone, caplog: LogCaptureFixture
) -> None:
    """
    Given: A series of successful pipelines
    When: the promote service is called without any build.
    Then: The last successful build that pushed to master is promoted.
    """
    drone.set_builds(
        {
            209: [
                {
                    "number": 209,
                    "finished": 1,
                    "target": "feat/1",
                    "status": "success",
                    "event": "push",
                }
            ],
            208: [
                {
                    "number": 208,
                    "finished": 1,
                    "target": "master",
                    "status": "success",
                    "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                    "message": "updated README",
                    "event": "push",
                }
            ],
        }
    )
    with patch("drode.services.ask", return_value=True) as ask_mock:

        result = services.promote(drone, "owner/repository", "production")

    assert result == 210
    assert [call("Are you sure? [y/N]: ")] == ask_mock.mock_calls
    assert (
        "drode.services",
        logging.INFO,
        "You're about to promote job #208 of the pipeline owner/repository to "
        "production\n\n      With commit 9fc1ad6e: updated README",
    ) in caplog.record_tuples


@pytest.mark.parametrize("answer", ["yes", "y"])
def test_ask_returns_true_if_user_anwers_yes(answer: str) -> None:
    """
    Given: Nothing
    When: The user answers yes or y to the ask question
    Then: it returns True
    """
    with patch("builtins.input", return_value=answer):

        result = services.ask("Do you want to continue? ([y]/n): ")

    assert result


@pytest.mark.parametrize("answer", ["no", "n", ""])
def test_ask_returns_false_otherwise(answer: str) -> None:
    """
    Given: Nothing
    When: The user answers no or empty to the ask question
    Then: it returns True
    """
    with patch("builtins.input", return_value=answer):

        result = services.ask("Do you want to continue? ([y]/n): ")

    assert not result
