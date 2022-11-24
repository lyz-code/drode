"""Store the classes and fixtures used throughout the tests."""

import os
from pathlib import Path
from shutil import copyfile

import pytest

from drode.config import Config

from .fake_adapters import FakeAWS, FakeDrone

os.environ["DRONE_SERVER"] = "https://drone.url"
os.environ["DRONE_TOKEN"] = "drone_token"


@pytest.fixture(name="config")
def fixture_config(tmp_path: Path) -> Config:
    """Configure the Config object for the tests."""
    data = tmp_path / "data"
    data.mkdir()
    config_file = data / "config.yaml"
    copyfile("tests/assets/config.yaml", config_file)
    config = Config(str(config_file))

    return config


@pytest.fixture(name="drone")
def fake_drone_() -> FakeDrone:
    """Prepare the FakeDrone object to test."""
    return FakeDrone("https://drone.url", "drone_token")


@pytest.fixture(name="aws")
def aws_() -> FakeAWS:
    """Configure the FakeAWS adapter."""
    return FakeAWS()
