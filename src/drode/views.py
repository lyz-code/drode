"""Define the representations of the data."""

import tabulate

from drode.adapters.aws import AutoscalerInfo
from drode.services import ProjectStatus


def print_autoscaling_group_info(autoscaler_info: AutoscalerInfo) -> None:
    """Print the information of the autoscaler information in table format."""
    print(f"Active Template: {autoscaler_info['template']}")
    print(
        tabulate.tabulate(
            autoscaler_info["instances"], headers="keys", tablefmt="simple"
        )
    )


def print_status(project_status: ProjectStatus) -> None:
    """Print the project environment status."""
    for environment, autoscaler_info in project_status.items():
        if autoscaler_info == {}:
            continue
        print(f"# {environment}")
        print_autoscaling_group_info(autoscaler_info)
        print()
