from typing import List


def volume_claim(name: str):
    return K8sPersistentVolumeClaimTemplate(name)


class K8sPersistentVolumeClaimTemplate:
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.size = '2Gi'

    def with_size(self, size: str):
        self.size = size
        return self

    def run(self) -> List[dict]:
        return [{
            'apiVersion': 'v1',
            'kind': 'PersistentVolumeClaim',
            'metadata': {'name': self.name},
            'spec': {
                'accessModes': ['ReadWriteOnce'],
                'volumeMode': 'Filesystem',
                'resources': {
                   'requests': {'storage': self.size}
                }
            }
        }]

