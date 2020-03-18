from krogon.k8s.template_context import TemplateContext


class K8sKubectl:
    def __init__(self, command: str):
        self.command = command

    def map_context(self, context: TemplateContext):
        cluster_name = context.get_state('cluster_name')
        if cluster_name is not None:
            context.kubectl.cmd(self.command, cluster_name)
        return context


def kubectl(command: str) -> K8sKubectl:
    return K8sKubectl(command)


