import re
import json
import krogon.either as E
import krogon.file_system as fs
import krogon.os as os
from typing import List
from krogon.either_ext import pipeline
from krogon.logger import Logger
from krogon.either_ext import chain


class Scripter:
    def __init__(self,
                 project_id: str,
                 service_account_info: dict,
                 os_system: os.OS,
                 file_system: fs.FileSystem,
                 logger: Logger):

        self.file_system = file_system
        self.os_system = os_system
        self.log = logger
        self.project = project_id
        self.cache_dir = file_system.cwd() + '/' + self.cache_folder_name()
        self.scripts_dir = file_system.script_dir(__file__)

        if not file_system.exists(self.cache_dir):
            file_system.mkdir(self.cache_dir)

        self.service_account_info = service_account_info
        self.service_account_file = self.cache_dir + '/service_account.json'

    @staticmethod
    def cache_folder_name():
        return '.infra_cache'

    def os_run(self, command: str):
        return self.os_system.run(command, self.log)

    def is_macos(self):
        return self.os_system.is_macos()


def get_clusters(scp: Scripter, by_tag: str):
    def _parse_cluster_names(cluster_names: str):
        names = list(map(lambda c: c.strip().strip(), cluster_names.split('\n')))
        return list(filter(lambda name: by_tag in name, names))

    return _setup(scp) \
           | E.then | (lambda _: scp.os_run("{cache_dir}/google-cloud-sdk/bin/gcloud "
                                            "container clusters list --format=\"value(name)\""
                                            .format(cache_dir=scp.cache_dir))) \
           | E.then | _parse_cluster_names


def install_istio(scp: Scripter, cluster_name: str, istio_version: str, gateway_type: str,
                  auto_sidecar_injection: bool):

    return _setup(scp) \
           | E.then | (lambda _: _gen_kubeconfig(scp, cluster_name)) \
           | E.then | (lambda _: _install_istio(scp, cluster_name, istio_version, gateway_type,
                                                auto_sidecar_injection)) \
           | E.then | (lambda _: _install_istio_gateway(scp, cluster_name))


