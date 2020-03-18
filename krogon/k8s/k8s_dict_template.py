from typing import List


def from_dicts(dicts: List[dict]):
    return K8sDictTemplate(dicts)


class K8sDictTemplate:
    def __init__(self, dicts: List[dict]):
        self.dicts = dicts

    def run(self) -> List[dict]:
        return self.dicts

    def __str__(self):
        return "K8sDictTemplate()"
