import krogon.either as E
import json
from krogon import run_in_cluster, gke_conn
from krogon.k8s import secret
from tests.helpers.mock_file_system import find_write_template_calls, MockFileSystem
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode, b64decode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_generate_secret_template():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        secret_name = 'test-secret'
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
                secret(secret_name, data={'key1': 'someValue'})
            ]
        )
        yamls = find_write_template_calls(fs)
        assert yamls[0]['kind'] == 'Secret'
        assert yamls[0]['metadata']['name'] == secret_name
        assert b64decode(yamls[0]['data']['key1'].encode('utf-8')).decode('utf-8') == 'someValue'

    mock_krogon_dsl(_run_dsl)
