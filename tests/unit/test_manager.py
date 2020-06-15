from botocore.exceptions import ClientError, NoRegionError
from drode.configuration import Config
from drode.manager import DeploymentManager
from unittest.mock import call, patch
from drode.version import __version__

import datetime
import os
import pytest


class TestDeploymentManager:
    """
    Class to test the DeploymentManager object.

    Public attributes:
        log (mock): logging mock
        log_debug (mock): log.debug mock
        manager (DeploymentManager object): DeploymentManager object to test
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.log_patch = patch('drode.manager.log', autospect=True)
        self.log = self.log_patch.start()
        self.time_patch = patch('drode.manager.time', autospect=True)
        self.time = self.time_patch.start()
        self.boto_patch = patch('drode.manager.boto3', autospect=True)
        self.boto = self.boto_patch.start()
        self.print_patch = patch('drode.manager.print', autospect=True)
        self.print = self.print_patch.start()

        # Values set as environmental variables in `tests/conftest.py`.
        self.url = 'https://drone.url'
        self.token = 'drone_token'

        self.manager = DeploymentManager()
        self.manager.config.data = {
            'projects': {
                'project_1': {
                    'pipeline': 'owner/repository',
                }
            }
        }

        yield 'setup'

        self.boto_patch.stop()
        self.log_patch.stop()
        self.print_patch.stop()
        self.time_patch.stop()

    def test_drone_config_is_loaded_from_env_variable(self):
        assert self.manager.drone_url == self.url
        assert self.manager.drone_token == self.token

    def test_drode_raise_drone_config_error_outputs_expected(self):
        with pytest.raises(SystemExit):
            self.manager._raise_drone_config_error()

        self.log.error.assert_called_once_with(
            'There was a problem contacting the Drone server. \n\n'
            '\t  Please make sure the DRONE_SERVER and DRONE_TOKEN '
            'environmental variables are set. \n'
            '\t  https://docs.drone.io/cli/configure/'
        )

    def test_drode_handles_drone_misconfiguration(self):
        del os.environ['DRONE_TOKEN']
        with patch(
            'drode.manager.DeploymentManager._raise_drone_config_error') as \
                errorMock:
            DeploymentManager()

            errorMock.assert_called()

        os.environ['DRONE_TOKEN'] = 'drone_token'

    def test_config_attribute_exists(self):
        assert isinstance(self.manager.config, Config)

    def test_builds_url_property_defined(self):
        assert self.manager.builds_url == \
            '{}/api/repos/owner/repository/builds'.format(self.url)

    def test_get_returns_requests_object(self, requests_mock):
        requests_mock.get('http://url', text='hi')

        assert self.manager.get('http://url').text == 'hi'
        assert requests_mock.request_history[0].method == 'GET'

    def test_get_is_called_with_bearer_token_external(self, requests_mock):
        requests_mock.get('http://url', text='hi')

        self.manager.get('http://url')

        assert requests_mock.request_history[0].headers['Authorization'] == \
            'Bearer drone_token'

    def test_get_accepts_post(self, requests_mock):
        requests_mock.post('http://url', text='hi')

        self.manager.get('http://url', 'post')

        assert requests_mock.request_history[0].method == 'POST'

    def test_get_handles_url_errors(self, requests_mock):
        requests_mock.get('http://url', status_code=401)

        with pytest.raises(SystemExit):
            self.manager.get('http://url')

        self.log.error.assert_called_once_with(
            '{} error while trying to access {}'.format('401', 'http://url')
        )

    def test_wait_waits_for_the_build_to_finish(self, requests_mock):
        # The first request shows that it hasn't finished but the second has.
        response_json_1 = {
            "id": 879,
            "status": "success",
            "number": "209",
            "trigger": "trigger_author",
            "event": "promote",
            "message": "commit message",
            "source": "master",
            "after": "9d924b358sflwegk30bbfa0571f754ec2a0b7457",
            "target": "master",
            "author_name": "Commit Author",
            "deploy_to": "production",
            "started": 1591128214,
            "finished": 0,
            "stages": []
        }
        response_json_2 = response_json_1.copy()
        response_json_2['finished'] = 1591129124

        requests_mock.get(
            '{}/api/repos/owner/repository/builds/274'.format(self.url),
            [
                {'json': response_json_1, 'status_code': 200},
                {'json': response_json_2, 'status_code': 200}
            ]
        )

        result = self.manager.wait(274)

        self.time.sleep.assert_called_once_with(1)
        assert result

        expected_calls = [
            call(
                'Waiting for job #209 started by a promote event '
                'by trigger_author.'
            ),
            call('Job #209 has finished with status success'),
        ]
        for message in expected_calls:
            assert message in self.log.info.mock_calls

    def test_wait_defaults_to_last_build(self, requests_mock):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds'.format(self.url),
            json=[
                {
                    "id": 882,
                    "number": 209,
                    "finished": 0,
                },
                {
                    "id": 881,
                    "number": 208,
                    "finished": 1,
                },
            ]
        )
        requests_mock.get(
            '{}/api/repos/owner/repository/builds/209'.format(self.url),
            [
                {'json': {"finished": 1591129124}, 'status_code': 200}
            ]
        )
        result = self.manager.wait()

        assert result

    def test_wait_skips_build_query_if_list_is_finished(self, requests_mock):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds'.format(self.url),
            json=[{
                "id": 882,
                "number": 209,
                "finished": 1591197904,
            }],
        )

        result = self.manager.wait()

        self.log.info.assert_called_once_with('There are no active jobs')
        assert result

    def test_wait_handles_unstarted_builds(self, requests_mock):
        # They don't have the finished key
        requests_mock.get(
            '{}/api/repos/owner/repository/builds/209'.format(self.url),
            json={
                "id": 882,
                "number": 209,
            },
        )

        result = self.manager.wait(209)

        self.log.info.assert_called_once_with('Job #209 has not started yet')
        assert result

    def test_promote_launches_promote_drone_job_build_num(self, requests_mock):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds/172'.format(self.url),
            json={
                "id": 882,
                "number": 172,
                "status": 'success',
                "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                "target": "master",
                "event": "push",
                "message": "updated README",
            },
        )

        promote_url = \
            '{}/api/repos/owner/repository/builds/'.format(self.url) + \
            '{}/promote?target={}'.format(172, 'production')
        requests_mock.post(
            promote_url,
            json={
                "id": 100207,
                "number": 174,
                "parent": 172,
                "status": "pending",
                "event": "promote",
                "message": "updated README",
                "before": "e3320539a4c03ccfda992641646deb67d8bf98f3",
                "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                "source": "master",
                "target": "master",
                "author_login": "octocat",
                "author_name": "The Octocat",
                "sender": "bradrydzewski",
                "started": 0,
                "finished": 0,
                "stages": []

            }
        )

        with patch('drode.manager.DeploymentManager.ask', return_value=True):
            response = self.manager.promote(172, 'production')

        assert requests_mock.request_history[-1].method == 'POST'
        assert requests_mock.request_history[-1].url == promote_url
        self.log.info.assert_called_with('Job #174 has started.')
        assert response == 174

    def test_promote_doesnt_promote_failed_job(self, requests_mock):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds/172'.format(self.url),
            json={
                "id": 882,
                "number": 172,
                "status": 'killed',
            },
        )

        with pytest.raises(SystemExit):
            self.manager.promote(172, 'production')

        self.log.error.assert_called_once_with(
            "You can't promote job #{} to {} as it's status is {}".format(
                172,
                'production',
                'killed',
            )
        )

    def test_last_successful_searches_master_and_push_events_by_default(
        self,
        requests_mock
    ):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds'.format(self.url),
            json=[
                {
                    "id": 882,
                    "number": 209,
                    "finished": 1,
                    "status": "success",
                    "source": "feat/1",
                    "target": "feat/1",
                },
                {
                    "id": 881,
                    "number": 208,
                    "finished": 1,
                    "status": "success",
                    "source": "master",
                    "target": "master",
                    "event": "promote",
                },
                {
                    "id": 880,
                    "number": 207,
                    "finished": 1,
                    "status": "success",
                    "source": "master",
                    "target": "master",
                    "event": "push",
                },
            ]
        )

        assert self.manager.last_success_build_info()['number'] == 207

    def test_last_successful_handles_no_result(self, requests_mock):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds'.format(self.url),
            json=[
                {
                    "id": 882,
                    "number": 209,
                    "finished": 1,
                    "status": "failure",
                    "source": "feat/1",
                    "target": "feat/1",
                },
            ]
        )

        with pytest.raises(SystemExit):
            self.manager.last_success_build_info()

        self.log.error.assert_called_once_with(
            'There are no successful jobs with target branch master'
        )

    def test_promote_launches_last_successful_master_job_if_none(
        self,
        requests_mock
    ):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds'.format(self.url),
            json=[
                {
                    "id": 882,
                    "number": 209,
                    "finished": 1,
                    "source": "feat/1",
                    "target": "feat/1",
                    "status": "success",
                    "event": "push",
                },
                {
                    "id": 881,
                    "number": 208,
                    "finished": 1,
                    "source": "master",
                    "target": "master",
                    "status": "success",
                    "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                    "message": "updated README",
                    "event": "push",
                },
            ]
        )

        promote_url = \
            '{}/api/repos/owner/repository/builds/'.format(self.url) + \
            '{}/promote?target={}'.format(208, 'production')

        requests_mock.post(
            promote_url,
            json={
                "id": 100207,
                "number": 209,
                "parent": 208,
                "status": "pending",
                "event": "promote",
                "message": "updated README",
                "before": "e3320539a4c03ccfda992641646deb67d8bf98f3",
                "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
                "source": "master",
                "target": "master",
                "started": 0,
                "finished": 0,
                "stages": []
            }
        )

        with patch('drode.manager.DeploymentManager.ask', return_value=True):
            response = self.manager.promote(None, 'production')
        assert response == 209

    def test_ask_returns_true_if_user_anwers_yes(self):
        with patch('builtins.input', return_value='yes'):
            assert self.manager.ask('Do you want to continue? ([y]/n): ')

        with patch('builtins.input', return_value='y'):
            assert self.manager.ask('Do you want to continue? ([y]/n): ')

    def test_ask_returns_false_otherwise(self):
        with patch('builtins.input', return_value='no'):
            assert not self.manager.ask('Do you want to continue? ([y]/n): ')

    def test_promote_asks_user_for_confirmation(self, requests_mock):

        promote_url = \
            '{}/api/repos/owner/repository/builds/'.format(self.url) + \
            '{}/promote?target={}'.format(208, 'production')

        requests_mock.post(
            promote_url,
            json={
                "id": 100207,
                "number": 209,
                "parent": 208,
                "status": "pending",
                "event": "promote",
                "source": "master",
                "target": "master",
                "started": 0,
                "finished": 0,
                "stages": []
            }
        )

        requests_mock.get(
            '{}/api/repos/owner/repository/builds/208'.format(self.url),
            json={
                "id": 882,
                "number": 208,
                "status": 'success',
                "message": "updated README",
                "before": "e3320539a4c03ccfda992641646deb67d8bf98f3",
                "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
            },
        )

        with patch('drode.manager.DeploymentManager.ask', return_value=True):
            self.manager.promote(208, 'production')

        expected_calls = [
            call(
                "You're about to promote job #{} ".format(208) +
                'of the project {} to {}'.format('project_1', 'production')
            ),
            call('With commit {}: {}'.format('9fc1ad6e', 'updated README')),
            call('Job #209 has started.'),
        ]
        for message in expected_calls:
            assert message in self.log.info.mock_calls

    def test_promote_does_nothing_if_user_doesnt_confirmation(
        self,
        requests_mock
    ):
        requests_mock.get(
            '{}/api/repos/owner/repository/builds/208'.format(self.url),
            json={
                "id": 882,
                "number": 208,
                "status": 'success',
                "message": "updated README",
                "before": "e3320539a4c03ccfda992641646deb67d8bf98f3",
                "after": "9fc1ad6ebf12462f3f9773003e26b4c6f54a772e",
            },
        )

        with patch('drode.manager.DeploymentManager.ask', return_value=False):
            self.manager.promote(208, 'production')

        assert 'Job #209 has started.' not in self.log.info.mock_calls

    def test_verify_returns_expected_info_if_working(self, requests_mock):
        requests_mock.get('{}/api/user/repos'.format(self.url))

        self.manager.verify()

        expected_calls = [
            call('Drode: {}'.format(__version__)),
            call('Drone: OK'),
            call('AWS: OK'),
        ]
        for message in expected_calls:
            assert message in self.log.info.mock_calls

    def test_verify_fails_if_drone_is_not_configured(self, requests_mock):
        requests_mock.get(
            '{}/api/user/repos'.format(self.url),
            status_code=401,
        )
        with patch(
            'drode.manager.DeploymentManager._raise_drone_config_error') as \
                errorMock:
            self.manager.verify()

            errorMock.assert_called()
        self.log.error.assert_called_with('Drone: KO')

    def test_verify_checks_aws_region(self, requests_mock):
        requests_mock.get('{}/api/user/repos'.format(self.url))
        self.boto.client.side_effect = NoRegionError()

        self.manager.verify()

        self.log.warning.assert_called_once_with('AWS: KO')

    def test_verify_checks_aws_credentials(self, requests_mock):
        requests_mock.get('{}/api/user/repos'.format(self.url))
        self.boto.client.return_value.describe_regions.side_effect = \
            ClientError

        self.manager.verify()

        self.log.warning.assert_called_once_with('AWS: KO')

    def test_print_aws_autoscaling_shows_instances_info(self):
        boto = self.boto.client.return_value
        boto.describe_auto_scaling_groups.return_value = {
            'AutoScalingGroups': [
                {
                    'AutoScalingGroupARN': 'autoscaling_arn',
                    'AutoScalingGroupName':
                        'production_autoscaling_group_name',
                    'AvailabilityZones': [
                        'us-west-1a',
                        'us-west-1b',
                        'us-west-1c'
                    ],
                    'CreatedTime': datetime.datetime(
                        2020, 5, 19, 16, 8, 26, 535000
                    ),
                    'DefaultCooldown': 300,
                    'DesiredCapacity': 2,
                    'EnabledMetrics': [],
                    'HealthCheckGracePeriod': 300,
                    'HealthCheckType': 'ELB',
                    'Instances': [
                        {
                            'AvailabilityZone': 'us-west-1d',
                            'HealthStatus': 'Healthy',
                            'InstanceId': 'i-xxxxxxxxxxxxxxxxx',
                            'LaunchConfigurationName':
                                'old-launch-config-name',
                            'LifecycleState': 'InService',
                            'ProtectedFromScaleIn': False
                        },
                    ],
                    'LaunchConfigurationName': 'launch-config-name',
                    'LoadBalancerNames': [],
                    'MaxSize': 10,
                    'MinSize': 2,
                    'NewInstancesProtectedFromScaleIn': False,
                    'ServiceLinkedRoleARN': 'servicelinkedrolearn',
                    'SuspendedProcesses': [],
                    'TargetGroupARNs': [
                        'target_group_arn'
                    ],
                    'TerminationPolicies': ['Default'],
                }
            ],
            'ResponseMetadata': {'HTTPStatusCode': 200},
        }
        boto.describe_instances.return_value = {
            'Reservations': [
                {
                    'Groups': [],
                    'Instances': [
                        {
                            'InstanceType': 't2.medium',
                            'LaunchTime': datetime.datetime(
                                2020, 6, 8, 11, 29, 27
                            ),
                            'PrivateIpAddress': '192.168.1.13',
                            'State': {'Code': 16, 'Name': 'running'},
                        }
                    ],
                }
            ],
            'ResponseMetadata': {'HTTPStatusCode': 200},
        }

        with patch('drode.manager.tabulate') as tabulateMock:
            self.manager._print_aws_autoscaling_group_info(
                'production_autoscaling_group_name'
            )

        # Status checks for autoscaling properties
        boto.describe_auto_scaling_groups.assert_called_once_with(
            AutoScalingGroupNames=['production_autoscaling_group_name']
        )

        # Status checks for ec2 instances properties
        boto.describe_instances.assert_called_once_with(
            InstanceIds=['i-xxxxxxxxxxxxxxxxx']
        )

        # Status formats the data in a table
        expected_headers = [
            'Instance',
            'IP',
            'Status',
            'Created',
            'LaunchConfiguration',
        ]
        expected_data = [[
            'i-xxxxxxxxxxxxxxxxx',
            '192.168.1.13',
            'Healthy/InService',
            '2020-06-08T11:29',
            'old-launch-config-name',
        ]]
        tabulateMock.assert_called_once_with(
            expected_data,
            headers=expected_headers,
            tablefmt='simple',
        )

        # Status prints the table
        expected_calls = [
            call('Active LaunchConfiguration: launch-config-name'),
            call(tabulateMock.return_value),
        ]

        for message in expected_calls:
            assert message in self.print.mock_calls

    def test_print_aws_autoscaling_handles_unexistent(self):
        boto = self.boto.client.return_value
        boto.describe_auto_scaling_groups.return_value = {
            'AutoScalingGroups': [],
            'ResponseMetadata': {'HTTPStatusCode': 200},
        }

        with pytest.raises(SystemExit):
            self.manager._print_aws_autoscaling_group_info(
                'non_existent_autoscaling_group'
            )
        self.log.error.assert_called_once_with(
            'There are no autoscaling groups named {}'.format(
                'non_existent_autoscaling_group'
            )
        )

    def test_status_prints_desired_information(self):
        self.manager.config.data['projects']['project_1']['aws'] = {
            'autoscaling_groups': {
                'production': 'production_autoscaling_group_name',
                'staging': 'staging_autoscaling_group_name',
            },
        }

        with patch(
            'drode.manager.DeploymentManager._print_aws_autoscaling_group_info'
        ) as awsMock:
            self.manager.status()

        for environment in ['production', 'staging']:
            assert call('{}_autoscaling_group_name'.format(environment)) in \
                awsMock.mock_calls

        expected_calls = [
            call('# Production'),
            call(),
            call('# Staging'),
        ]

        for message in expected_calls:
            assert message in self.print.mock_calls

    def test_status_handles_projects_without_environments(self):
        self.manager.config.data['projects']['project_1']['aws'] = {
            'autoscaling_groups': {
                'production': 'production_autoscaling_group_name',
            },
        }

        with patch(
            'drode.manager.DeploymentManager._print_aws_autoscaling_group_info'
        ):
            self.manager.status()

        expected_calls = [
            call('# Production'),
            call(),
            call('# Staging'),
        ]

        for message in expected_calls:
            assert message in self.print.mock_calls

    def test_status_handles_projects_without_aws_section(self):
        self.manager.status()

        expected_calls = [
            call('# Production'),
            call(),
            call('# Staging'),
        ]

        for message in expected_calls:
            assert message in self.print.mock_calls
