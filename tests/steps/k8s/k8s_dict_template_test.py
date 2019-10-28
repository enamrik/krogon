import json
import krogon.file_system as f
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, from_dicts
from krogon.yaml import load_all

fs = f.file_system()


def test_can_exec_yaml_as_dict():
    def _run_dsl(_args):
        project_id = "project1"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        from_dicts([{"kind": "Service"}])
                    ]
                )
            ],
            for_config=config(project_id, service_account_b64, output_template=True)
        )
        assert load_all(result[0][0])[0]['kind'] == 'Service'

    mock_krogon_dsl(_run_dsl)
