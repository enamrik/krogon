import krogon.yaml as y
from krogon.exec_context import ExecContext


def from_file(path: str):
    return K8sFileTemplate(path)


class K8sFileTemplate:
    def __init__(self, path):
        self.path = path

    def map_context(self, context: ExecContext) -> ExecContext:
        templates = y.load_all(context.fs.read(self.path))
        context.append_templates(templates)
        return context

    def __str__(self):
        return "K8sFileTemplate({})".format(self.path)
