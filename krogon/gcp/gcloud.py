from typing import Callable, Any
from google.oauth2 import service_account
from apiclient.discovery import build
from krogon.config import Config
from krogon.os import OS
from krogon.logger import Logger
from datetime import datetime
from datetime import timedelta
import krogon.file_system as fs
import krogon.yaml as yaml
import krogon.either as E
import json


class GCloud:
    def __init__(self,
                 config: Config,
                 file: fs.FileSystem,
                 os: OS,
                 log: Logger,
                 init_client: Callable[[str, str, dict], Any]):

        self.init_client = init_client
        self.service_account_info = config.service_account_info
        self.file = file
        self.config = config
        self.run = lambda cmd: os.run(cmd, log)
        self.is_macos = os.is_macos
        self.log = log


def new_gcloud(config: Config, file: fs.FileSystem, os: OS, log: Logger):
    return GCloud(config, file, os, log, _make_init_client())


def create_api(gcloud: GCloud, name: str, version: str):
    return gcloud.init_client(name, version, gcloud.service_account_info)


def gcloud_cmd(gcloud: GCloud, command: str):
    return _configure_auth(gcloud) \
           | E.then | (lambda _: gcloud.run("{cache_dir}/google-cloud-sdk/bin/gcloud {cmd}"
                                            .format(cache_dir=gcloud.config.cache_dir, cmd=command)))


def kubeconfig_file_path(gcloud: GCloud, cluster_name: str):
    return _kubeconfig_file_path(gcloud.config.cache_dir, cluster_name)


def get_access_token(gcloud: GCloud, cluster_name: str):
    kubeconfig_file = _kubeconfig_file_path(gcloud.config.cache_dir, cluster_name)

    return gen_kubeconfig(gcloud, cluster_name) \
           | E.then | (lambda _: gcloud.run('{scripts_dir}/get-access-token.sh {cache_dir} {kubeconfig_file}'
                                            .format(scripts_dir=gcloud.config.scripts_dir,
                                                    cache_dir=gcloud.config.cache_dir,
                                                    kubeconfig_file=kubeconfig_file,
                                                    cluster_name=cluster_name)))


def gen_kubeconfig(gcloud: GCloud, cluster_name: str):

    if _is_kubeconfig_valid(gcloud, cluster_name, gcloud.log):
        return E.Success()

    kubeconfig_file = _kubeconfig_file_path(gcloud.config.cache_dir, cluster_name)

    return _configure_auth(gcloud) \
           | E.then | (lambda _:  gcloud.run('{scripts_dir}/create-kube-config.sh {cluster_name} '
                                             '{cache_dir} {key_file} "{kubeconfig_file}" {project}'
                                             .format(scripts_dir=gcloud.config.scripts_dir,
                                                     cluster_name=cluster_name,
                                                     cache_dir=gcloud.config.cache_dir,
                                                     kubeconfig_file=kubeconfig_file,
                                                     key_file=gcloud.config.service_account_file,
                                                     project=gcloud.config.project_id)))


def get_clusters(gcloud: GCloud, by_tag: str):

    def _parse_cluster_names(cluster_names: str):
        names = list(map(lambda c: c.strip().strip(), cluster_names.split('\n')))
        return list(filter(lambda name: by_tag in name, names))

    return _configure_auth(gcloud) \
           | E.then | (lambda _: gcloud.run("{cache_dir}/google-cloud-sdk/bin/gcloud "
                                            "container clusters list --format=\"value(name)\""
                                            .format(cache_dir=gcloud.config.cache_dir))) \
           | E.then | _parse_cluster_names


def _configure_auth(gcloud: GCloud):
    return _install_google_cloud_sdk(gcloud) \
           | E.then | (lambda _: _write_service_account_file(gcloud))


def _cleanup(gcloud: GCloud, cluster_name: str):
    return _delete_service_account_file(gcloud) \
           | E.then | (lambda _: _delete_kubeconfig(gcloud, cluster_name))


def _delete_kubeconfig(gcloud: GCloud, cluster_name: str):
    kubeconfig_file = _kubeconfig_file_path(gcloud.config.cache_dir, cluster_name)
    return gcloud.run('rm -f {}'.format(kubeconfig_file))


def _delete_service_account_file(gcloud: GCloud):
    gcloud.file.delete(gcloud.config.service_account_file)


def _write_service_account_file(gcloud: GCloud):
    gcloud.file.write(gcloud.config.service_account_file,
                      json.dumps(gcloud.config.service_account_info, ensure_ascii=False))


def _kubeconfig_file_path(cache_dir: str, cluster_name: str):
    return '{cache_dir}/{cluster_name}-kubeconfig.yaml' \
        .format(cache_dir=cache_dir, cluster_name=cluster_name)


def _install_google_cloud_sdk(gcloud: GCloud):
    if gcloud.file.exists("{cache_dir}/google-cloud-sdk".format(cache_dir=gcloud.config.cache_dir)):
        return E.Success()

    gcloud.log.info("INSTALLING DEPENDENCY: Installing google-cloud-sdk...")
    cur_os = 'darwin' if gcloud.is_macos() else 'linux'

    google_sdk_url = ("https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/"
                      "google-cloud-sdk-228.0.0-{os}-x86_64.tar.gz".format(os=cur_os))
    return gcloud.run("cd {cache_dir} && curl -L {url} | tar zx"
                      .format(cache_dir=gcloud.config.cache_dir, url=google_sdk_url))


def _is_kubeconfig_valid(gcloud: GCloud, cluster_name: str, log: Logger):
    kubeconfig_file = _kubeconfig_file_path(gcloud.config.cache_dir, cluster_name)

    def is_valid(expiry: str) -> bool:
        return datetime.fromisoformat(expiry) > (datetime.utcnow() + timedelta(minutes=10))

    def parse_kubeconfig_expiry() -> str:
        kubeconfig = yaml.load(gcloud.file.read(kubeconfig_file))
        return kubeconfig['users'][0]['user']['auth-provider']['config']['expiry'].replace('Z', '')

    if gcloud.file.exists(kubeconfig_file):
        return E.try_catch(lambda: parse_kubeconfig_expiry()) \
               | E.then | (lambda expiry: is_valid(expiry)) \
               | E.on | dict(failure=lambda e: log.warn('Failed to parse kubeconfig at: {}. {}'
                                                        .format(kubeconfig_file, e))) \
               | E.from_either | dict(if_success=lambda valid: valid,
                                      if_failure=lambda _: False)

    return False


def _make_init_client() -> Any:
    def _init_client(api: str, version: str, service_acc_info: dict):
        return E.try_catch(lambda: service_account.Credentials.from_service_account_info(service_acc_info)) \
               | E.then | (lambda credentials: E.try_catch(lambda: build(api,
                                                                         version,
                                                                         credentials=credentials,
                                                                         cache_discovery=False)))
    return _init_client
