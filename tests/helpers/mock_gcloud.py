from krogon.gcp.gcloud import GCloud
from tests.helpers.mocks import MockSetup, Setup
from unittest.mock import Mock, PropertyMock
from typing import List, Any
import krogon.either as E


class MockGCloud:
    def __init__(self):
        self.client = Mock(name='gcloud.deployment_manager.client')
        self.client = MockGCloud._mock_deployments(self.client)
        self.client = MockGCloud._mock_cloudbuild(self.client)
        self.client = MockGCloud._mock_kms(self.client)

        init_client = Mock(name='init_client')
        MockSetup.mock(init_client, [Setup(return_values=[E.Success(self.client)])])
        self.gcloud = GCloud(service_account_info={}, init_client=init_client)

    def get_mock(self) -> GCloud:
        return self.gcloud

    def mock_path(self, path: str, args=None, kwargs=None, exec_returns: List[Any] = None):
        MockGCloud._mock_path(self.client, path, args, kwargs, exec_returns)

    @staticmethod
    def _mock_deployments(client):
        status = lambda action: {'fingerprint': 'someFingerprint', 'operation': {'status': 'DONE', 'progress': 100, 'operationType': action}}
        MockGCloud._mock_path(client, 'deployments().get()', exec_returns=[status('get')])
        MockGCloud._mock_path(client, 'deployments().delete()', exec_returns=[status('delete')])
        MockGCloud._mock_path(client, 'deployments().update()', exec_returns=[status('update')])
        MockGCloud._mock_path(client, 'deployments().insert()', exec_returns=[status('insert')])
        return client

    @staticmethod
    def _mock_cloudbuild(client):
        resp = {'metadata': {'build': {'id': '1'}}}
        MockGCloud._mock_path(client, 'projects().builds().create()', exec_returns=[resp])
        resp = {'status': 'SUCCESS'}
        MockGCloud._mock_path(client, 'projects().builds().get()', exec_returns=[resp])
        return client

    @staticmethod
    def _mock_kms(client):
        MockGCloud._mock_path(client, 'projects().locations().keyRings().get()', exec_returns=[{}])
        MockGCloud._mock_path(client, 'projects().locations().keyRings().create()', exec_returns=[{}])
        MockGCloud._mock_path(client, 'projects().locations().keyRings().cryptoKeys().create()', exec_returns=[{}])
        MockGCloud._mock_path(client, 'projects().locations().keyRings().cryptoKeys().encrypt()',
                              exec_returns=[{'ciphertext': 'someCiphertext'}])
        return client

    @staticmethod
    def _mock_path(mock, path: str, args=None, kwargs=None, exec_returns: List[Any] = None):
        MockGCloud._mock_path_chain(mock, None, path, args, kwargs, exec_returns)

    @staticmethod
    def _mock_path_chain(mock, path_prefix, path: str, args, kwargs, exec_returns: List[Any]):

        if '.' not in path:
            name = path_prefix + '.' + path
            gcloud_method_i = Mock(name=name+'-i')
            gcloud_method = Mock(name=name)
            MockSetup.mock(gcloud_method, [Setup(kwargs=kwargs, args=args, return_values=[gcloud_method_i])])

            gcloud_method_i.execute = Mock(name=name+'-i.execute')
            MockSetup.mock(gcloud_method_i.execute, [Setup(return_values=exec_returns)])
            attrs = {'name': name+'-prop', path.replace('()', ''): gcloud_method}
            mock.configure_mock(**attrs)
            return

        head, *tail = path.split('.')
        prop_mock = getattr(mock, head) if hasattr(mock, head) else Mock()
        next_path = '.'.join(tail)
        name = path_prefix + '.' + head if path_prefix is not None else head

        MockGCloud._mock_path_chain(prop_mock, name, next_path, args, kwargs, exec_returns)
        if '()' in head:
            attrs = {'name': name+'-prop', head.replace('()', ''): Mock(name=name, return_value=prop_mock)}
        else:
            attrs = {'name': name+'-prop', head: prop_mock}

        mock.configure_mock(**attrs)


def create_mock_http_error(status: int):
    return  MockHttpError(status=status)


class MockHttpErrorResponse:
    def __init__(self, status: int):
        self.status = status


class MockHttpError(Exception):
    def __init__(self, status: int):
        self.resp = MockHttpErrorResponse(status)


