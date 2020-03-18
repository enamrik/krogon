from krogon.file_system import FileSystem
from unittest.mock import Mock
from krogon.config import Config
from python_mock import PyMock
from typing import List
from krogon.yaml import load_all


class MockFileSystem:
    def __init__(self):
        file_system = Mock(spec=FileSystem)
        file_system.cwd = Mock(name='file_system.cwd', return_value=self.cwd())
        file_system.exists = Mock(name='file_system.exists', return_value=False)
        file_system.mkdir = Mock(name='file_system.mkdir')
        file_system.read = Mock(name='file_system.read', return_value='')
        file_system.delete = Mock(name='file_system.delete')
        file_system.glob = Mock(name='file_system.glob', return_value=[])
        file_system.with_temp_file = Mock(name='file_system.with_temp_file', return_value=[])

        self.file_system = file_system
        self.mock_glob_kubeconfigs([])
        self.mock_with_temp_file()
        self.mock_path_rel_to_cwd()
        self.mock_path_rel_to_file()
        self.mock_path_rel_to_app_dir()
        self.mock_write()

    def mock_write(self):
        mock = PyMock.new_mock(name='file_system.write', return_values=[''])
        self.file_system.write = mock

    def mock_path_rel_to_app_dir(self):
        mock = PyMock.new_mock(
            name='file_system.path_rel_to_app_dir',
            call_fake=lambda x: MockFileSystem.krogon_dir()+'/'+x['args'][0])
        self.file_system.path_rel_to_app_dir = mock

    def mock_path_rel_to_file(self):
        mock = PyMock.new_mock(
            name='file_system.path_rel_to_file',
            call_fake=lambda x: '/rel_to_file/'+x['args'][0])
        self.file_system.path_rel_to_file = mock

    def mock_path_rel_to_cwd(self):
        mock = PyMock.new_mock(
            name='file_system.path_rel_to_cwd',
            call_fake=lambda x: '/rel_to_cwd/'+x['args'][0])
        self.file_system.path_rel_to_cwd = mock

    def mock_with_temp_file(self):
        def _t(x):
            filepath = '/temp/'+x['kwargs']['filename']
            self.file_system.write(filepath, x['kwargs']['contents'])
            return x['kwargs']['runner'](filepath)

        PyMock.mock(self.file_system.with_temp_file, call_fake=_t)

    def mock_glob_kubeconfigs(self, cluster_configs: List[str]):
        PyMock.mock(self.file_system.glob, args=['{cwd}/{cache_dir}/*kubeconfig.yaml'
                    .format(cwd=self.file_system.cwd(), cache_dir=Config.cache_folder_name())],
                    return_values=[cluster_configs])
        return self

    @staticmethod
    def krogon_dir():
        return '/krogon'

    @staticmethod
    def cwd():
        return '/var/app-root'

    @staticmethod
    def script_dir():
        return '/rel_to_file/./'+Config.scripts_folder_name()

    def get_mock(self):
        return self.file_system


def find_write_template_calls(fs: MockFileSystem, cluster: str = None) -> List[dict]:
    calls = PyMock.calls(fs.file_system.write)
    matches = []
    for call in calls:
        if cluster is not None and call['args'][0] == '/var/app-root/output/'+cluster+'/k8s.yaml':
            matches = matches + load_all(call['args'][1])
        if call['args'][0] == '/temp/template.yaml':
            matches = matches + load_all(call['args'][1])
        if call['args'][0] == '/var/app-root/output/k8s.yaml':
            matches = matches + load_all(call['args'][1])
    if len(matches) > 0:
        return matches
    raise Exception('fs.write not used to write template')
