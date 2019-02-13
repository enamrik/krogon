from krogon.config import config
from base64 import b64encode
from krogon.steps.deploy import deploy
from krogon.steps.steps import steps
from tests.helpers.mock_gcloud import create_mock_http_error
from tests.helpers.mocks import RaiseException
from unittest.mock import patch
from tests.helpers.assert_diff import assert_same_dict, same_dict
from tests.helpers.mocks import MockSetup
from tests.helpers import mock_krogon_dsl
import krogon.krogon as k
import krogon.gcp.deployment_manager.deployments.gke as gke
import krogon.either as E
import krogon.yaml as yaml
import tests.helpers.assert_either as e
import json
import copy


def test_will_create_cluster():
    def _run_dsl(args):
        gcloud = args['gcloud']
        project_id = "project1"
        cluster_name = 'prod-1'
        region = 'us-east1'
        expected_stack_name = cluster_name + '-cluster-stack'
        template = _make_expected_template()
        body = {'name': expected_stack_name,
                'description': '',
                'labels': [],
                'target': {'config': {'content': yaml.dump(template)}}}

        gcloud.mock_path('deployments().get()',
                         kwargs=dict(project=project_id, deployment=expected_stack_name),
                         exec_returns=[
                             RaiseException(create_mock_http_error(status=404)),
                             {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}])

        gcloud.mock_path('deployments().insert()',
                         kwargs=dict(project=project_id,
                                     body=MockSetup.match(lambda x: _compare_body(x, body))),
                         exec_returns=[{'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'insert'}}])

        result = k.krogon(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region))
            )
        )
        template = gcloud.client.deployments().insert.setup(0).call_at(0)['kwargs']['body']
        yaml_template = yaml.load(template['target']['config']['content'])
        expected_template = _make_expected_template()

        assert_same_dict(yaml_template, expected_template)
        e.assert_that(result).succeeded()

    mock_krogon_dsl(_run_dsl)


def test_will_update_cluster():
    def _run_dsl(args):
        gcloud = args['gcloud']
        project_id = "project1"
        cluster_name = 'prod-1'
        region = 'us-east1'
        expected_stack_name = cluster_name + '-cluster-stack'
        fingerprint = 'someFingerprint'
        template = _make_expected_template()
        body = {'name': expected_stack_name,
                'description': '',
                'labels': [],
                'target': {'config': {'content': yaml.dump(template)}},
                'fingerprint': fingerprint
                }

        gcloud.mock_path('deployments().update()',
                         kwargs=dict(project=project_id,
                                     deployment=expected_stack_name,
                                     body=MockSetup.match(lambda x: _compare_body(x, body))),
                         exec_returns=[{
                             'fingerprint': fingerprint,
                             'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}
                         }])

        result = k.krogon(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region))
            )
        )
        template = gcloud.client.deployments().update.setup(0).call_at(0)['kwargs']['body']
        yaml_template = yaml.load(template['target']['config']['content'])
        expected_template = _make_expected_template()
        assert_same_dict(yaml_template, expected_template)
        e.assert_that(result).succeeded()

    mock_krogon_dsl(_run_dsl)


