import krogon.either as E
import json
from krogon import config, run_in_cluster, gke_conn
from krogon.k8s import volume_claim
from tests.helpers.mock_file_system import MockFileSystem, find_write_template_calls
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_generate_persistent_volume_claim_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args['file_system']
        project_id = "project1"
        claim_name = 'test-volume'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                volume_claim(claim_name)
            ]
        )

        yamls = find_write_template_calls(fs)
        assert yamls[0] == {'apiVersion': 'v1',
                            'kind': 'PersistentVolumeClaim',
                            'metadata': {'name': 'test-volume'},
                            'spec': {'accessModes': ['ReadWriteOnce'],
                                     'resources': {'requests': {'storage': '2Gi'}},
                                     'volumeMode': 'Filesystem'}}

    mock_krogon_dsl(_run_dsl)


def test_can_set_persistent_volume_claim_size_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args['file_system']
        project_id = "project1"
        claim_name = 'test-volume'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                volume_claim(claim_name).with_size('5Gi')
            ]
        )

        yamls = find_write_template_calls(fs)
        assert yamls[0] == {'apiVersion': 'v1',
                            'kind': 'PersistentVolumeClaim',
                            'metadata': {'name': 'test-volume'},
                            'spec': {'accessModes': ['ReadWriteOnce'],
                                     'resources': {'requests': {'storage': '5Gi'}},
                                     'volumeMode': 'Filesystem'}}

    mock_krogon_dsl(_run_dsl)
