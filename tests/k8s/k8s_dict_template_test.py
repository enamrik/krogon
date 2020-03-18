import json
import krogon.file_system as f
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl
from krogon import run_in_cluster, gke_conn
from krogon.k8s import from_dicts
from tests.helpers.mock_file_system import find_write_template_calls, MockFileSystem

fs = f.file_system()


def test_can_exec_yaml_as_dict():
    def _run_dsl(args):
        mock_fs: MockFileSystem = args['file_system']
        project_id = "project1"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))
        cluster_name = 'prod-us-east1'

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                from_dicts([{"kind": "Service"}])
            ]
        )

        yamls = find_write_template_calls(mock_fs)
        assert yamls[0]['kind'] == 'Service'

    mock_krogon_dsl(_run_dsl)
