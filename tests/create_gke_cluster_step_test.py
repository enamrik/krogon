from krogon.krogon import Krogon
from krogon.config import config
from base64 import b64encode
from krogon.steps.deploy import deploy
from krogon.steps.steps import steps
from tests.helpers import MockLogger, MockGCloud, MockFileSystem, MockOsSystem
from tests.helpers.mock_gcloud import create_mock_http_error
from tests.helpers.mocks import RaiseException
from unittest.mock import patch
from tests.helpers.assert_diff import assert_same_dict
import krogon.gcp.deployment_manager.deployments.gke as gke
import krogon.either as E
import krogon.yaml as yaml
import tests.helpers.assert_either as e
import json


def test_will_create_cluster():
    project_id = "project1"
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()
    krogon = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock())

    cluster_name = 'prod-1'
    region = 'us-east1'
    expected_stack_name = cluster_name + '-cluster-stack'

    get_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    not_found_error = create_mock_http_error(status=404)
    gcloud.mock_deployment_method(
        gcloud.deployments_get,
        dict(project=project_id, deployment_name=expected_stack_name),
        exec_returns=[RaiseException(not_found_error), get_status])

    insert_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    dp_insert_setup = gcloud.mock_deployment_method(
        gcloud.deployments_insert,
        dict(project=project_id, deployment_name=expected_stack_name), exec_returns=[insert_status])

    with patch('time.sleep', return_value=None):
        result = krogon.exec(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region))
            )
        )
    template = dp_insert_setup.call_at(0)['kwargs']['body']
    yaml_template = yaml.load(template['target']['config']['content'])
    expected_template = _make_expected_template()

    assert_same_dict(yaml_template, expected_template)
    e.assert_that(result).succeeded()


def test_will_update_cluster():
    project_id = "project1"
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()
    krogon = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock())

    cluster_name = 'prod-1'
    region = 'us-east1'
    expected_stack_name = cluster_name + '-cluster-stack'

    status = {
        'fingerprint': 'someFingerprint',
        'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}
    }

    dp_update_setup = gcloud.mock_deployment_method(
        gcloud.deployments_update,
        dict(project=project_id, deployment_name=expected_stack_name), exec_returns=[status])

    with patch('time.sleep', return_value=None):
        result = krogon.exec(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region))
            )
        )
    template = dp_update_setup.call_at(0)['kwargs']['body']
    yaml_template = yaml.load(template['target']['config']['content'])
    expected_template = _make_expected_template()

    assert_same_dict(yaml_template, expected_template)
    e.assert_that(result).succeeded()


def test_can_create_cluster_with_istio_addon_without_gclb():
    project_id = "project1"
    istio_version = '1.0.5'
    cluster_name = 'prod-1'
    region = 'us-east1'
    gateway_type = 'LoadBalancer'
    expected_stack_name = cluster_name + '-cluster-stack'
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()
    krogon = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock())

    get_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    not_found_error = create_mock_http_error(status=404)
    gcloud.mock_deployment_method(
        gcloud.deployments_get,
        dict(project=project_id, deployment_name=expected_stack_name),
        exec_returns=[RaiseException(not_found_error), get_status])

    insert_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    dp_insert_setup = gcloud.mock_deployment_method(
        gcloud.deployments_insert,
        dict(project=project_id, deployment_name=expected_stack_name), exec_returns=[insert_status])

    create_kube_config = os_system.mock_create_kube_config(cluster_name, return_value=E.Success())
    download_istio = os_system.mock_download_istio(istio_version, return_value=E.Success())
    install_istio = os_system.mock_install_istio(istio_version, cluster_name, gateway_type, return_value=E.Success())
    install_istio_gateway = os_system.mock_install_istio_gateway(cluster_name, return_value=E.Success())

    with patch('time.sleep', return_value=None):
        result = krogon.exec(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region).with_istio(istio_version, using_global_load_balancer=False))
            )
        )
    template = dp_insert_setup.call_at(0)['kwargs']['body']
    yaml_template = yaml.load(template['target']['config']['content'])
    expected_template = _make_expected_template()

    create_kube_config.expected_to_have_been_called(exactly_times=1)
    download_istio.expected_to_have_been_called(exactly_times=1)
    install_istio.expected_to_have_been_called(exactly_times=1)
    install_istio_gateway.expected_to_have_been_called(exactly_times=1)
    assert_same_dict(yaml_template, expected_template)
    e.assert_that(result).succeeded()


