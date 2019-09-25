import krogon.file_system as f
import krogon.either as E
from python_mock import PyMock, assert_that
import json
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, micro_service
from tests.helpers.mock_os_system import MockOsSystem
from tests.helpers.mock_file_system import MockFileSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_execute_service_yaml_with_defaults():
    fs = f.file_system()
    service_defaults = fs.read('{}/service_defaults.yaml'.format(fs.dirname(__file__)))

    def _run_dsl(args):
        project_id = "project1"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service("test-service", "test-service:1.0.0", 3000)
                    ]
                )
            ],
            for_config=config(project_id, service_account_b64, output_template=True)
        )
        assert result[0] == service_defaults

    mock_krogon_dsl(_run_dsl)


def test_can_generate_service_yaml_with_defaults():
    fs = f.file_system()
    service_defaults = fs.read('{}/service_defaults.yaml'.format(fs.dirname(__file__)))

    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
        project_id = "project1"
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service("test-service", "test-service:1.0.0", 3000)
                    ]
                )
            ],
            for_config=config(project_id, service_account_b64)
        )
        template_str = PyMock.calls(fs.file_system.with_temp_file)[0]['kwargs']['contents']
        assert template_str == service_defaults

    mock_krogon_dsl(_run_dsl)
