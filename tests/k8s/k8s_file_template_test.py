import json
import krogon.file_system as f
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl
from tests.helpers.mock_file_system import MockFileSystem
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, yaml_file
from krogon.yaml import load_all
from python_mock import PyMock

fs = f.file_system()


def test_can_exec_yaml_file():
    def _run_dsl(args):
        project_id = "project1"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))
        service_defaults_path = '{}/service_defaults.yaml'.format(fs.dirname(__file__))
        mock_fs: MockFileSystem = args['file_system']
        PyMock.mock(mock_fs.get_mock().read,
                    call_fake=lambda path:
                    read(path['args'][0])
                    if path['args'][0] == service_defaults_path
                    else '')

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        yaml_file(service_defaults_path)
                    ]
                )
            ],
            for_config=config(project_id, service_account_b64, output_template=True)
        )
        assert load_all(result[0][0])[0]['kind'] == 'Service'

    mock_krogon_dsl(_run_dsl)


def read(file_path: str) -> str:
    with open(file_path) as f:
        return f.read()
