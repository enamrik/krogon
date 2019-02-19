from typing import List
from krogon.config import Config
from krogon.os import OS
from krogon.logger import Logger
from krogon.either_ext import pipeline
import re
import krogon.file_system as fs
import krogon.gcp.gcloud as g
import krogon.either as E


class KubeMci:
    def __init__(self,
                 config: Config,
                 os: OS,
                 log: Logger,
                 gcloud: g.GCloud,
                 file: fs.FileSystem):

        self.config = config
        self.gcloud = gcloud
        self.log = log
        self.run = lambda cmd: os.run(cmd, log)
        self.is_macos = os.is_macos
        self.file = file


def configure_gclb(k_mci: KubeMci, cluster_names: List[str], global_lb_name: str, service_port: int):
    return _setup(k_mci) \
           | E.then | (lambda _:  _create_gclb_ip(k_mci, global_lb_name)) \
           | E.then | (lambda ip: _sync_clusters_with_gclb(k_mci, ip, global_lb_name, cluster_names, service_port))


def delete_gclb(k_mci: KubeMci, global_lb_name: str, service_port: int):
    return k_mci.run("{scripts_dir}/gclb-ingress.sh delete {cache_dir} "
                     "{cache_dir}/clusters.yaml {global_lb_name} {project} {service_port} {key_file}"
                     .format(global_lb_name=global_lb_name,
                             cache_dir=k_mci.config.cache_dir,
                             scripts_dir=k_mci.config.scripts_dir,
                             project=k_mci.config.project_id,
                             service_port=service_port,
                             key_file=k_mci.config.service_account_file))


def remove_gclb_cluster(k_mci: KubeMci, cluster_name: str, global_lb_name: str, service_port: int):
    kubeconfig_file = g.kubeconfig_file_path(k_mci.gcloud, cluster_name)
    return k_mci.run("{scripts_dir}/gclb-ingress.sh remove-clusters {cache_dir} "
                     "{kubeconfig} {global_lb_name} {project} {service_port} {key_file}"
                     .format(global_lb_name=global_lb_name,
                             scripts_dir=k_mci.config.scripts_dir,
                             kubeconfig=kubeconfig_file,
                             cache_dir=k_mci.config.cache_dir,
                             project=k_mci.config.project_id,
                             service_port=service_port,
                             key_file=k_mci.config.service_account_file))


def _sync_clusters_with_gclb(k_mci: KubeMci,
                             gclb_ip: str,
                             global_lb_name: str,
                             cluster_names: List[str], service_port: int):

    def _extract_kubeconfigs():
        configs = k_mci.file.glob("{cache_dir}/*kubeconfig.yaml"
                                  .format(cache_dir=k_mci.config.cache_dir))
        k_mci.log.info("EXTRACT CONFIGS: Found: {}".format(configs))
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
        k_mci.log.info("SYNCING CONFIGS: {}".format(final_configs))

        return k_mci.run("KUBECONFIG={configs} {cache_dir}/kubectl "
                            "config view --flatten > {cache_dir}/clusters.yaml"
                            .format(configs=':'.join(final_configs), cache_dir=k_mci.config.cache_dir)) \
               | E.then | (
                   lambda _: k_mci.run("{scripts_dir}/gclb-ingress.sh create {cache_dir} "
                                       "{cache_dir}/clusters.yaml {global_lb_name} {project} {service_port} {key_file}"
                                       .format(gclb_ip=gclb_ip,
                                               cache_dir=k_mci.config.cache_dir,
                                               global_lb_name=global_lb_name,
                                               scripts_dir=k_mci.config.scripts_dir,
                                               project=k_mci.config.project_id,
                                               service_port=service_port,
                                               key_file=k_mci.config.service_account_file)))

    return pipeline(list(map(lambda name: lambda _: g.gen_kubeconfig(k_mci.gcloud, name), cluster_names))) \
           | E.then | (lambda _: _extract_kubeconfigs()) \
           | E.then | (lambda configs: _sync_configs(configs))


def _create_gclb_ip(k_mci: KubeMci, global_lb_name: str):
    def extract_ip(ip_data):
        return re.search(r'address: (\d+\.\d+\.\d+\.\d+)', ip_data, re.IGNORECASE).group(1)

    def _get_global_lb_ip(lb_name: str):
        return k_mci.run("{cache_dir}/google-cloud-sdk/bin/gcloud compute addresses describe --global {global_lb_name}"
                            .format(cache_dir=k_mci.config.cache_dir, global_lb_name=lb_name)) \
               | E.on | dict(failure=lambda e: k_mci.log.info("Get GCLB Failed: {}".format(e))) \
               | E.from_either | dict(if_success=lambda ip_data: extract_ip(ip_data),
                                      if_failure=lambda _: None)

    gclb_ip = _get_global_lb_ip(global_lb_name)
    if gclb_ip is None:
        k_mci.log.info("Creating GCLB IP...")
        return k_mci.run("{cache_dir}/google-cloud-sdk/bin/gcloud compute addresses create --global {global_lb_name}"
                            .format(cache_dir=k_mci.config.cache_dir, global_lb_name=global_lb_name)) \
               | E.then | (lambda _: _get_global_lb_ip(global_lb_name)) \
               | E.on | dict(success=lambda ip: k_mci.log.info("Created GCLB IP: {}".format(ip)))
    else:
        k_mci.log.info("CLB Already exists: {}".format(gclb_ip))
        return E.Success(gclb_ip)


def _setup(k_mci: KubeMci):
    return _install_kubemci(k_mci)


def _install_kubemci(k_mci: KubeMci):
    if k_mci.file.exists("{cache_dir}/kubemci".format(cache_dir=k_mci.config.cache_dir)):
        return E.Success()

    k_mci.log.info("INSTALLING DEPENDENCY: Installing kubemci...")
    cur_os = 'darwin' if k_mci.is_macos() else 'linux'
    url = ("https://storage.googleapis.com/kubemci-release/release/v0.4.0/bin/{os}/amd64/kubemci".format(os=cur_os))
    return k_mci.run("cd {cache_dir} && curl -L {url} > {cache_dir}/kubemci && chmod u+x {cache_dir}/kubemci"
                     .format(cache_dir=k_mci.config.cache_dir, url=url))


