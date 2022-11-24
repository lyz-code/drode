"""Define the representations of the data."""

from typing import TYPE_CHECKING

import tabulate

if TYPE_CHECKING:
    from drode.adapters.aws import AutoscalerInfo
    from drode.services import PipelineTimes, ProjectStatus


def print_autoscaling_group_info(autoscaler_info: "AutoscalerInfo") -> None:
    """Print the information of the autoscaler information in table format."""
    print(f"Active Template: {autoscaler_info.template}")
    print(
        tabulate.tabulate(autoscaler_info.instances, headers="keys", tablefmt="simple")
    )


def print_status(project_status: "ProjectStatus") -> None:
    """Print the project environment status."""
    for environment, autoscaler_info in project_status.items():
        if len(autoscaler_info.instances) == 0:
            continue
        print(f"# {environment}")
        print_autoscaling_group_info(autoscaler_info)
        print()


def print_times(pipeline_name: str, pipeline_times: "PipelineTimes") -> None:
    """Print the information of the pipeline times."""
    mean_time, standard_deviation, number_builds = pipeline_times

    print(f"Analyzing pipeline {pipeline_name}")
    print(f"Using {number_builds} successful builds")
    print(f"Mean build time: {_print_time(mean_time)}")
    print(f"Standard deviation time: {_print_time(standard_deviation)}")


def _print_time(time: float) -> str:
    """Print the time with a nice format.

    Examples:
    >>> _print_time(63.1)
    "01:03"
    """
    return f"{round(time)//60:02}:{round(time)%60:02}"
