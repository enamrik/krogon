from krogon.os import OS
from .mock_file_system import MockFileSystem
from unittest.mock import Mock
from python_mock import PyMock, MatchArg
from krogon.config import Config
from typing import Any, List
import krogon.either as E


class MockOsSystem:
    def __init__(self):
        os_system = Mock(spec=OS)
        os_system.is_macos = Mock(name='os_system.is_macos', return_value=True)
        os_system.run = Mock(name='os_system.run', return_value=E.success())
        os_system.get_env = Mock(name='os_system.get_env', return_value=None)
        self.os_system = os_system
        self.mock_gcloud_download(E.success())
        self.mock_kubernetes_release(return_value=E.success("1.16"))
        self.mock_download_install_kubectl("1.16", return_value=E.success())
        self.mock_clusters_list(['prod-us-east1'])
        self.mock_set_project_id('project1', return_values=[E.success()])
        self.mock_activate_service_account('service_account.json', return_values=[E.success()])

    def mock_get_env(self, key, return_values):
        PyMock.mock(self.os_system.get_env, args=[key], return_values=return_values)

    def mock_kubectl_apply_temp_file(self, cluster_name: str, return_value: E.Either[Any, Any]):
        return self.mock_kubectl(cluster_name, command='apply -f /temp/template.yaml', return_value=return_value)

    def mock_kubectl(self, cluster_name: str, command: str, return_value: E.Either[Any, Any]):
        cmd = '{cwd}/{cache_dir_name}/kubectl ' \
              '--kubeconfig {cwd}/{cache_dir_name}/{cluster_name}-kubeconfig.yaml {command}' \
            .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(),
                    cluster_name=cluster_name, command=command)

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def mock_set_project_id(self, project_id: str, return_values: List[E.Either[Any, Any]]):
        cmd = '{cwd}/{cache_dir_name}/google-cloud-sdk/bin/gcloud config set project {project}' \
            .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(), project=project_id)

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=return_values)

    def mock_activate_service_account(self, key_file_path: str, return_values: List[E.Either[Any, Any]]):
        cmd = '{cwd}/{cache_dir_name}/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file ' \
              '{cwd}/{cache_dir_name}/{key_file}' \
            .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(), key_file=key_file_path)

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=return_values)

    def mock_clusters_list(self, cluster_names: List[str]):
        for cluster_name in cluster_names:
            self.mock_create_kube_config(cluster_name, return_value=E.success())
            self.mock_kubectl_apply_temp_file(cluster_name, return_value=E.success())

        cmd = '{cwd}/{cache_dir_name}/google-cloud-sdk/bin/gcloud container clusters list --format=\"value(name)\"' \
            .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd())

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[E.success('\n'.join(cluster_names))])

    def mock_create_kube_config(self, cluster_name: str, return_value: E.Either[Any, Any]):
        cmd = '{script_dir}/create-kube-config.sh {cluster_name} {cwd}/{cache_dir_name} ' \
              '{cwd}/{cache_dir_name}/service_account.json ' \
              '"{cwd}/{cache_dir_name}/{cluster_name}-kubeconfig.yaml" project1' \
            .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(),
                    cluster_name=cluster_name, script_dir=MockFileSystem.script_dir())

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def mock_download_install_kubectl(self, version: str, return_value: E.Either[Any, Any]):
        os = 'darwin' if self.os_system.is_macos() else 'linux'
        cmd = 'curl -L https://storage.googleapis.com/kubernetes-release/release' \
              '/{version}/bin/{os}/amd64/kubectl > {cwd}/{cache_dir_name}/kubectl && ' \
              'chmod u+x {cwd}/{cache_dir_name}/kubectl'\
            .format(version=version, cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def mock_gcloud_download(self, return_value: E.Either[Any, Any]):
        os = 'darwin' if self.os_system.is_macos() else 'linux'
        cmd = 'cd {cwd}/{cache_dir_name} && ' \
              'curl -L https://dl.google.com/dl/cloudsdk/channels/rapid/' \
              'downloads/google-cloud-sdk-284.0.0-{os}-x86_64.tar.gz | tar zx' \
              .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def mock_kubernetes_release(self, return_value: E.Either[Any, Any]):
        cmd = 'curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt'
        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def get_mock(self):
        return self.os_system

