from unittest.mock import patch
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl
import json
from krogon import krogon
from krogon import config

project_id = "project1"
service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))


def test_can_execute_steps():
    def _run_dsl(_args):
        step1 = lambda: dict(exec=lambda _: ("success", "step1 completed"))
        step2 = lambda: dict(exec=lambda _: ("success", "step2 completed"))
        step3 = lambda: dict(exec=lambda _: ("success", "step3 completed"))

        result = krogon(
            run_steps=[step1(), step2(), step3()],
            for_config=config(project_id, service_account_b64)
        )

        assert result == ('success', ['step1 completed', 'step2 completed', 'step3 completed'])

    mock_krogon_dsl(_run_dsl)


def test_can_short_circuit_on_failed_step():
    def _run_dsl(_args):
        step1 = lambda: dict(exec=lambda _: ("success", "step1 completed"))
        step2 = lambda: dict(exec=lambda _: ("failure", "step2Error"))
        step3 = lambda: dict(exec=lambda _: ("success", "step3 completed"))

        with patch('sys.exit'):
            result = krogon(
                run_steps=[step1(), step2(), step3()],
                for_config=config(project_id, service_account_b64)
            )

        assert result == ('failure', "step2Error")

    mock_krogon_dsl(_run_dsl)
