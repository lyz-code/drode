"""Define the factories of the program."""

from typing import Any

from pydantic_factories import ModelFactory

from drode.adapters.drone import BuildInfo


class BuildInfoFactory(ModelFactory[Any]):
    """Define factory for the BuildInfo model."""

    __model__ = BuildInfo