def test_can_create_cluster_with_istio_addon_with_gclb():
    project_id = "project1"
    istio_version = '1.0.5'
    cluster_name = 'prod-1'
    region = 'us-east1'
    gateway_type = 'NodePort'
    expected_stack_name = cluster_name + '-cluster-stack'
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()
    krogon = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock())

    get_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    not_found_error = create_mock_http_error(status=404)
    gcloud.mock_deployment_method(
        gcloud.deployments_get,
        dict(project=project_id, deployment_name=expected_stack_name),
        exec_returns=[RaiseException(not_found_error), get_status])

    insert_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    dp_insert_setup = gcloud.mock_deployment_method(
        gcloud.deployments_insert,
        dict(project=project_id, deployment_name=expected_stack_name), exec_returns=[insert_status])

    create_kube_config = os_system.mock_create_kube_config(cluster_name, return_value=E.Success())
    download_istio = os_system.mock_download_istio(istio_version, return_value=E.Success())
    install_istio = os_system.mock_install_istio(istio_version, cluster_name, gateway_type, return_value=E.Success())
    install_istio_gateway = os_system.mock_install_istio_gateway(cluster_name, return_value=E.Success())

    with patch('time.sleep', return_value=None):
        result = krogon.exec(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region).with_istio(istio_version, using_global_load_balancer=True))
            )
        )
    template = dp_insert_setup.call_at(0)['kwargs']['body']
    yaml_template = yaml.load(template['target']['config']['content'])
    expected_template = _make_expected_template()

    create_kube_config.expected_to_have_been_called(exactly_times=1)
    download_istio.expected_to_have_been_called(exactly_times=1)
    install_istio.expected_to_have_been_called(exactly_times=1)
    install_istio_gateway.expected_to_have_been_called(exactly_times=1)
    assert_same_dict(yaml_template, expected_template)
    e.assert_that(result).succeeded()


def test_can_create_cluster_with_vault_addon():
    project_id = "project1"
    vault_token = "someVaultToken"
    vault_address = '11.11.11.1'
    vault_ca_b64 = 'c29tZXN0dWZmCg=='
    cluster_name = 'prod-1'
    region = 'us-east1'
    expected_stack_name = cluster_name + '-cluster-stack'
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()
    krogon = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock())

    get_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    not_found_error = create_mock_http_error(status=404)
    gcloud.mock_deployment_method(
        gcloud.deployments_get,
        dict(project=project_id, deployment_name=expected_stack_name),
        exec_returns=[RaiseException(not_found_error), get_status])

    insert_status = {'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
    dp_insert_setup = gcloud.mock_deployment_method(
        gcloud.deployments_insert,
        dict(project=project_id, deployment_name=expected_stack_name), exec_returns=[insert_status])

    create_kube_config = os_system.mock_create_kube_config(cluster_name, return_value=E.Success())
    install_vaultingkube = os_system.mock_install_vaultingkube(
        cluster_name, vault_address, vault_token, vault_ca_b64, return_value=E.Success())

    with patch('time.sleep', return_value=None):
        result = krogon.exec(
            config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))),
            steps(
                deploy(gke.cluster(
                    name=cluster_name,
                    region=region).with_vault(vault_address=vault_address,
                                              vault_token=vault_token,
                                              vault_ca_b64=vault_ca_b64))
            )
        )
    template = dp_insert_setup.call_at(0)['kwargs']['body']
    yaml_template = yaml.load(template['target']['config']['content'])
    expected_template = _make_expected_template()

    create_kube_config.expected_to_have_been_called(exactly_times=1)
    install_vaultingkube.expected_to_have_been_called(exactly_times=1)
    assert_same_dict(yaml_template, expected_template)
    e.assert_that(result).succeeded()


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
