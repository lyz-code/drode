"""Test the command line interface."""

import logging
import os
import re
from unittest.mock import patch

import pytest
from _pytest.logging import LogCaptureFixture
from click.testing import CliRunner
from mypy_extensions import TypedDict
from py._path.local import LocalPath
from tests.fake_adapters import FakeAWS, FakeDrone

from drode.config import Config
from drode.entrypoints.cli import cli
from drode.version import __version__

FakeDeps = TypedDict("FakeDeps", {"drone": FakeDrone, "aws": FakeAWS})


@pytest.fixture(name="fake_dependencies")
def fake_dependencies_() -> FakeDeps:
    """Configure the injection of fake dependencies."""
    return {
        "drone": FakeDrone("https://drone.url", "drone_token"),
        "aws": FakeAWS(),
    }


@pytest.fixture(name="runner")
def fixture_runner(config: Config) -> CliRunner:
    """Configure the Click cli test runner."""
    return CliRunner(
        mix_stderr=False,
        env={
            "DRODE_CONFIG_PATH": config.config_path,
            "DRONE_SERVER": "https://drone.url",
            "DRONE_TOKEN": "drone_token",
        },
    )


def test_version(runner: CliRunner) -> None:
    """Prints program version when called with --version."""
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert re.search(
        rf" *drode: {__version__}\n" r" *Python: .*\n *Platform: .*",
        result.stdout,
    )


def test_load_config_handles_configerror_exceptions(
    runner: CliRunner, tmpdir: LocalPath, caplog: LogCaptureFixture
) -> None:
    """
    Given: A wrong configuration file.
    When: CLI is initialized
    Then: The ConfigError exception is gracefully handled.
    """
    config_file = tmpdir.join("config.yaml")  # type: ignore
    config_file.write("[ invalid yaml")

    result = runner.invoke(cli, ["-c", str(config_file), "null"])

    assert result.exit_code == 1
    assert (
        "drode.entrypoints",
        logging.ERROR,
        f'while parsing a flow sequence\n  in "{config_file}", '
        "line 1, column 1\nexpected ',' or ']', but got '<stream end>'\n  in"
        f' "{config_file}", line 1, column 15',
    ) in caplog.record_tuples


def test_load_config_creates_default_file_if_it_doesnt_exist(
    runner: CliRunner, caplog: LogCaptureFixture, config: Config
) -> None:
    """
    Given: A missing configuration file.
    When: CLI is initialized
    Then: The file is created and the commandline ends well.
    """
    os.remove(config.config_path)

    result = runner.invoke(cli, ["null"])

    assert result.exit_code == 0
    with open("assets/config.yaml", "r", encoding="utf-8") as file_descriptor:
        default_config = file_descriptor.read()
    with open(config.config_path, "r", encoding="utf-8") as file_descriptor:
        created_config = file_descriptor.read()
    assert created_config == default_config


def test_set_active_project_happy_path(
    runner: CliRunner, caplog: LogCaptureFixture
) -> None:
    """
    Given: An existent project.
    When: The set subcommand is called on that project.
    Then: The project is activated
    """
    result = runner.invoke(cli, ["set", "test_project_1"])

    assert result.exit_code == 0
    assert (
        "drode.services",
        logging.INFO,
        "The project test_project_1 is now active",
    ) in caplog.record_tuples


def test_set_active_project_unhappy_path(
    runner: CliRunner, caplog: LogCaptureFixture
) -> None:
    """
    Given: A configured drode program.
    When: The set subcommand is called on an inexistent project.
    Then: The exception is gracefully handled.
    """
    result = runner.invoke(cli, ["set", "inexistent"])

    assert result.exit_code == 1
    assert (
        "drode.entrypoints.cli",
        logging.ERROR,
        "The project inexistent does not exist",
    ) in caplog.record_tuples


def test_active_project_happy_path(runner: CliRunner) -> None:
    """
    Given: An existent project.
    When: The active subcommand is called on that project.
    Then: The project that is active is returned.
    """
    result = runner.invoke(cli, ["active"])

    assert result.exit_code == 0
    assert "test_project_1" in result.stdout


