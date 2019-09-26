from typing import List


def yaml_as_dicts(dicts: List[dict]):
    return K8sDictTemplate(dicts)


class K8sDictTemplate:
    def __init__(self, dicts: List[dict]):
        self.dicts = dicts

    def run(self) -> List[dict]:
        return self.dicts
