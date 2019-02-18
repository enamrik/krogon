from krogon.config import Config
from krogon.os import OS
from krogon.logger import Logger
from .https import IstioHttpsConfig
from .gateway import create_gateway
from typing import Optional
import krogon.k8s.kubectl as k
import krogon.helm.helm as h
import krogon.either as E
import krogon.maybe as M
import krogon.gcp.gcloud as g
import krogon.file_system as fs


class Istio:
    def __init__(self,
                 config: Config,
                 os: OS,
                 log: Logger,
                 gcloud: g.GCloud,
                 file: fs.FileSystem,
                 k_ctl: k.KubeCtl):

        self.config = config
        self.log = log
        self.file = file
        self.gcloud = gcloud
        self.run = lambda cmd: os.run(cmd, log)
        self.is_macos = os.is_macos
        self.helm = h.Helm(config, os, log, file)
        self.k_ctl = k_ctl


def install_istio(istio: Istio,
                  cluster_name: str,
                  istio_version: str,
                  gateway_type: str,
                  auto_sidecar_injection: bool,
                  https_config: M.Maybe[IstioHttpsConfig]):

    # return create_gateway(istio.k_ctl, istio.config, cluster_name, https_config)
    return _setup(istio, istio_version) \
           | E.then | (lambda _: _install_istio(istio, cluster_name, istio_version, gateway_type,
                                                auto_sidecar_injection)) \
           | E.then | (lambda _: create_gateway(istio.k_ctl, istio.config, cluster_name, https_config))


def _install_istio(istio: Istio, cluster_name: str, istio_version: str,
                   gateway_type: str, auto_sidecar_injection: bool):

    sidecar_injection = 'true' if auto_sidecar_injection else 'false'
    kubeconfig_file = g.kubeconfig_file_path(istio.gcloud, cluster_name)

    return g.gen_kubeconfig(istio.gcloud, cluster_name) \
           | E.then | (lambda _: istio.run('{scripts_dir}/install-istio.sh {cache_dir} '
                                           '{istio_version} {kubeconfig_file} {gateway_type} {sidecar_injection}'
                                           .format(scripts_dir=istio.config.scripts_dir,
                                                   cache_dir=istio.config.cache_dir,
                                                   kubeconfig_file=kubeconfig_file,
                                                   istio_version=istio_version,
                                                   gateway_type=gateway_type,
                                                   sidecar_injection=sidecar_injection)))


def _setup(istio: Istio, istio_version: str):
    return h.install_helm(istio.helm) \
           | E.then | (lambda _: _download_istio(istio, istio_version))


def _download_istio(istio: Istio, istio_version: str):
    if istio.file.exists("{cache_dir}/istio-{version}".format(
            cache_dir=istio.config.cache_dir, version=istio_version)):
        return E.Success()

    istio.log.info("INSTALLING DEPENDENCY: Installing istio-{version}...".format(version=istio_version))
    cur_os = 'osx' if istio.is_macos() else 'linux'
    istio_sdk_url = \
        "https://github.com/istio/istio/releases/download/{istio_version}/istio-{istio_version}-{os}.tar.gz" \
            .format(istio_version=istio_version, os=cur_os)
    return istio.run(
        "cd {cache_dir} && curl -L {url} | tar zx"
            .format(cache_dir=istio.config.cache_dir, os=cur_os, url=istio_sdk_url))


