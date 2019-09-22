from krogon.exec_context import ExecContext


def template_file(path: str):
    return K8sTemplateFile(path)


class K8sTemplateFile:
    def __init__(self, path):
        self.path = path

    def to_string(self, context: ExecContext) -> str:
        return context.fs.read(self.path)
