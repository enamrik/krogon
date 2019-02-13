from krogon.file_system import FileSystem
from unittest.mock import Mock, MagicMock
from krogon.scripts.scripter import Scripter
from .mocks import MockSetup, Setup
from typing import List


class MockFileSystem:
    def __init__(self):
        file_system = Mock(spec=FileSystem)
        file_system.cwd = Mock(name='file_system.cwd', return_value=self.cwd())
        file_system.script_dir = Mock(name='file_system.script_dir', return_value=self.script_dir())
        file_system.exists = Mock(name='file_system.exists', return_value=False)
        file_system.mkdir = Mock(name='file_system.mkdir')
        file_system.write = MockSetup.new_mock(name='file_system.write', return_values=[''])
        file_system.read = Mock(name='file_system.read', return_value='')
        file_system.path_rel_to_app_dir = MockSetup.new_mock(
            name='file_system.path_rel_to_app_dir',
            call_fake=lambda x: MockFileSystem.krogon_dir()+'/'+x['args'][0])
        file_system.path_rel_to_file = MockSetup.new_mock(
            name='file_system.path_rel_to_file',
            call_fake=lambda x: '/rel_to_file/'+x['args'][0])
        file_system.path_rel_to_cwd = MockSetup.new_mock(
            name='file_system.path_rel_to_cwd',
            call_fake=lambda x: '/rel_to_cwd/'+x['args'][0])
        file_system.delete = Mock(name='file_system.delete')
        file_system.glob = Mock(name='file_system.glob', return_value=[])
        self.file_system = file_system
        self.mock_glob_kubeconfigs([])

    def mock_glob_kubeconfigs(self, cluster_configs: List[str]):
        expectation = Setup(args=['{cwd}/{cache_dir}/*kubeconfig.yaml'
                            .format(cwd=self.file_system.cwd(), cache_dir=Scripter.cache_folder_name())],
                            return_values=[cluster_configs])
        MockSetup.mock(self.file_system.glob, [expectation])
        return self

    @staticmethod
    def krogon_dir():
        return '/krogon'

    @staticmethod
    def cwd():
        return '/var/app-root'

    @staticmethod
    def script_dir():
        return '/rel_to_file/./'

    def get_mock(self):
        return self.file_system
