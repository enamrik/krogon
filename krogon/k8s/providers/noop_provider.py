import krogon.either as E
from krogon.k8s.providers.k8s_provider import K8sProvider


class NoopProvider(K8sProvider):
    def get_clusters(self, by_regex: str):
        return E.success(['Noop'])

    def kubectl(self, command: str, cluster_name: str):
        return E.success()

    def gen_kubeconfig_file(self, cluster_name: str):
        return E.success('')
