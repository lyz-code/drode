"""Store the classes and fixtures used throughout the tests."""

import os
from shutil import copyfile

import pytest
from _pytest.tmpdir import TempPathFactory

from drode.config import Config

from .fake_adapters import FakeAWS, FakeDrone

os.environ["DRONE_SERVER"] = "https://drone.url"
os.environ["DRONE_TOKEN"] = "drone_token"


@pytest.fixture(name="config")
def fixture_config(tmpdir_factory: TempPathFactory) -> Config:
    """Configure the Config object for the tests."""
    data = tmpdir_factory.mktemp("data")
    config_file = str(data.join("config.yaml"))  # type: ignore
    copyfile("tests/assets/config.yaml", config_file)
    config = Config(config_file)

    return config


@pytest.fixture(name="drone")
def fake_drone_() -> FakeDrone:
    """Prepare the FakeDrone object to test."""
    return FakeDrone("https://drone.url", "drone_token")


@pytest.fixture(name="aws")
def aws_() -> FakeAWS:
    """Configure the FakeAWS adapter."""
    return FakeAWS()
