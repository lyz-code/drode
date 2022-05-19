"""Command line interface definition."""

import logging
import sys
from typing import Optional

import click
from click.core import Context
from ruamel.yaml.parser import ParserError

from .. import services, version, views
from ..adapters.aws import AWSConfigurationError
from ..adapters.drone import DroneBuildError, DroneConfigurationError
from ..config import ConfigError
from ..version import __version__
from . import load_aws, load_config, load_drone, load_logger

log = logging.getLogger(__name__)


@click.group()
@click.version_option(version="", message=version.version_info())
@click.option("-v", "--verbose", is_flag=True)
@click.option(
    "-c",
    "--config_path",
    default="~/.local/share/drode/config.yaml",
    help="configuration file path",
    envvar="DRODE_CONFIG_PATH",
)
@click.pass_context
def cli(ctx: Context, config_path: str, verbose: bool) -> None:
    """Command line interface main click entrypoint."""
    ctx.ensure_object(dict)

    try:
        ctx.obj["config"] = load_config(config_path)
    except ParserError as error:
        log.error(error)
        sys.exit(1)

    try:
        ctx.obj["drone"]
    except KeyError:
        ctx.obj["drone"] = load_drone()

    try:
        ctx.obj["aws"]
    except KeyError:
        ctx.obj["aws"] = load_aws()

    load_logger(verbose)


@cli.command("set")
@click.argument("project_id")
@click.pass_context
def set_active_project(ctx: Context, project_id: str) -> None:
    """Activate the project."""
    try:
        services.set_active_project(ctx.obj["config"], project_id)
    except ConfigError as error:
        log.error(error)
        sys.exit(1)


@cli.command("active")
@click.pass_context
def get_active_project(ctx: Context) -> None:
    """Get the active project."""
    try:
        print(services.get_active_project(ctx.obj["config"]))
    except ConfigError as error:
        log.error(error)
        sys.exit(1)


@cli.command("wait")
@click.argument("build_number", type=int, default=None, required=False)
@click.pass_context
def wait_command(ctx: Context, build_number: Optional[int] = None) -> None:
    """Wait for the build to finish running."""
    try:
        project_id = services.get_active_project(ctx.obj["config"])
        pipeline = ctx.obj["config"]["projects"][project_id]["pipeline"]
        services.wait(ctx.obj["drone"], pipeline, build_number)
    except (DroneBuildError, ConfigError) as error:
        log.error(error)
        sys.exit(1)
    print("\a")


@cli.command()
@click.argument(
    "environment",
    type=click.Choice(["production", "staging"]),
    default="production",
    required=False,
)
@click.argument("build_number", type=int, default=None, required=False)
@click.option("-w", "--wait", is_flag=True, help="Wait for the promoted job to finish")
@click.pass_context
def promote(
    ctx: Context, environment: str, wait: bool, build_number: Optional[int] = None
) -> None:
    """Promote build_number or commit id to the desired environment."""
    try:
        project_id = services.get_active_project(ctx.obj["config"])
        pipeline = ctx.obj["config"]["projects"][project_id]["pipeline"]
        promote_build_number = services.promote(
            ctx.obj["drone"], pipeline, environment, build_number
        )

        if wait:
            services.wait(ctx.obj["drone"], project_id, promote_build_number)
            print("\a")
    except (DroneBuildError, ConfigError) as error:
        log.error(error)
        sys.exit(1)


@cli.command()
@click.pass_context
def verify(ctx: Context) -> None:
    """Verify that the different integrations are correctly configured."""
    try:
        log.info(f"Drode: {__version__}")
        ctx.obj["drone"].check_configuration()
        ctx.obj["aws"].check_configuration()
    except (AWSConfigurationError, DroneConfigurationError) as error:
        log.error(error)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: Context) -> None:
    """Print the status of the autoscaling groups of the active project."""
    try:
        project_status = services.project_status(ctx.obj["config"], ctx.obj["aws"])
        views.print_status(project_status)
    except ConfigError as error:
        log.error(error)
        sys.exit(1)


@cli.command(hidden=True)
def null() -> None:
    """Do nothing.

    Used for the tests until we have a better solution.
    """


if __name__ == "__main__":  # pragma: no cover
    # E1120: As the arguments are passed through the function decorators instead of
    # during the function call, pylint get's confused.
    cli(ctx={})  # noqa: E1120
