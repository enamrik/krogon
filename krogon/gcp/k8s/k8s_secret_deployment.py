from krogon.gcp.k8s.k8s_deployment import K8sDeployment
from base64 import b64encode
import krogon.gcp.k8s.kubectl as k


def create_secret(name: str, data: dict):
    return K8sSecretDeployment(name, data)


class K8sSecretDeployment(K8sDeployment):
    def __init__(self, name: str, secret_data: dict):
        super().__init__()
        self.template = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {'name': name},
            'type': 'Opaque',
            'data': {key: b64encode(value.encode('utf-8')) for key, value in secret_data.items()}
        }

    def exec(self, kubectl: k.KubeCtl, cluster_tag: str):
        return k.apply(kubectl, [self.template], cluster_tag)