def test_active_project_unhappy_path(
    runner: CliRunner, caplog: LogCaptureFixture, config: Config
) -> None:
    """
    Given: A drode program without any active project
    When: The active subcommand is called.
    Then: The exception is gracefully handled.
    """
    del config.data["active_project"]
    config.save()

    result = runner.invoke(cli, ["active"])

    assert result.exit_code == 1
    assert (
        "drode.entrypoints.cli",
        logging.ERROR,
        "There are more than one project configured but none is marked as active. "
        "Please use drode set command to define one.",
    ) in caplog.record_tuples


def test_wait_subcommand_calls_wait_service(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A configured drode program and a drone server with no active jobs.
    When: The wait subcommand is called without a build number.
    Then: The service wait is called and it informs that there are no active jobs,
        raising the terminal bell when finished.
    """
    fake_dependencies["drone"].set_builds({209: [{"number": 209, "finished": 1}]})

    result = runner.invoke(cli, ["wait"], obj=fake_dependencies)

    assert result.exit_code == 0
    assert "\x07" in result.stdout
    assert (
        "drode.services",
        logging.INFO,
        "There are no active jobs",
    ) in caplog.record_tuples


def test_wait_subcommand_accepts_build_number_argument(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A configured drode program and a drone server with no active jobs.
    When: The wait command is called with a non existent build number.
    Then: The service wait is called with the build number.
    """
    fake_dependencies["drone"].set_builds({209: [{"number": 209}]})

    result = runner.invoke(cli, ["wait", "209"], obj=fake_dependencies)

    assert result.exit_code == 0
    assert (
        "drode.services",
        logging.INFO,
        "Job #209 has not started yet",
    ) in caplog.record_tuples


def test_wait_subcommand_handles_unhappy_path(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A faulty Drone adapter that raises an error
    When: The wait subcommand is called with an inexistent job number.
    Then: The exception is handled gracefully.
    """
    # ignore: we know that the type of number is wrong, we want to raise the exception.
    fake_dependencies["drone"].set_builds(
        {209: [{"number": "invalid", "finished": 1}]}  # type: ignore
    )

    result = runner.invoke(cli, ["wait", "1"], obj=fake_dependencies)

    assert result.exit_code == 1
    assert (
        "drode.entrypoints.cli",
        logging.ERROR,
        "The build 1 was not found at the pipeline test_projects/webpage",
    ) in caplog.record_tuples


def test_load_drone_handles_wrong_drone_credentials(
    config: Config, caplog: LogCaptureFixture
) -> None:
    """
    Given: A user environment without the required drone environmental variables.
    When: Trying to load the Drone object
    Then: The user is informed of the issue and the program exits.
    """
    del os.environ["DRONE_TOKEN"]
    runner = CliRunner(
        mix_stderr=False,
        env={
            "DRODE_CONFIG_PATH": config.config_path,
            "DRONE_SERVER": "https://drone.url",
        },
    )

    result = runner.invoke(cli, ["null"])

    assert result.exit_code == 1
    assert (
        "drode.entrypoints",
        logging.ERROR,
        "Please set the DRONE_SERVER and DRONE_TOKEN environmental variables",
    ) in caplog.record_tuples


def test_promote_happy_path(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A drode program with a valid job to promote
    When: The promote subcommand is called on that build.
    Then: The build is promoted.
    """
    fake_dependencies["drone"].set_builds(
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
                },
                {
                    "number": 208,
                    "finished": 1,
                    "target": "master",
                    "status": "success",
                    "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                    "message": "updated README",
                    "event": "push",
                },
            ],
        }
    )
    with patch("drode.services.ask", return_value=True):

        result = runner.invoke(
            cli, ["promote", "production", "208"], obj=fake_dependencies
        )

    assert result.exit_code == 0
    assert (
        "drode.services",
        logging.INFO,
        "You're about to promote job #208 of the pipeline test_projects/webpage to "
        "production\n\n      With commit 9fc1ad6e: updated README",
    ) in caplog.record_tuples


