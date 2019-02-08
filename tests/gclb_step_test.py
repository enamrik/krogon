from krogon.krogon import Krogon
from krogon.config import Config
from base64 import b64encode
from krogon.steps.gclb import GclbStep
from krogon.steps.steps import steps
from tests.helpers import MockLogger, MockGCloud, MockFileSystem, MockOsSystem
import krogon.either as E
import tests.helpers.assert_either as e
import json


def test_can_run_gclb_step():
    project_id = "project1"
    config = Config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')))
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()

    gclb_name = 'someGclb'
    gclb_ip = 'address: 127.0.0.1'
    create_gclb_address = os_system.mock_create_gclb_address(gclb_name, return_value=E.Success())
    describe_gclb_address= os_system.mock_describe_gclb_address(gclb_name,
                                                                return_values=[E.Failure(''), E.Success(gclb_ip)])

    cluster_configs = ['/cluster-1-kubeconfig.yaml', '/cluster-2-kubeconfig.yaml']
    file_system.mock_glob_kubeconfigs(cluster_configs)
    clusters = ['cluster-1', 'cluster-2']
    gen_kube_config_c1 = os_system.mock_create_kube_config('cluster-1', return_value=E.Success())
    gen_kube_config_c2 = os_system.mock_create_kube_config('cluster-2', return_value=E.Success())
    flatten_cluster_configs = os_system.mock_flatten_cluster_configs(cluster_configs, return_value=E.Success())
    create_gclb_clusters = os_system.mock_create_gclb_clusters(gclb_name, project_id, return_value=E.Success())

    step = GclbStep(gclb_name=gclb_name, clusters=clusters)
    result = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock())\
        .exec(config, steps(step))

    e.assert_that(result).succeeded()
    create_gclb_address.expected_to_have_been_called()
    describe_gclb_address.expected_to_have_been_called()
    gen_kube_config_c1.expected_to_have_been_called()
    gen_kube_config_c2.expected_to_have_been_called()
    flatten_cluster_configs.expected_to_have_been_called()
    create_gclb_clusters.expected_to_have_been_called()


def test_wont_create_gclb_if_it_exists():
    project_id = "project1"
    config = Config(project_id, b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')))
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()

    gclb_name = 'someGclb'
    gclb_ip = 'address: 127.0.0.1'
    create_gclb_address = os_system.mock_create_gclb_address(gclb_name, return_value=E.Success())
    describe_gclb_address = os_system.mock_describe_gclb_address(gclb_name, return_values=[E.Success(gclb_ip)])

    cluster_configs = ['/cluster-1-kubeconfig.yaml', '/cluster-2-kubeconfig.yaml']
    file_system.mock_glob_kubeconfigs(cluster_configs)
    clusters = ['cluster-1', 'cluster-2']
    gen_kube_config_c1 = os_system.mock_create_kube_config('cluster-1', return_value=E.Success())
    gen_kube_config_c2 = os_system.mock_create_kube_config('cluster-2', return_value=E.Success())
    flatten_cluster_configs = os_system.mock_flatten_cluster_configs(cluster_configs, return_value=E.Success())
    create_gclb_clusters = os_system.mock_create_gclb_clusters(gclb_name, project_id, return_value=E.Success())

    step = GclbStep(gclb_name=gclb_name, clusters=clusters)
    result = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock()) \
        .exec(config, steps(step))

    e.assert_that(result).succeeded()
    create_gclb_address.expected_not_to_have_been_called()
    describe_gclb_address.expected_to_have_been_called()
    gen_kube_config_c1.expected_to_have_been_called()
    gen_kube_config_c2.expected_to_have_been_called()
    flatten_cluster_configs.expected_to_have_been_called()
    create_gclb_clusters.expected_to_have_been_called()

