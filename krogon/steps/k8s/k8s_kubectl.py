import krogon.either as E
import krogon.k8s.kubectl as k
import krogon.gcp.gcloud as g
from krogon.either_ext import chain
from krogon.exec_context import ExecContext


class K8sKubectl:
    def __init__(self, command: str):
        self.command = command

    def map_context(self, context: ExecContext):

        def _exec_command(cluster_name):
            return k.kubectl(context.kubectl, cluster_name, self.command)

        if not context.config.output_template:
            cluster_tags = context.get_state('cluster_tags')

            g.get_clusters(context.gcloud, by_tags=cluster_tags) \
                | E.then | (lambda cluster_names: chain(cluster_names, _exec_command))

        return context


def kubectl(command: str) -> K8sKubectl:
    return K8sKubectl(command)