@pytest.mark.parametrize("wait_flag", ["-w", "--wait"])
def test_promote_happy_path_with_wait_flag(
    runner: CliRunner,
    caplog: LogCaptureFixture,
    wait_flag: str,
    fake_dependencies: FakeDeps,
) -> None:
    """
    Given: A drode program with a valid job to promote
    When: The promote subcommand is called on that build with the wait flag.
    Then: The build is promoted and then we wait for it to finish.
    """
    fake_dependencies["drone"].set_builds(
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
                },
                {
                    "number": 208,
                    "finished": 1,
                    "target": "master",
                    "status": "success",
                    "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                    "message": "updated README",
                    "event": "push",
                },
            ],
        }
    )
    with patch("drode.services.ask", return_value=True):

        result = runner.invoke(
            cli, ["promote", "production", "208", wait_flag], obj=fake_dependencies
        )

    assert result.exit_code == 0
    # Assert we are promoting the build
    assert (
        "drode.services",
        logging.INFO,
        "You're about to promote job #208 of the pipeline test_projects/webpage to "
        "production\n\n      With commit 9fc1ad6e: updated README",
    ) in caplog.record_tuples
    # Assert we are waiting for the promote build
    assert (
        "drode.services",
        logging.INFO,
        "Job #209 has not started yet",
    ) in caplog.record_tuples


def test_promote_unhappy_path(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A drode program with valid jobs to promote
    When: The user tries to promote an inexistent job.
    Then: The exception is handled gracefully
    """
    result = runner.invoke(cli, ["promote", "production", "208"], obj=fake_dependencies)

    assert result.exit_code == 1
    assert (
        "drode.entrypoints.cli",
        logging.ERROR,
        "The build 208 was not found at the pipeline test_projects/webpage",
    ) in caplog.record_tuples


def test_verify_happy_path(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A Drone and AWS correct configurations.
    When: The verify command is called
    Then: The user is informed of the correct configuration.
    """
    result = runner.invoke(cli, ["verify"], obj=fake_dependencies)

    assert result.exit_code == 0
    expected_calls = [
        ("drode.entrypoints.cli", logging.INFO, f"Drode: {__version__}"),
        ("tests.fake_adapters", logging.INFO, "Drone: OK"),
        ("tests.fake_adapters", logging.INFO, "AWS: OK"),
    ]
    for expected_call in expected_calls:
        assert expected_call in caplog.record_tuples


def test_verify_fails_gracefully_on_drone_error(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A wrong Drone and AWS correct configurations.
    When: The verify command is called
    Then: The Drone exception is handled gracefully
    """
    fake_dependencies["drone"].correct_config = False

    result = runner.invoke(cli, ["verify"], obj=fake_dependencies)

    assert result.exit_code == 1
    expected_calls = [
        ("drode.entrypoints.cli", logging.INFO, f"Drode: {__version__}"),
        ("tests.fake_adapters", logging.ERROR, "Drone: KO"),
    ]
    for expected_call in expected_calls:
        assert expected_call in caplog.record_tuples


def test_verify_fails_gracefully_on_aws_error(
    runner: CliRunner, caplog: LogCaptureFixture, fake_dependencies: FakeDeps
) -> None:
    """
    Given: A wrong Drone and AWS correct configurations.
    When: The verify command is called
    Then: The Drone exception is handled gracefully
    """
    fake_dependencies["aws"].correct_config = False

    result = runner.invoke(cli, ["verify"], obj=fake_dependencies)

    assert result.exit_code == 1
    expected_calls = [
        ("drode.entrypoints.cli", logging.INFO, f"Drode: {__version__}"),
        ("tests.fake_adapters", logging.INFO, "Drone: OK"),
        ("tests.fake_adapters", logging.ERROR, "AWS: KO"),
    ]
    for expected_call in expected_calls:
        assert expected_call in caplog.record_tuples


def test_status_happy_path(runner: CliRunner, fake_dependencies: FakeDeps) -> None:
    """
    Given: A correctly configured drode program
    When: The status command is called
    Then: The expected output is returned
    """
    result = runner.invoke(cli, ["status"], obj=fake_dependencies)

    assert result.exit_code == 0
    assert "# Production" in result.output


def test_status_unhappy_path(
    runner: CliRunner,
    fake_dependencies: FakeDeps,
    caplog: LogCaptureFixture,
    config: Config,
) -> None:
    """
    Given: A wrong configured drode program.
    When: The status command is called.
    Then: The exception is handled gracefuly.
    """
    del config.data["active_project"]
    config.save()

    result = runner.invoke(cli, ["status"], obj=fake_dependencies)

    assert result.exit_code == 1
    assert (
        "drode.entrypoints.cli",
        logging.ERROR,
        "There are more than one project configured but none is marked as active. "
        "Please use drode set command to define one.",
    ) in caplog.record_tuples
