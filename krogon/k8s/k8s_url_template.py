import krogon.yaml as y
import requests

from krogon.k8s.template_context import TemplateContext


def from_url(url: str):
    return K8sUrlTemplate(url)


class K8sUrlTemplate:
    def __init__(self, url):
        self.url = url

    def map_context(self, context: TemplateContext) -> TemplateContext:
        req = requests.get(self.url)
        if req.status_code != 200:
            raise Exception("Request fail {} failed: {}".format(self.url, req.status_code))

        templates = y.load_all(req.text)
        context.append_templates(templates)
        return context

    def __str__(self):
        return "K8sUrlTemplate({})".format(self.url)
