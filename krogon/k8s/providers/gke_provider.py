from krogon.config import Config
from datetime import datetime
from datetime import timedelta
import krogon.yaml as yaml
import krogon.either as E
from base64 import b64decode
import json
import re
from krogon.k8s.providers.k8s_provider import K8sProvider


class GKEProvider(K8sProvider):
    def __init__(self,
                 project_id: str,
                 service_account_b64: str,
                 config: Config):

        self._conf = config
        self._project_id = _get_project_id(project_id, config)
        self._service_account_info = _get_service_account_info(service_account_b64, config)
        self._scripts_dir = config.scripts_dir
        self._cache_dir = config.cache_dir
        self._file = config.fs
        self._run = lambda cmd: config.os.run(cmd, config.log)
        self._is_macos = config.os.is_macos
        self._log = config.log
        self._service_account_file = config.cache_dir + '/service_account.json'

    def get_project_id(self):
        return self._project_id

    def get_service_account_info(self):
        return self._service_account_info

    def get_clusters(self, by_regex: str):
        def _parse_cluster_names(cluster_names: str):
            names = list(map(lambda c: c.strip().strip(), cluster_names.split('\n')))
            final_names = set()
            matching_clusters = list(filter(lambda name: re.search(by_regex, name) is not None, names))
            final_names.update(matching_clusters)
            return list(final_names)

        return self._get_all_clusters() | E.then | _parse_cluster_names

    def kubectl(self, command: str, cluster_name: str):
        kubeconfig_file = self._kubeconfig_file_path(cluster_name)
        return self._gen_kubeconfig(cluster_name) \
               | E.on | (dict(whatever=lambda _x, _y: self._log.info("\n\n==========kubectl: {}==========".format(cluster_name)))) \
               | E.then | (lambda _: self._run('{cache_dir}/kubectl --kubeconfig {kubeconfig_file} {command}'
                                               .format(cache_dir=self._cache_dir,
                                                       kubeconfig_file=kubeconfig_file,
                                                       command=command))) \
               | E.on | (dict(whatever=lambda _x, _y: self._log.info("\n==========kubectl: {} END==========\n".format(cluster_name))))

    def _get_all_clusters(self):
        return self._configure_auth() \
               | E.then | (lambda _: self._run("{cache_dir}/google-cloud-sdk/bin/gcloud "
                                               "container clusters list --format=\"value(name)\""
                                               .format(cache_dir=self._cache_dir)))

    def _gen_kubeconfig(self, cluster_name: str):
        if self._is_kubeconfig_valid(cluster_name):
            return E.success()

        kubeconfig_file = self._kubeconfig_file_path(cluster_name)

        self._log.info("\n\n==========KUBECONFIG SETUP==========")
        return self._configure_auth() \
               | E.then | (lambda _: self._run('{scripts_dir}/create-kube-config.sh {cluster_name} '
                                               '{cache_dir} {key_file} "{kubeconfig_file}" {project}'
                                               .format(scripts_dir=self._scripts_dir,
                                                       cluster_name=cluster_name,
                                                       cache_dir=self._cache_dir,
                                                       kubeconfig_file=kubeconfig_file,
                                                       key_file=self._service_account_file,
                                                       project=self._project_id))) \
               | E.on | (dict(whatever=lambda _x, _y: self._log.info("\n==========KUBECONFIG SETUP END==========\n")))

    def _configure_auth(self):
        return self._install_google_cloud_sdk() \
               | E.then | (lambda _: self._install_kubectl()) \
               | E.then | (lambda _: self._write_service_account_file()) \
               | E.then | (lambda _: self._run("{cache_dir}/google-cloud-sdk/bin/gcloud "
                                               "config set project {project}"
                                               .format(cache_dir=self._cache_dir,
                                                       project=self._project_id)
                                               )) \
               | E.then | (lambda _: self._run("{cache_dir}/google-cloud-sdk/bin/gcloud "
                                               "auth activate-service-account --key-file {key_file}"
                                               .format(cache_dir=self._cache_dir,
                                                       key_file=self._service_account_file)))

    def _cleanup(self, cluster_name: str):
        return self._delete_service_account_file() \
               | E.then | (lambda _: self._delete_kubeconfig(cluster_name))

    def _delete_kubeconfig(self, cluster_name: str):
        kubeconfig_file = self._kubeconfig_file_path(cluster_name)
        return self._run('rm -f {}'.format(kubeconfig_file))

    def _delete_service_account_file(self):
        self._file.delete(self._service_account_file)

    def _write_service_account_file(self):
        self._file.write(self._service_account_file,
                         json.dumps(self._service_account_info, ensure_ascii=False))

    def _install_kubectl(self):
        if self._file.exists("{cache_dir}/kubectl".format(cache_dir=self._cache_dir)):
            return E.success()

        cur_os = 'darwin' if self._is_macos() else 'linux'

        self._log.info("INSTALLING DEPENDENCY: Installing kubectl...")
        self._run("curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt") \
        | E.then | (lambda kube_version:
                    self._run("curl -L https://storage.googleapis.com/kubernetes-release/release"
                              "/{kube_version}/bin/{os}/amd64/kubectl > {cache_dir}/kubectl "
                              "&& chmod u+x {cache_dir}/kubectl"
                              .format(os=cur_os, kube_version=kube_version, cache_dir=self._cache_dir)))

    def _install_google_cloud_sdk(self):
        if self._file.exists("{cache_dir}/google-cloud-sdk".format(cache_dir=self._cache_dir)):
            return E.success()

        self._log.info("INSTALLING DEPENDENCY: Installing google-cloud-sdk...")
        cur_os = 'darwin' if self._is_macos() else 'linux'

        gcloud_version = self._conf.get_arg('KG_GCLOUD_VERSION', default='284.0.0')
        google_sdk_url = ("https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/"
                          "google-cloud-sdk-{gcloud_version}-{os}-x86_64.tar.gz"
                          .format(os=cur_os, gcloud_version=gcloud_version))

        return self._run("cd {cache_dir} && curl -L {url} | tar zx"
                          .format(cache_dir=self._cache_dir, url=google_sdk_url))

    def _is_kubeconfig_valid(self, cluster_name: str):
        kubeconfig_file = self._kubeconfig_file_path(cluster_name)

        def is_valid(expiry: str) -> bool:
            return datetime.fromisoformat(expiry) > (datetime.utcnow() + timedelta(minutes=10))

        def parse_kubeconfig_expiry() -> str:
            kubeconfig = yaml.load(self._file.read(kubeconfig_file))
            return kubeconfig['users'][0]['user']['auth-provider']['config']['expiry'].replace('Z', '')

        if self._file.exists(kubeconfig_file):
            return E.try_catch(lambda: parse_kubeconfig_expiry()) \
                   | E.then | (lambda expiry: is_valid(expiry)) \
                   | E.on | dict(failure=lambda e: self._log.warn('Failed to parse kubeconfig at: {}. {}'
                                                                  .format(kubeconfig_file, e))) \
                   | E.from_either | dict(if_success=lambda valid: valid,
                                          if_failure=lambda _: False)

        return False

    def _kubeconfig_file_path(self, cluster_name: str):
        return '{cache_dir}/{cluster_name}-kubeconfig.yaml' \
            .format(cache_dir=self._cache_dir, cluster_name=cluster_name)


def _get_project_id(project_id, config: Config):
    return config.get_arg('KG_PROJECT_ID', project_id, ensure=True)


def _get_service_account_info(service_account_b64: str, config: Config):
    service_account_b64 = config.get_arg('KG_SERVICE_ACCOUNT_B64', service_account_b64, ensure=True)
    return json.loads(b64decode(service_account_b64).decode("utf-8"))


