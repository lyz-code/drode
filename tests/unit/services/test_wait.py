"""Tests the wait service."""

import logging
from unittest.mock import call, patch

from _pytest.logging import LogCaptureFixture
from tests.fake_adapters import FakeDrone

from drode import services

from ...factories import BuildInfoFactory


def test_wait_waits_for_the_build_to_finish(
    drone: FakeDrone, caplog: LogCaptureFixture
) -> None:
    """
    Given: A running build with number 209.
    When: the service wait is called with the 209 build number.
    Then: It will wait till the build has finished.
    """
    # The first time we query for the job 209, we'll get that it has not finished
    drone.set_builds(
        {
            209: [
                BuildInfoFactory.build(
                    number=209,
                    event="promote",
                    trigger="trigger_author",
                    finished=0,
                ),
                BuildInfoFactory.build(
                    number=209,
                    finished=1591129124,
                    status="success",
                ),
            ]
        }
    )
    with patch("drode.services.time") as time_mock:

        result = services.wait(drone, "owner/repository", 209)

    assert result
    assert time_mock.sleep.mock_calls == [call(1)]
    expected_calls = [
        (
            "drode.services",
            logging.INFO,
            "Waiting for job #209 started by a promote event by trigger_author.",
        ),
        (
            "drode.services",
            logging.INFO,
            "Job #209 has finished with status success",
        ),
    ]
    for log_entry in expected_calls:
        assert log_entry in caplog.record_tuples


def test_wait_defaults_to_the_last_build(
    drone: FakeDrone, caplog: LogCaptureFixture
) -> None:
    """
    Given: A pipeline has multiple build numbers
    When: the service wait is called without a build number.
    Then: It will wait on the last build number.
    """
    drone.set_builds(
        {
            209: [
                BuildInfoFactory.build(
                    number=209,
                    finished=0,
                ),
                BuildInfoFactory.build(
                    number=209,
                    event="promote",
                    trigger="trigger_author",
                    finished=0,
                ),
                BuildInfoFactory.build(
                    number=209,
                    finished=1591129124,
                    status="success",
                ),
            ],
            208: [
                BuildInfoFactory.build(
                    number=208, finished=1591129124, status="success"
                )
            ],
        }
    )
    with patch("drode.services.time"):

        result = services.wait(drone, "owner/repository")

    assert result
    assert (
        "drode.services",
        logging.INFO,
        "Job #209 has finished with status success",
    ) in caplog.record_tuples


def test_wait_returns_if_there_are_no_running_builds(
    drone: FakeDrone, caplog: LogCaptureFixture
) -> None:
    """
    Given: A pipeline has only finished build numbers
    When: the service wait is called.
    Then: It will inform the user that there are no active jobs.
    """
    drone.set_builds(
        {
            208: [
                BuildInfoFactory.build(
                    number=208, finished=1591129124, status="success"
                )
            ],
        }
    )

    result = services.wait(drone, "owner/repository")

    assert result
    assert (
        "drode.services",
        logging.INFO,
        "There are no active jobs",
    ) in caplog.record_tuples