def proxy(scp: Scripter, cluster_name: str, port: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return _setup(scp) \
           | E.then | (lambda _: _gen_kubeconfig(scp, cluster_name)) \
           | E.then | (lambda _: scp.os_run('{cache_dir}/kubectl proxy --port {port} --kubeconfig {kubeconfig_file}'
                                            .format(cache_dir=scp.cache_dir,
                                                    kubeconfig_file=kubeconfig_file,
                                                    port=port)))


def kubectl_all_by_tag(scp: Scripter, cluster_tag: str, command: str):
    def _exec_in_clusters(cluster_names: List[str]):
        return chain(cluster_names, lambda cluster_name: kubectl(scp, cluster_name, command))

    return get_clusters(scp, by_tag=cluster_tag) \
           | E.then | (lambda cluster_names: _exec_in_clusters(cluster_names))


def kubectl(scp: Scripter, cluster_name: str, command: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return _setup(scp) \
           | E.then | (lambda _: _gen_kubeconfig(scp, cluster_name)) \
           | E.then | (lambda _: scp.os_run('{cache_dir}/kubectl --kubeconfig {kubeconfig_file} {command}'
                                            .format(cache_dir=scp.cache_dir,
                                                    kubeconfig_file=kubeconfig_file,
                                                    command=command)))


def get_access_token(scp: Scripter, cluster_name: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return _setup(scp) \
           | E.then | (lambda _: _gen_kubeconfig(scp, cluster_name)) \
           | E.then | (lambda _: scp.os_run('{scripts_dir}/get-access-token.sh {cache_dir} {kubeconfig_file}'
                                            .format(scripts_dir=scp.scripts_dir,
                                                    cache_dir=scp.cache_dir,
                                                    kubeconfig_file=kubeconfig_file,
                                                    cluster_name=cluster_name)))


def configure_vault(scp: Scripter, cluster_name: str, vault_address: str, vault_token: str, vault_ca_b64: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)

    return _setup(scp) \
           | E.then | (lambda _: _gen_kubeconfig(scp, cluster_name)) \
           | E.then | (lambda _: scp.os_run(
        "{scripts_dir}/install-vaultingkube.sh {cache_dir} {kubeconfig_file} "
        "{vault_address} {vault_token} {vault_ca_b64}"
            .format(scripts_dir=scp.scripts_dir, cache_dir=scp.cache_dir, vault_address=vault_address,
                    vault_token=vault_token, vault_ca_b64=vault_ca_b64, kubeconfig_file=kubeconfig_file)))


def configure_gclb(scp: Scripter, cluster_names: List[str], global_lb_name: str):
    return _setup(scp) \
           | E.then | (lambda _:  _create_gclb_ip(scp, global_lb_name)) \
           | E.then | (lambda ip: _sync_clusters_with_gclb(scp, ip, global_lb_name, cluster_names))


def delete_gclb(scp: Scripter, global_lb_name: str):
    return scp.os_run("{scripts_dir}/gclb-ingress.sh delete {cache_dir} "
                      "{cache_dir}/clusters.yaml {global_lb_name} {project}"
                      .format(global_lb_name=global_lb_name, cache_dir=scp.cache_dir, scripts_dir=scp.scripts_dir,
                              project=scp.project))


def remove_gclb_cluster(scp: Scripter, cluster_name: str, global_lb_name: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return scp.os_run("{scripts_dir}/gclb-ingress.sh remove-clusters {cache_dir} "
                      "{kubeconfig} {global_lb_name} {project}"
                      .format(global_lb_name=global_lb_name, scripts_dir=scp.scripts_dir,
                              kubeconfig=kubeconfig_file, cache_dir=scp.cache_dir,
                              project=scp.project))


def _sync_clusters_with_gclb(scp: Scripter, gclb_ip: str, global_lb_name: str, cluster_names: List[str]):
    def _extract_kubeconfigs():
        configs = scp.file_system.glob("{cache_dir}/*kubeconfig.yaml".format(cache_dir=scp.cache_dir))
        scp.log.info("EXTRACT CONFIGS: Found: {}".format(configs))
        final_configs = []
        for config in configs:
            for cluster_name in cluster_names:
                if cluster_name+'-kubeconfig.yaml' in config:
                    final_configs.append(config)
                    break
        if len(final_configs) == 0:
            return E.Failure("Must have at least one cluster online with the LB.")
        return E.Success(final_configs)

    def _sync_configs(final_configs):
        scp.log.info("SYNCING CONFIGS: {}".format(final_configs))

        return scp.os_run("KUBECONFIG={configs} {cache_dir}/kubectl config view --flatten > {cache_dir}/clusters.yaml"
                          .format(configs=':'.join(final_configs), cache_dir=scp.cache_dir)) \
               | E.then | (
                   lambda _: scp.os_run("{scripts_dir}/gclb-ingress.sh create {cache_dir} "
                                        "{cache_dir}/clusters.yaml {global_lb_name} {project}"
                                        .format(gclb_ip=gclb_ip, cache_dir=scp.cache_dir, global_lb_name=global_lb_name,
                                                scripts_dir=scp.scripts_dir, project=scp.project)))

    return pipeline(list(map(lambda name: lambda _: _gen_kubeconfig(scp, name), cluster_names))) \
           | E.then | (lambda _: _extract_kubeconfigs()) \
           | E.then | (lambda configs: _sync_configs(configs))


def _create_gclb_ip(scp: Scripter, global_lb_name: str):
    def extract_ip(ip_data):
        return re.search(r'address: (\d+\.\d+\.\d+\.\d+)', ip_data, re.IGNORECASE).group(1)

    def _get_global_lb_ip(lb_name: str):
        return scp.os_run("{cache_dir}/google-cloud-sdk/bin/gcloud compute addresses describe --global {global_lb_name}"
                          .format(cache_dir=scp.cache_dir, global_lb_name=lb_name)) \
               | E.on | dict(failure=lambda e: scp.log.info("Get GCLB Failed: {}".format(e))) \
               | E.from_either | dict(if_success=lambda ip_data: extract_ip(ip_data),
                                      if_failure=lambda _: None)

    gclb_ip = _get_global_lb_ip(global_lb_name)
    if gclb_ip is None:
        scp.log.info("Creating GCLB IP...")
        return scp.os_run("{cache_dir}/google-cloud-sdk/bin/gcloud compute addresses create --global {global_lb_name}"
                          .format(cache_dir=scp.cache_dir, global_lb_name=global_lb_name)) \
               | E.then | (lambda _: _get_global_lb_ip(global_lb_name)) \
               | E.on | dict(success=lambda ip: scp.log.info("Created GCLB IP: {}".format(ip)))
    else:
        scp.log.info("CLB Already exists: {}".format(gclb_ip))
        return E.Success(gclb_ip)


def _setup(scp: Scripter):
    return _install_google_cloud_sdk(scp) \
           | E.then | (lambda _: _install_kubectl(scp)) \
           | E.then | (lambda _: _install_helm(scp)) \
           | E.then | (lambda _: _install_kubemci(scp)) \
           | E.then | (lambda _: _write_service_account_file(scp))


def _cleanup(scp: Scripter, cluster_name: str):
    return _delete_service_account_file(scp) \
           | E.then | (lambda _: _delete_kubeconfig(scp, cluster_name))


def _delete_kubeconfig(scp: Scripter, cluster_name: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return scp.os_run('rm -f {}'.format(kubeconfig_file))


def _gen_kubeconfig(scp: Scripter, cluster_name: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return scp.os_run('{scripts_dir}/create-kube-config.sh {cluster_name} '
                      '{cache_dir} {key_file} "{kubeconfig_file}" {project}'
                      .format(scripts_dir=scp.scripts_dir,
                              cluster_name=cluster_name,
                              cache_dir=scp.cache_dir,
                              kubeconfig_file=kubeconfig_file,
                              key_file=scp.service_account_file,
                              project=scp.project))


def _delete_service_account_file(scp: Scripter):
    scp.file_system.delete(scp.service_account_file)


def _write_service_account_file(scp: Scripter):
    scp.file_system.write(scp.service_account_file, json.dumps(scp.service_account_info, ensure_ascii=False))


def _kubeconfig_file_path(cache_dir: str, cluster_name: str):
    return '{cache_dir}/{cluster_name}-kubeconfig.yaml' \
        .format(cache_dir=cache_dir, cluster_name=cluster_name)


def _install_istio(scp: Scripter, cluster_name: str, istio_version: str,
                   gateway_type: str, auto_sidecar_injection: bool):

    sidecar_injection = 'true' if auto_sidecar_injection else 'false'
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return _download_istio(scp, istio_version) \
           | E.then | (lambda _: scp.os_run('{scripts_dir}/install-istio.sh {cache_dir} '
                                            '{istio_version} {kubeconfig_file} {gateway_type} {sidecar_injection}'
                                            .format(scripts_dir=scp.scripts_dir,
                                                    cache_dir=scp.cache_dir,
                                                    kubeconfig_file=kubeconfig_file,
                                                    istio_version=istio_version,
                                                    gateway_type=gateway_type,
                                                    sidecar_injection=sidecar_injection)))


def _install_istio_gateway(scp: Scripter, cluster_name: str):
    kubeconfig_file = _kubeconfig_file_path(scp.cache_dir, cluster_name)
    return scp.os_run('{scripts_dir}/istio-gateway.sh install '
                      '{cache_dir} {kubeconfig_file}'
                      .format(scripts_dir=scp.scripts_dir,
                              cache_dir=scp.cache_dir,
                              kubeconfig_file=kubeconfig_file))


def _download_istio(scp: Scripter, istio_version: str):
    if scp.file_system.exists("{cache_dir}/istio-{version}".format(cache_dir=scp.cache_dir, version=istio_version)):
        return E.Success()

    scp.log.info("INSTALLING DEPENDENCY: Installing istio-{version}...".format(version=istio_version))
    cur_os = 'osx' if scp.is_macos() else 'linux'
    istio_sdk_url = \
        "https://github.com/istio/istio/releases/download/{istio_version}/istio-{istio_version}-{os}.tar.gz" \
            .format(istio_version=istio_version, os=cur_os)
    return scp.os_run(
        "cd {cache_dir} && curl -L {url} | tar zx"
            .format(cache_dir=scp.cache_dir, os=cur_os, url=istio_sdk_url))


def _install_helm(scp: Scripter):
    if scp.file_system.exists("{cache_dir}/helm".format(cache_dir=scp.cache_dir)):
        return E.Success()

    scp.log.info("INSTALLING DEPENDENCY: Installing helm...")
    cur_os = 'darwin' if scp.is_macos() else 'linux'
    return scp.os_run("cd {cache_dir} && mkdir helm && cd ./helm && curl -L https://storage.googleapis.com/kubernetes-helm/"
                      "helm-v2.12.1-{os}-amd64.tar.gz | tar zx && cp -rf ./{os}-amd64/* . && rm -r ./{os}-amd64"
                      .format(cache_dir=scp.cache_dir, os=cur_os))


def _install_google_cloud_sdk(scp: Scripter):
    if scp.file_system.exists("{cache_dir}/google-cloud-sdk".format(cache_dir=scp.cache_dir)):
        return E.Success()

    scp.log.info("INSTALLING DEPENDENCY: Installing google-cloud-sdk...")
    cur_os = 'darwin' if scp.is_macos() else 'linux'

    google_sdk_url = ("https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/"
                      "google-cloud-sdk-228.0.0-{os}-x86_64.tar.gz".format(os=cur_os))
    return scp.os_run("cd {cache_dir} && curl -L {url} | tar zx"
                      .format(cache_dir=scp.cache_dir, url=google_sdk_url))


def _install_kubectl(scp: Scripter):
    if scp.file_system.exists("{cache_dir}/kubectl".format(cache_dir=scp.cache_dir)):
        return E.Success()

    cur_os = 'darwin' if scp.is_macos() else 'linux'

    scp.log.info("INSTALLING DEPENDENCY: Installing kubectl...")
    scp.os_run("curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt") \
    | E.then | (lambda kube_version:
                scp.os_run("curl -L https://storage.googleapis.com/kubernetes-release/release"
                           "/{kube_version}/bin/{os}/amd64/kubectl > {cache_dir}/kubectl "
                           "&& chmod u+x {cache_dir}/kubectl"
                           .format(os=cur_os, kube_version=kube_version, cache_dir=scp.cache_dir)))


def _install_kubemci(scp: Scripter):
    if scp.file_system.exists("{cache_dir}/kubemci".format(cache_dir=scp.cache_dir)):
        return E.Success()

    scp.log.info("INSTALLING DEPENDENCY: Installing kubemci...")
    cur_os = 'darwin' if scp.is_macos() else 'linux'
    url = ("https://storage.googleapis.com/kubemci-release/release/v0.4.0/bin/{os}/amd64/kubemci".format(os=cur_os))
    scp.os_run("cd {cache_dir} && curl -L {url} > {cache_dir}/kubemci && chmod u+x {cache_dir}/kubemci"
               .format(cache_dir=scp.cache_dir, url=url))


