from krogon.config import Config
from krogon.k8s.providers.k8s_provider import K8sProvider
from typing import List, Any
import krogon.either as E


class HostKubectlProvider(K8sProvider):
    def __init__(self, conf: Config):
        self._conf = conf

    def get_clusters(self, by_regex: str) -> E.Either[List[str], Any]:
        return E.success(['host-kubectl'])

    def kubectl(self, command: str, cluster_name: str) -> E.Either[None, Any]:
        return self._conf.os_run('kubectl {command}' .format(command=command))

