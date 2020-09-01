"""
Module to store the main class of deploy

Classes:
    DeploymentManager: Class to manipulate the deployment data
"""

import logging
import os
import sys
import time

import boto3
import requests
from tabulate import tabulate

from drode import config
from drode.version import __version__

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class DeploymentManager:
    """
    Abstract Class to manipulate the deployment data.

    Public attributes:
        builds_url: project drone builds url.
        last_build_info: Returns the information of the build.

    Public methods:
        ask: Prompts the user to answer yes or no to a question.
        build_info: Returns the information of the build.
        get: Requests wrapper to handle errors and configuration.
        last_success_build_info: Returns the information of the last
            successful build.
        promote: Promotes build_number or commit id to the desired environment.
        status: Shows the project environment status.
        verify: Checks user drode, drone and aws configuration.
        wait: Waits for the build to finish to run.
    """

    def __init__(self):
        self.config = config
        try:
            self.drone_url = os.environ["DRONE_SERVER"]
            self.drone_token = os.environ["DRONE_TOKEN"]
        except KeyError:
            self._raise_drone_config_error()

    def _print_aws_autoscaling_group_info(self, autoscaling_name):
        """
        Print information of AWS autoscaling group instances

        Arguments:
            autoscaling_name(str): Autoscaling group name
        """
        ec2 = boto3.client("ec2")
        autoscaling = boto3.client("autoscaling")

        try:
            autoscaling_group = autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames=[autoscaling_name]
            )["AutoScalingGroups"][0]
            print(
                "Active LaunchConfiguration: {}".format(
                    autoscaling_group["LaunchConfigurationName"]
                )
            )
        except IndexError:
            log.error(
                "There are no autoscaling groups named {}".format(autoscaling_name)
            )
            sys.exit(1)
        headers = [
            "Instance",
            "IP",
            "Status",
            "Created",
            "LaunchConfiguration",
        ]
        instances_data = []

        for instance_data in autoscaling_group["Instances"]:
            ec2_data = ec2.describe_instances(
                InstanceIds=[instance_data["InstanceId"]]
            )["Reservations"][0]["Instances"][0]

            instances_data.append(
                [
                    instance_data["InstanceId"],
                    ec2_data["PrivateIpAddress"],
                    "{}/{}".format(
                        instance_data["HealthStatus"], instance_data["LifecycleState"],
                    ),
                    ec2_data["LaunchTime"].strftime("%Y-%m-%dT%H:%M"),
                    instance_data["LaunchConfigurationName"][:35],
                ]
            )
        print(tabulate(instances_data, headers=headers, tablefmt="simple"))

    def _raise_drone_config_error(self):
        """
        Show Drone configuration error message and exit
        """
        log.error(
            "There was a problem contacting the Drone server. \n\n"
            "\t  Please make sure the DRONE_SERVER and DRONE_TOKEN "
            "environmental variables are set. \n"
            "\t  https://docs.drone.io/cli/configure/"
        )
        sys.exit(1)

    def ask(self, question):
        """
        Prompts the user to answer yes or no to a question.

        Returns:
            answer(bool): User's answer
        """
        answer = input(question)
        if answer in ["yes", "y"]:
            return True
        return False

    def build_info(self, build_number):
        """
        Returns the information of the build.

        Arguments:
            build_number(int): Number of drone build.

        Returns:
            info(dict): build number information.
        """
        return self.get("{}/{}".format(self.builds_url, build_number)).json()

    @property
    def builds_url(self):
        """
        Returns the builds project drone url.

        Returns:
            url(str): builds project drone url.
        """
        return "{}/api/repos/{}/builds".format(
            self.drone_url,
            self.config.get("projects.{}.pipeline".format(self.config.project)),
        )

    def get(self, url, method="get"):
        """
        Requests wrapper to handle errors and configuration.

        Arguments:
            url(str): URL to fetch.
            method(str): HTTP method, one of ['get', 'post']

        Returns:
            response(requests): Requests response
        """

        if method == "post":
            response = requests.post(
                url, headers={"Authorization": "Bearer {}".format(self.drone_token)},
            )
        else:
            response = requests.get(
                url, headers={"Authorization": "Bearer {}".format(self.drone_token)},
            )

        if response.status_code == 200:
            return response
        else:
            log.error(
                "{} error while trying to access {}".format(response.status_code, url)
            )
            sys.exit(1)

    @property
    def last_build_info(self):
        """
        Returns the information of the last build.

        Returns:
            info(dict): build number information.
        """
        return self.get(self.builds_url).json()[0]

    def last_success_build_info(self, branch="master"):
        """
        Returns the information of the last successful build.

        Arguments:
            branch(str): Branch to search the last build

        Returns:
            info(dict): build number information.
        """
        history = self.get(self.builds_url).json()

        for build in history:
            if (
                build["status"] == "success"
                and build["target"] == branch
                and build["event"] == "push"
            ):
                return build
        log.error("There are no successful jobs with target branch {}".format(branch))
        sys.exit(1)

    def promote(self, build_number, environment):
        """
        Promotes build_number or commit id to the desired environment.

        Arguments:
            build_number(int): Number of drone build or commit id.
            environment(str): Environment one of ['production', 'staging']

        Returns:
            build_number(int): Promote drone job build number.
        """

        if build_number is None:
            build = self.last_success_build_info()
            build_number = build["number"]
        else:
            build = self.build_info(build_number)

        if build["status"] != "success":
            log.error(
                "You can't promote job #{} to {} as it's status is {}".format(
                    build_number, environment, build["status"],
                )
            )
            sys.exit(1)

        log.info(
            "You're about to promote job #{} ".format(build_number)
            + "of the project {} to {}".format(self.config.project, environment)
        )
        log.info("With commit {}: {}".format(build["after"][:8], build["message"],))
        if self.ask("Are you sure? [y/n]: "):
            promote_url = "{}/{}/promote?target={}".format(
                self.builds_url, build_number, environment
            )
            response = self.get(promote_url, "post").json()
            log.info("Job #{} has started.".format(response["number"],))
            return response["number"]

    def status(self):
        """
        Shows the project environment status.
        """

        for environment in ["Production", "Staging"]:
            print("# {}".format(environment))
            try:
                self._print_aws_autoscaling_group_info(
                    self.config.get(
                        "projects.{}.aws.autoscaling_groups.{}".format(
                            self.config.project, environment.lower(),
                        )
                    )
                )
            except KeyError:
                pass
            print()

    def verify(self):
        """
        Checks user drode, drone and aws configuration.
        """
        log.info("Drode: {}".format(__version__))

        exception = False
        try:
            response = requests.get(
                "{}/api/user/repos".format(self.drone_url),
                headers={"Authorization": "Bearer {}".format(self.drone_token)},
            )
        except Exception:
            exception = True

        if exception or response.status_code != 200:
            log.error("Drone: KO")
            self._raise_drone_config_error()
        else:
            log.info("Drone: OK")

        try:
            ec2 = boto3.client("ec2")
            ec2.describe_regions()
            log.info("AWS: OK")
        except Exception:
            log.warning("AWS: KO")

    def wait(self, build_number=None):
        """
        Waits for the build to finish to run.

        Arguments:
            build_number(int): Number of drone build.

        Returns:
            True: when job has finished
        """
        if build_number is None:
            last_build = self.last_build_info
            if last_build["finished"] != 0:
                log.info("There are no active jobs")
                return True
            build_number = last_build["number"]

        first_time = True
        while True:
            build = self.build_info(build_number)

            try:
                if build["finished"] == 0:
                    if first_time:
                        log.info(
                            "Waiting for job #{} started by a {} ".format(
                                build["number"], build["event"],
                            )
                            + "event by {}.".format(build["trigger"])
                        )
                        first_time = False
                    time.sleep(1)
                    continue
                log.info(
                    "Job #{} has finished with status {}".format(
                        build["number"], build["status"],
                    )
                )
            except KeyError:
                log.info("Job #{} has not started yet".format(build_number))
            return True
