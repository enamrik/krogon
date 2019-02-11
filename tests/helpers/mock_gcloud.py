from krogon.gcp.gcloud import GCloud
from tests.helpers.mocks import MockSetup, Setup
from krogon.logger import Logger
from krogon.gcp.deployment_manager.deployment_manager import DeploymentManager
from unittest.mock import Mock
import krogon.either as E


class MockGCloud:
    def __init__(self):

        deployments = Mock(name='gcloud.client.deployments')

        status = {'fingerprint': 'someFingerprint', 'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'get'}}
        self.deployments_get = deployments.get = Mock(name='gcloud.client.deployments.get')
        self.mock_deployment_method(self.deployments_get, kwargs=None, exec_returns=[status])

        status = {'fingerprint': 'someFingerprint', 'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'delete'}}
        self.deployments_delete = deployments.delete = Mock(name='gcloud.client.deployments.delete')
        self.mock_deployment_method(self.deployments_delete, kwargs=None, exec_returns=[status])

        status = {'fingerprint': 'someFingerprint', 'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'update'}}
        self.deployments_update = deployments.update = Mock(name='gcloud.client.deployments.update')
        self.mock_deployment_method(self.deployments_update, kwargs=None, exec_returns=[status])

        status = {'fingerprint': 'someFingerprint', 'operation': {'status': 'DONE', 'progress': 100, 'operationType': 'insert'}}
        self.deployments_insert = deployments.insert = Mock(name='gcloud.client.deployments.insert')
        self.mock_deployment_method(self.deployments_insert, kwargs=None, exec_returns=[status])

        client = Mock(name='gcloud.deployment_manager.client')
        client.deployments = Mock(name='gcloud.client.deployments', return_value=deployments)

        init_client = Mock(name='init_client')
        MockSetup.mock(init_client, [Setup(return_values=[E.Success(client)])])

        self.gcloud = GCloud(service_account_info={}, init_client=init_client)

    def mock_deployment_method(self, mock_dp_method, kwargs, exec_returns):
        http_client = Mock()
        http_client.execute = Mock(name=MockSetup.mock_name(mock_dp_method)+'.execute')
        MockSetup.mock(http_client.execute, [Setup(kwargs=kwargs, return_values=exec_returns)])

        dp_get_setup = Setup(kwargs=kwargs, return_values=[http_client])
        MockSetup.mock(mock_dp_method, [dp_get_setup])
        return dp_get_setup

    def get_mock(self):
        return self.gcloud


def create_mock_http_error(status: int):
    return  MockHttpError(status=status)


class MockHttpErrorResponse:
    def __init__(self, status: int):
        self.status = status


class MockHttpError(Exception):
    def __init__(self, status: int):
        self.resp = MockHttpErrorResponse(status)


