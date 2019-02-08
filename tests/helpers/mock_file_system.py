from krogon.file_system import FileSystem
from unittest.mock import Mock, MagicMock
from krogon.scripts.scripter import Scripter
from .mocks import MockSetup, Setup
from typing import List


class MockFileSystem:
    def __init__(self):
        file_system = Mock(spec=FileSystem)
        file_system.cwd = MagicMock(name='file_system.cwd', return_value=self.cwd())
        file_system.script_dir = MagicMock(name='file_system.script_dir', return_value=self.script_dir())
        file_system.exists = MagicMock(name='file_system.exists', return_value=False)
        file_system.mkdir = MagicMock(name='file_system.mkdir')
        file_system.write = MagicMock(name='file_system.write')
        file_system.read = MagicMock(name='file_system.read', return_value='')
        file_system.delete = MagicMock(name='file_system.delete')
        file_system.glob = MagicMock(name='file_system.glob', return_value=[])
        self.file_system = file_system
        self.glob_expectations = []
        self.mock_glob_kubeconfigs([])

    def mock_glob_kubeconfigs(self, cluster_configs: List[str]):
        expectation = Setup(args=['{cwd}/{cache_dir}/*kubeconfig.yaml'
                            .format(cwd=self.file_system.cwd(), cache_dir=Scripter.cache_folder_name())],
                            return_values=[cluster_configs])
        self.glob_expectations.insert(0, expectation)
        return self

    @staticmethod
    def cwd():
        return '/var/app-root'

    @staticmethod
    def script_dir():
        return '/var/krogon/scripts'

    def get_mock(self):
        MockSetup.mock(self.file_system.glob, self.glob_expectations)
        return self.file_system
