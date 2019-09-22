import krogon.yaml as y
from typing import List
from krogon.exec_context import ExecContext


def template_file(path: str):
    return K8sTemplateFile(path)


class K8sTemplateFile:
    def __init__(self, path):
        self.path = path

    def run(self, context: ExecContext) -> List[dict]:
        return y.load_all(context.fs.read(self.path))
