from krogon.os import OS
from .mock_file_system import MockFileSystem
from unittest.mock import Mock
from krogon.scripts.scripter import Scripter
from .mocks import MockSetup, Setup
from typing import Any, List
import krogon.either as E


class MockOsSystem:
    def __init__(self):
        os_system = Mock(spec=OS)
        os_system.is_macos = Mock(name='os_system.is_macos', return_value=True)
        os_system.run = Mock(name='os_system.run', return_value=E.Success())
        self.os_system = os_system
        self.mock_gcloud_download(E.Success())
        kubectl_version = '1.0.5'
        self.mock_kubernetes_release(E.Success(kubectl_version))
        self.mock_download_install_kubectl(kubectl_version, E.Success())
        self.mock_download_install_helm(E.Success())
        self.mock_download_install_kubemci(E.Success())

    def mock_install_vaultingkube(self, cluster_name: str, vault_address: str,
                                  vault_token: str, vault_ca_b64: str, return_value: E.Either[Any, Any]):

        cmd = '{script_dir}/install-vaultingkube.sh {cwd}/{cache_dir_name} ' \
              '{cwd}/{cache_dir_name}/{cluster_name}-kubeconfig.yaml {vault_address} ' \
              '{vault_token} {vault_ca_b64}' \
            .format(cache_dir_name=Scripter.cache_folder_name(),
                    cwd=MockFileSystem.cwd(), cluster_name=cluster_name,
                    script_dir=MockFileSystem.script_dir(), vault_ca_b64=vault_ca_b64,
                    vault_token=vault_token, vault_address=vault_address)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_install_istio_gateway(self, cluster_name: str, return_value: E.Either[Any, Any]):
        cmd = '{script_dir}/istio-gateway.sh install {cwd}/{cache_dir_name} ' \
              '{cwd}/{cache_dir_name}/{cluster_name}-kubeconfig.yaml' \
            .format(cache_dir_name=Scripter.cache_folder_name(),
                    cwd=MockFileSystem.cwd(), cluster_name=cluster_name,
                    script_dir=MockFileSystem.script_dir())

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_install_istio(self, istio_version: str, cluster_name: str,
                           gateway_type: str,
                           auto_sidecar_injection: bool,
                           return_value: E.Either[Any, Any]):
        cmd = '{script_dir}/install-istio.sh {cwd}/{cache_dir_name} ' \
              '{istio_version} {cwd}/{cache_dir_name}/{cluster_name}-kubeconfig.yaml ' \
              '{gateway_type} {auto_sidecar_injection}' \
                  .format(cache_dir_name=Scripter.cache_folder_name(),
                          cwd=MockFileSystem.cwd(), cluster_name=cluster_name,
                          script_dir=MockFileSystem.script_dir(), istio_version=istio_version,
                          gateway_type=gateway_type, auto_sidecar_injection=str(auto_sidecar_injection).lower())

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_download_istio(self, istio_version: str, return_value: E.Either[Any, Any]):
        os = 'osx' if self.os_system.is_macos() else 'linux'
        cmd = 'cd {cwd}/{cache_dir_name} && curl -L https://github.com/istio/istio/releases/' \
              'download/1.0.5/istio-{istio_version}-{os}.tar.gz | tar zx' \
                  .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(),
                          os=os, istio_version=istio_version)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_create_gclb_address(self, gclb_name: str, return_value: E.Either[Any, Any]):
        cmd = '{cwd}/{cache_dir_name}/google-cloud-sdk/bin/gcloud compute addresses create --global {gclb_name}' \
            .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(), gclb_name=gclb_name)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_create_gclb_clusters(self, gclb_name: str, project_id: str, return_value: E.Either[Any, Any]):
        cmd = '{script_dir}/gclb-ingress.sh create {cwd}/{cache_dir_name} ' \
              '{cwd}/{cache_dir_name}/clusters.yaml {gclb_name} {project_id}' \
            .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(),
                    script_dir=MockFileSystem.script_dir(), gclb_name=gclb_name, project_id=project_id)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_flatten_cluster_configs(self, cluster_kubeconfig_paths: List[str], return_value: E.Either[Any, Any]):
        kubeconfig_paths = ':'.join(cluster_kubeconfig_paths)

        cmd = 'KUBECONFIG={kubeconfig_paths} ' \
              '{cwd}/{cache_dir_name}/kubectl config view --flatten > ' \
              '{cwd}/{cache_dir_name}/clusters.yaml' \
            .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(),
                    kubeconfig_paths=kubeconfig_paths)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_create_kube_config(self, cluster_name: str, return_value: E.Either[Any, Any]):
        cmd = '{script_dir}/create-kube-config.sh {cluster_name} {cwd}/{cache_dir_name} ' \
              '{cwd}/{cache_dir_name}/service_account.json ' \
              '"{cwd}/{cache_dir_name}/{cluster_name}-kubeconfig.yaml" project1' \
            .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(),
                    cluster_name=cluster_name, script_dir=MockFileSystem.script_dir())

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_download_install_kubemci(self, return_value: E.Either[Any, Any]):
        os = 'darwin' if self.os_system.is_macos() else 'linux'
        cmd = 'cd {cwd}/{cache_dir_name} && ' \
              'curl -L https://storage.googleapis.com/kubemci-release/release/v0.4.0/' \
              'bin/{os}/amd64/kubemci > {cwd}/{cache_dir_name}/kubemci && ' \
              'chmod u+x {cwd}/{cache_dir_name}/kubemci' \
            .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_download_install_helm(self, return_value: E.Either[Any, Any]):
        os = 'darwin' if self.os_system.is_macos() else 'linux'
        cmd = 'cd {cwd}/{cache_dir_name} && mkdir helm && cd ./helm && curl -L ' \
              'https://storage.googleapis.com/kubernetes-helm/helm-v2.12.1-{os}-amd64.tar.gz ' \
              '| tar zx && cp -rf ./{os}-amd64/* . && rm -r ./{os}-amd64'\
            .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_download_install_kubectl(self, version: str, return_value: E.Either[Any, Any]):
        os = 'darwin' if self.os_system.is_macos() else 'linux'
        cmd = 'curl -L https://storage.googleapis.com/kubernetes-release/release' \
               '/{version}/bin/{os}/amd64/kubectl > {cwd}/{cache_dir_name}/kubectl && ' \
               'chmod u+x {cwd}/{cache_dir_name}/kubectl'\
            .format(version=version, cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_gcloud_download(self, return_value: E.Either[Any, Any]):
        os = 'darwin' if self.os_system.is_macos() else 'linux'
        cmd = 'cd {cwd}/{cache_dir_name} && ' \
              'curl -L https://dl.google.com/dl/cloudsdk/channels/rapid/' \
              'downloads/google-cloud-sdk-228.0.0-{os}-x86_64.tar.gz | tar zx' \
              .format(cache_dir_name=Scripter.cache_folder_name(), cwd=MockFileSystem.cwd(), os=os)

        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_kubernetes_release(self, return_value: E.Either[Any, Any]):
        cmd = 'curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt'
        expectation = Setup(args=[cmd, MockSetup.any()], return_values=[return_value])
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def mock_describe_gclb_address(self, gclb_name: str, return_values: List[E.Either[Any, Any]]):
        expectation = Setup(
            args=[
                '{cwd}/{cache_dir}/google-cloud-sdk/bin/gcloud compute addresses describe --global {gclb_name}'
                    .format(cache_dir=Scripter.cache_folder_name(),
                            cwd=MockFileSystem.cwd(), gclb_name=gclb_name),
                MockSetup.any()],
            return_values=return_values)
        MockSetup.mock(self.os_system.run, [expectation])
        return expectation

    def get_mock(self):
        return self.os_system

