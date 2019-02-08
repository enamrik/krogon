from krogon.gcp.k8s.k8s_deployment import K8sDeployment
import krogon.scripts.scripter as scp
from krogon.file_system import FileSystem
from base64 import b64encode
import krogon.yaml as yaml


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

    def exec(self, cluster_tag: str, scripter: scp.Scripter, fs: FileSystem):
        return fs.with_temp_file(
            contents=yaml.dump(self.template, default_flow_style=False),
            filename='template',
            runner=lambda temp_file: scp.kubectl_all_by_tag(scripter,
                                                            cluster_tag,
                                                            'apply -f {}'.format(temp_file)))

