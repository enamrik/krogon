import sys
from typing import List, Callable, Any
from krogon.config import Config
from krogon.either_ext import chain
from krogon.k8s.providers.gke_provider import GKEProvider
from krogon.k8s.providers.host_kubectl_provider import HostKubectlProvider
from krogon.k8s.providers.k8s_provider import K8sProvider
import krogon.either as E
import krogon.yaml as yaml
from krogon.k8s.providers.noop_provider import NoopProvider


class KubeCtl:
    def __init__(self,
                 config: Config,
                 k8s_provider: K8sProvider,
                 cluster_regex: str):

        self._cluster_regex = cluster_regex
        self._config = config
        self._log = config.log
        self._file = config.fs
        self._k8s_provider = k8s_provider
        self._run = lambda cmd: config.os.run(cmd, config.log)

    def __str__(self):
        return 'KubeCtl: Regex: {}, Provider: {}'.format(self._cluster_regex, self._k8s_provider)

    def get_provider(self) -> K8sProvider:
        return self._k8s_provider

    def get_clusters(self) -> E.Either[List[str], Any]:
        return self._k8s_provider.get_clusters(by_regex=self._cluster_regex)

    def cmd(self, cmd: str, cluster_name: str):
        return self._k8s_provider.kubectl(cmd, cluster_name)

    def cmd_all(self, cmd: str):
        def _kubectl_in_cluster(cluster_name: str):
            return self._k8s_provider.kubectl(cmd, cluster_name)

        return self._in_all_clusters(_kubectl_in_cluster)

    def _in_all_clusters(self, action: Callable[[str], E.Either]):
        def _exec_in_clusters(cluster_names: List[str]):
            return chain(cluster_names, lambda cluster_name: action(cluster_name))

        return \
            self._k8s_provider.get_clusters(by_regex=self._cluster_regex) \
            | E.then | (lambda cluster_names: _exec_in_clusters(cluster_names))

    def delete(self, templates: List[dict], cluster_name: str):
        return self._exec_template('delete', templates, cluster_name)

    def apply(self, templates: List[dict], cluster_name: str):
        return self._exec_template('apply', templates, cluster_name)

    def _exec_template(self, action, templates: List[dict], cluster_name: str):
        if len(templates) is 0:
            return E.success()
        return self._file.with_temp_file(
            contents=yaml.combine_templates(templates),
            filename='template.yaml',
            runner=lambda temp_file: self._k8s_provider.kubectl(action+' -f {}'.format(temp_file), cluster_name))


def discover_conn() -> Callable[[Config], KubeCtl]:
    def discover(conf: Config) -> KubeCtl:
        if conf.get_arg('KG_CONN_TYPE') == 'LOCAL':
            return local_kubectl_conn()(conf)
        if conf.get_arg('KG_CONN_TYPE') == 'GKE':
            return gke_conn()(conf)
        if conf.has_arg('KG_SERVICE_ACCOUNT_B64'):
            return gke_conn()(conf)
        else:
            return local_kubectl_conn()(conf)

    return discover


def noop_conn() -> Callable[[Config], KubeCtl]:
    return lambda conf: KubeCtl(conf, NoopProvider(), '')


def local_kubectl_conn() -> Callable[[Config], KubeCtl]:
    return lambda conf: KubeCtl(conf, HostKubectlProvider(conf), '')


def gke_conn(
        cluster_regex: str = None,
        project_id: str = None,
        service_account_b64: str = None) -> Callable[[Config], KubeCtl]:

    def create_kubectl(conf: Config):
        regex = conf.get_arg('KG_CLUSTER_REGEX', cluster_regex)
        if regex is None:
            conf.log.error('gke_conn: cluster_regex required. Either pass cluster_regex or set env var KG_CLUSTER_REGEX')
            sys.exit(1)
        return KubeCtl(conf, GKEProvider(project_id, service_account_b64, conf), regex)

    return create_kubectl

