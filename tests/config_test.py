import json
from tests.helpers.assert_diff import assert_same_dict
from tests.helpers.mock_os_system import MockOsSystem
from unittest.mock import patch
from krogon.config import config
from base64 import b64encode, b64decode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_get_project_id_if_exits():
    def _run_dsl(_args):
        project_id = "someId"
        service_account_key = {"key": "someKey"}
        service_account_b64 = b64encode(json.dumps(service_account_key).encode('utf-8')).decode('utf-8')
        cf = config(project_id=project_id, service_account_b64=service_account_b64)
        assert cf.get_project_id() == project_id

    mock_krogon_dsl(_run_dsl)


def test_can_get_project_id_if_exits_as_env_variable():
    def _run_dsl(args):
        os: MockOsSystem = args['os_system']
        project_id = "someId"
        os.mock_get_env('KG_PROJECT_ID', return_values=[project_id])
        os.mock_get_env('KG_DELETE', return_values=["true"])
        os.mock_get_env('KG_TEMPLATE', return_values=["false"])
        service_account_key = {'key': 'someKey'}
        service_account_b64 = b64encode(json.dumps(service_account_key).encode('utf-8')).decode('utf-8')
        cf = config(service_account_b64=service_account_b64)
        assert cf.get_project_id() == project_id

    mock_krogon_dsl(_run_dsl)


def test_can_raise_error_if_project_id_missing():
    def _run_dsl(_args):
        project_id = None
        service_account_key = {"key": "someKey"}
        service_account_b64 = b64encode(json.dumps(service_account_key).encode('utf-8')).decode('utf-8')

        with patch('sys.exit', return_value="RaisedError"):
            cf = config(project_id=project_id, service_account_b64=service_account_b64)
            assert cf.get_project_id() == "RaisedError"

    mock_krogon_dsl(_run_dsl)


def test_can_get_service_account_if_exits():
    def _run_dsl(_args):
        project_id = "someId"
        service_account_key = {"key": "someKey"}
        service_account_b64 = b64encode(json.dumps(service_account_key).encode('utf-8')).decode('utf-8')
        cf = config(project_id=project_id, service_account_b64=service_account_b64)
        assert_same_dict(
            json.loads(b64decode(cf.get_service_account_b64()).decode('utf-8')),
            service_account_key)

    mock_krogon_dsl(_run_dsl)


def test_can_get_service_account_if_exits_as_env_variable():
    def _run_dsl(args):
        os: MockOsSystem = args['os_system']
        project_id = "someId"
        service_account_key = {"key": "someKey"}
        service_account_b64 = b64encode(json.dumps(service_account_key).encode('utf-8')).decode('utf-8')
        os.mock_get_env('KG_SERVICE_ACCOUNT_B64', return_values=[service_account_b64])
        os.mock_get_env('KG_DELETE', return_values=["true"])
        os.mock_get_env('KG_TEMPLATE', return_values=["false"])

        cf = config(project_id=project_id)

        assert_same_dict(
            json.loads(b64decode(cf.get_service_account_b64()).decode('utf-8')),
            service_account_key)

    mock_krogon_dsl(_run_dsl)


def test_can_raise_error_if_service_account_missing():
    def _run_dsl(_args):
        project_id = "someProjectId"

        with patch('sys.exit', return_value="RaisedError"):
            cf = config(project_id=project_id)
            assert cf.get_service_account_b64(ensure=True) == "RaisedError"

    mock_krogon_dsl(_run_dsl)


def test_can_get_service_account_info_if_exits():
    def _run_dsl(_args):
        project_id = "someId"
        service_account_key = {"key": "someKey"}
        service_account_b64 = b64encode(json.dumps(service_account_key).encode('utf-8')).decode('utf-8')
        cf = config(project_id=project_id, service_account_b64=service_account_b64)
        assert_same_dict(
            cf.get_service_account_info(),
            service_account_key)

    mock_krogon_dsl(_run_dsl)