def test_can_create_cluster_with_istio_addon():
    def _run_dsl(args):
        gcloud = args['gcloud']
        os_system = args['os_system']
        project_id = "project1"
        istio_version = '1.0.5'
        cluster_name = 'prod-1'
        region = 'us-east1'
        gateway_type = 'LoadBalancer'
        expected_stack_name = cluster_name + '-cluster-stack'

        body = {'name': expected_stack_name,
                'description': '',
                'labels': [],
                'target': {'config': {'content': yaml.dump(_make_expected_template())}}}

        gcloud.mock_path(
            'deployments().get()',
            kwargs=dict(project=project_id, deployment=expected_stack_name),
            exec_returns=[
                RaiseException(create_mock_http_error(status=404)),
                {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}])

        gcloud.mock_path(
            'deployments().insert()',
            kwargs=dict(project=project_id,
                        body=MockSetup.match(lambda x: _compare_body(x, body))),
            exec_returns=[{'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'insert'}}])

        create_kube_config = os_system.mock_create_kube_config(cluster_name, return_value=E.Success())
        download_istio = os_system.mock_download_istio(istio_version, return_value=E.Success())
        install_istio = os_system.mock_install_istio(istio_version, cluster_name, gateway_type,
                                                     auto_sidecar_injection=True, return_value=E.Success())
        install_istio_gateway = os_system.mock_install_istio_gateway(cluster_name, return_value=E.Success())

        with patch('time.sleep', return_value=None):
            result = k.krogon(
                config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
                steps(
                    deploy(gke.cluster(
                        name=cluster_name,
                        region=region).with_istio(istio_version))
                )
            )
        template = gcloud.client.deployments().insert.setup(0).call_at(0)['kwargs']['body']
        yaml_template = yaml.load(template['target']['config']['content'])
        expected_template = _make_expected_template()

        create_kube_config.expected_to_have_been_called(exactly_times=1)
        download_istio.expected_to_have_been_called(exactly_times=1)
        install_istio.expected_to_have_been_called(exactly_times=1)
        install_istio_gateway.expected_to_have_been_called(exactly_times=1)
        assert_same_dict(yaml_template, expected_template)
        e.assert_that(result).succeeded()

    mock_krogon_dsl(_run_dsl)


def test_can_create_cluster_with_istio_addon_without_auto_inject_sidecar():
    def _run_dsl(args):
        gcloud = args['gcloud']
        os_system = args['os_system']
        project_id = "project1"
        istio_version = '1.0.5'
        cluster_name = 'prod-1'
        region = 'us-east1'
        auto_sidecar_injection = False
        gateway_type = 'NodePort'
        expected_stack_name = cluster_name + '-cluster-stack'
        body = {'name': expected_stack_name,
                'description': '',
                'labels': [],
                'target': {'config': {'content': yaml.dump(_make_expected_template())}}}

        gcloud.mock_path(
            'deployments().get()',
            kwargs=dict(project=project_id, deployment=expected_stack_name),
            exec_returns=[RaiseException(create_mock_http_error(status=404)),
                          {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}])

        gcloud.mock_path(
            'deployments().insert()',
            kwargs=dict(project=project_id,
                        body=MockSetup.match(lambda x: _compare_body(x, body))),
            exec_returns=[{'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'insert'}}])

        create_kube_config = os_system.mock_create_kube_config(cluster_name, return_value=E.Success())
        download_istio = os_system.mock_download_istio(istio_version, return_value=E.Success())
        install_istio = os_system.mock_install_istio(istio_version, cluster_name, gateway_type,
                                                     auto_sidecar_injection,
                                                     return_value=E.Success())
        install_istio_gateway = os_system.mock_install_istio_gateway(cluster_name, return_value=E.Success())

        result = k.krogon(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region).with_istio(istio_version,
                                              using_global_load_balancer=True,
                                              auto_sidecar_injection=auto_sidecar_injection))
            )
        )

        template = gcloud.client.deployments().insert.setup(0).call_at(0)['kwargs']['body']
        yaml_template = yaml.load(template['target']['config']['content'])
        expected_template = _make_expected_template()

        create_kube_config.expected_to_have_been_called(exactly_times=1)
        download_istio.expected_to_have_been_called(exactly_times=1)
        install_istio.expected_to_have_been_called(exactly_times=1)
        install_istio_gateway.expected_to_have_been_called(exactly_times=1)
        assert_same_dict(yaml_template, expected_template)
        e.assert_that(result).succeeded()

    mock_krogon_dsl(_run_dsl)


def test_can_create_cluster_with_istio_addon_with_gclb():
    def _run_dsl(args):
        gcloud = args['gcloud']
        os_system = args['os_system']
        project_id = "project1"
        istio_version = '1.0.5'
        cluster_name = 'prod-1'
        region = 'us-east1'
        gateway_type = 'NodePort'
        expected_stack_name = cluster_name + '-cluster-stack'
        body = {'name': expected_stack_name,
                'description': '',
                'labels': [],
                'target': {'config': {'content': yaml.dump(_make_expected_template())}}}

        gcloud.mock_path('deployments().get()',
                         kwargs=dict(project=project_id, deployment=expected_stack_name),
                         exec_returns=[RaiseException(create_mock_http_error(status=404)),
                                       {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}])

        gcloud.mock_path('deployments().insert()',
                         kwargs=dict(project=project_id,
                                     body=MockSetup.match(lambda x: _compare_body(x, body))),
                         exec_returns=[{'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'insert'}}])

        create_kube_config = os_system.mock_create_kube_config(cluster_name, return_value=E.Success())
        download_istio = os_system.mock_download_istio(istio_version, return_value=E.Success())
        install_istio = os_system.mock_install_istio(istio_version, cluster_name, gateway_type,
                                                     auto_sidecar_injection=True, return_value=E.Success())
        install_istio_gateway = os_system.mock_install_istio_gateway(cluster_name, return_value=E.Success())

        result = k.krogon(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region).with_istio(istio_version, using_global_load_balancer=True))
            )
        )

        template = gcloud.client.deployments().insert.setup(0).call_at(0)['kwargs']['body']
        yaml_template = yaml.load(template['target']['config']['content'])
        expected_template = _make_expected_template()

        create_kube_config.expected_to_have_been_called(exactly_times=1)
        download_istio.expected_to_have_been_called(exactly_times=1)
        install_istio.expected_to_have_been_called(exactly_times=1)
        install_istio_gateway.expected_to_have_been_called(exactly_times=1)
        assert_same_dict(yaml_template, expected_template)
        e.assert_that(result).succeeded()

    mock_krogon_dsl(_run_dsl)


def test_can_create_cluster_with_vault_addon():
    def _run_dsl(args):
        gcloud = args['gcloud']
        os_system = args['os_system']
        project_id = "project1"
        vault_token = "someVaultToken"
        vault_address = '11.11.11.1'
        vault_ca_b64 = 'c29tZXN0dWZmCg=='
        cluster_name = 'prod-1'
        region = 'us-east1'
        expected_stack_name = cluster_name + '-cluster-stack'
        body = {'name': expected_stack_name,
                'description': '',
                'labels': [],
                'target': {'config': {'content': yaml.dump(_make_expected_template())}}}

        gcloud.mock_path('deployments().get()',
                         kwargs=dict(project=project_id, deployment=expected_stack_name),
                         exec_returns=[RaiseException(create_mock_http_error(status=404)),
                                       {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}])

        gcloud.mock_path('deployments().insert()',
                         kwargs=dict(project=project_id,
                                     body=MockSetup.match(lambda x: _compare_body(x, body))),
                         exec_returns=[{'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'insert'}}])

        create_kube_config = os_system.mock_create_kube_config(cluster_name, return_value=E.Success())
        install_vaultingkube = os_system.mock_install_vaultingkube(
            cluster_name, vault_address, vault_token, vault_ca_b64, return_value=E.Success())

        result = k.krogon(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region).with_vault(vault_address=vault_address,
                                              vault_token=vault_token,
                                              vault_ca_b64=vault_ca_b64))
            )
        )
        template = gcloud.client.deployments().insert.setup(0).call_at(0)['kwargs']['body']
        yaml_template = yaml.load(template['target']['config']['content'])
        expected_template = _make_expected_template()

        create_kube_config.expected_to_have_been_called(exactly_times=1)
        install_vaultingkube.expected_to_have_been_called(exactly_times=1)
        assert_same_dict(yaml_template, expected_template)
        e.assert_that(result).succeeded()

    mock_krogon_dsl(_run_dsl)


def _make_expected_template():
    return {
        'resources': [{
            'name': 'prod-1',
            'properties': {
                'cluster': {
                    'addonsConfig': {'horizontalPodAutoscaling': {'disabled': False},
                                     'kubernetesDashboard': {'disabled': False}},
                    'loggingService': 'logging.googleapis.com',
                    'maintenancePolicy': {'window': {'dailyMaintenanceWindow': {'startTime': '08:00'}}},
                    'monitoringService': 'monitoring.googleapis.com',
                    'nodePools': [{'autoscaling': {'enabled': True, 'maxNodeCount': 10, 'minNodeCount': 1},
                                   'config': {'diskType': 'pd-standard', 'machineType': 'n1-standard-1',
                                              'oauthScopes': [
                                                  'https://www.googleapis.com/auth/compute',
                                                  'https://www.googleapis.com/auth/logging.write',
                                                  'https://www.googleapis.com/auth/monitoring',
                                                  'https://www.googleapis.com/auth/cloud-platform',
                                              ]},
                                   'initialNodeCount': 1,
                                   'management': {'autoRepair': True, 'autoUpgrade': True},
                                   'name': 'prod-1-node-pool'}]},
                'parent': 'projects/project1/locations/us-east1', 'projectId': 'project1'},
            'type': 'gcp-types/container-v1beta1:projects.locations.clusters'
        }]}


def _compare_body(body: dict, expected_body: dict):
    body_clone = copy.deepcopy(body)
    body_clone['target']['config']['content'] = yaml.load(body_clone['target']['config']['content'])
    expected_body_clone = copy.deepcopy(expected_body)
    expected_body_clone['target']['config']['content'] = yaml.load(expected_body_clone['target']['config']['content'])
    same, result = same_dict(body_clone, expected_body_clone)
    if not same:
        print("NOT SAME:", result)
    return same
