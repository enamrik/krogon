import json
import krogon.file_system as f
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl
from tests.helpers.mock_file_system import MockFileSystem, find_write_template_calls
from krogon import run_in_cluster, gke_conn
from krogon.k8s import from_file
from python_mock import PyMock

fs = f.file_system()


def test_can_exec_yaml_file():
    def _run_dsl(args):
        mock_fs: MockFileSystem = args['file_system']
        project_id = "project1"
        cluster_name = 'prod-us-east1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))
        service_defaults_path = '{}/service_defaults.yaml'.format(fs.dirname(__file__))
        PyMock.mock(mock_fs.get_mock().read,
                    call_fake=lambda path:
                    read(path['args'][0])
                    if path['args'][0] == service_defaults_path
                    else '')

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                from_file(service_defaults_path)
            ]
        )

        yamls = find_write_template_calls(mock_fs)
        assert yamls[0]['kind'] == 'Service'

    mock_krogon_dsl(_run_dsl)


def read(file_path: str) -> str:
    with open(file_path) as f:
        return f.read()
