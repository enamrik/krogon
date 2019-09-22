from base64 import b64encode
from typing import List


def secret(name: str, data: dict, already_b64=False):
    return K8sSecretTemplate(name, data, already_b64)


class K8sSecretTemplate:
    def __init__(self, name: str, secret_data: dict, already_b64: bool):
        super().__init__()

        to_base64 = lambda value: value \
            if already_b64 \
            else b64encode(value.encode('utf-8')).decode('utf-8')

        self.template = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {'name': name},
            'type': 'Opaque',
            'data': {key: to_base64(value) for key, value in secret_data.items()}
        }

    def run(self) -> List[dict]:
        return [self.template]
