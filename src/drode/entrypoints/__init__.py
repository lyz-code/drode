"""Define the different ways to expose the program functionality.

Functions:
    load_logger: Configure the Logging logger.
"""

import logging
import os
import sys

from drode.adapters import Drone
from drode.adapters.aws import AWS
from drode.config import Config, ConfigError

log = logging.getLogger(__name__)


def load_config(config_path: str) -> Config:
    """Configure the Config object."""
    try:
        return Config(config_path)
    except ConfigError as error:
        log.error(str(error))
        sys.exit(1)


def load_drone() -> Drone:
    """Configure the Drone adapter."""
    try:
        drone_url = os.environ["DRONE_SERVER"]
        drone_token = os.environ["DRONE_TOKEN"]
    except KeyError:
        log.error("Please set the DRONE_SERVER and DRONE_TOKEN environmental variables")
        sys.exit(1)

    return Drone(drone_url, drone_token)


def load_aws() -> AWS:
    """Configure the AWS adapter."""
    return AWS()


# I have no idea how to test this function :(. If you do, please send a PR.
def load_logger(verbose: bool = False) -> None:  # pragma no cover
    """Configure the Logging logger.

    Args:
        verbose: Set the logging level to Debug.
    """
    logging.addLevelName(logging.INFO, "[\033[36m+\033[0m]")
    logging.addLevelName(logging.ERROR, "[\033[31m+\033[0m]")
    logging.addLevelName(logging.DEBUG, "[\033[32m+\033[0m]")
    logging.addLevelName(logging.WARNING, "[\033[33m+\033[0m]")
    if verbose:
        logging.basicConfig(
            stream=sys.stderr, level=logging.DEBUG, format="  %(levelname)s %(message)s"
        )
    else:
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.basicConfig(
            stream=sys.stderr, level=logging.INFO, format="  %(levelname)s %(message)s"
        )
