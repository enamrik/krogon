from krogon.os import OS
from .mock_file_system import MockFileSystem
from unittest.mock import Mock
from python_mock import PyMock, MatchArg
from krogon.config import Config
from typing import Any, List
import python_either.either as E


class MockOsSystem:
    def __init__(self):
        os_system = Mock(spec=OS)
        os_system.is_macos = Mock(name='os_system.is_macos', return_value=True)
        os_system.run = Mock(name='os_system.run', return_value=E.success())
        os_system.get_env = Mock(name='os_system.run', return_value=None)
        self.os_system = os_system
        self.mock_gcloud_download(E.success())

    def mock_kubectl_apply_temp_file(self, cluster_name: str, return_value: E.Either[Any, Any]):
        return self.mock_kubectl(cluster_name, command='apply -f /temp/template.yaml', return_value=return_value)

    def mock_kubectl(self, cluster_name: str, command: str, return_value: E.Either[Any, Any]):
        cmd = '{cwd}/{cache_dir_name}/kubectl ' \
              '--kubeconfig {cwd}/{cache_dir_name}/{cluster_name}-kubeconfig.yaml {command}' \
            .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(),
                    cluster_name=cluster_name, command=command)

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def mock_clusters_list(self, cluster_names: List[str]):
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

    def mock_download_install_helm(self, return_value: E.Either[Any, Any]):
        os = 'darwin' if self.os_system.is_macos() else 'linux'
        cmd = 'cd {cwd}/{cache_dir_name} && mkdir helm && cd ./helm && curl -L ' \
              'https://storage.googleapis.com/kubernetes-helm/helm-v2.12.1-{os}-amd64.tar.gz ' \
              '| tar zx && cp -rf ./{os}-amd64/* . && rm -r ./{os}-amd64'\
            .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

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
              'downloads/google-cloud-sdk-228.0.0-{os}-x86_64.tar.gz | tar zx' \
              .format(cache_dir_name=Config.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def mock_kubernetes_release(self, return_value: E.Either[Any, Any]):
        cmd = 'curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt'
        PyMock.mock(self.os_system.run, args=[cmd, MatchArg.any()], return_values=[return_value])

    def get_mock(self):
        return self.os_system

