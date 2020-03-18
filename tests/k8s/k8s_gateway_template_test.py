import krogon.either as E
import json
import sys
from unittest.mock import patch
from krogon import run_in_cluster, gke_conn
from krogon import config
from krogon.k8s import gateway_mapping
from tests.helpers.mock_file_system import MockFileSystem, find_write_template_calls
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_create_istio_virtual_service():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args['file_system']
        project_id = "project1"
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl(cluster_name, 'get mappings', E.failure('No such resource'))
        os.mock_kubectl(cluster_name, 'get virtualservices', E.success())

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                gateway_mapping('api', 'api.com', 'api.default.svc.cluster.local')
            ]
        )

        yamls = find_write_template_calls(fs)
        output_yaml = yamls[0]
        assert output_yaml == {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'VirtualService',
            'metadata': {'name': 'api-vs'},
            'spec': { 'hosts': ['api.com'], 'gateways': ['cluster-gateway'],
                      'http': [{'route': [{'destination': {'host': 'api.default.svc.cluster.local'}}]}]}}

    mock_krogon_dsl(_run_dsl)


def test_can_create_ambassador_mapping():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl(cluster_name, 'get mappings', E.success())
        os.mock_kubectl(cluster_name, 'get virtualservices', E.failure('No such resource'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                gateway_mapping('api', 'api.com', 'api.default.svc.cluster.local')
            ]
        )
        yamls = find_write_template_calls(fs)
        output_yaml = yamls[0]
        assert output_yaml == {
            'apiVersion': 'getambassador.io/v1',
            'kind': 'Mapping', 'metadata': {'name': 'api-mapping'},
            'spec': {'host': 'api.com', 'prefix': '/', 'service': 'api.default.svc.cluster.local'}}

    mock_krogon_dsl(_run_dsl)


def test_can_create_ambassador_catch_all_mapping():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl(cluster_name, 'get mappings', E.success())
        os.mock_kubectl(cluster_name, 'get virtualservices', E.failure('No such resource'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                gateway_mapping('api', '*', 'api.default.svc.cluster.local')
            ]
        )
        yamls = find_write_template_calls(fs)
        output_yaml = yamls[0]
        assert output_yaml == {
            'apiVersion': 'getambassador.io/v1',
            'kind': 'Mapping', 'metadata': {'name': 'api-mapping'},
            'spec': {'prefix': '/', 'service': 'api.default.svc.cluster.local'}}

    mock_krogon_dsl(_run_dsl)


def test_will_fail_if_neither_istio_or_ambassador_configured_in_cluster():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl(cluster_name, 'get mappings', E.failure('No such resource'))
        os.mock_kubectl(cluster_name, 'get virtualservices', E.failure('No such resource'))

        with patch.object(sys, "exit") as mock_exit:
            _, error = run_in_cluster(
                conn=gke_conn(cluster_name, project_id, service_account_b64),
                templates=[
                    gateway_mapping('api', 'api.com', 'api.default.svc.cluster.local')
                ]
            )
            assert mock_exit.call_args[0][0] == 1
            assert str(error.caught_error) == 'Unsupported gateway'

    mock_krogon_dsl(_run_dsl)
