import krogon.yaml as y
from krogon.k8s.template_context import TemplateContext


def from_file(path: str):
    return K8sFileTemplate(path)


class K8sFileTemplate:
    def __init__(self, path):
        self.path = path

    def map_context(self, context: TemplateContext) -> TemplateContext:
        templates = y.load_all(context.config.fs.read(self.path))
        context.append_templates(templates)
        return context

    def __str__(self):
        return "K8sFileTemplate({})".format(self.path)
