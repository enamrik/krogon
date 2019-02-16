from typing import List
from krogon.steps.step import Step
from krogon.gcp.k8s.k8s_secret_deployment import K8sSecretDeployment
from krogon.gcp.k8s.k8s_deployment import K8sDeployment
from krogon.gcp.k8s.k8s_micro_service_deployment import K8sMicroServiceDeployment
from krogon.gcp.k8s.k8s_job_deployment import K8sJobDeployment
from krogon.gcp.k8s.kubectl import KubeCtl
from krogon.either_ext import chain
from krogon.file_system import FileSystem
import krogon.scripts.scripter as scp
import krogon.either as E


def deploy_in_clusters(with_tag: str, run: List[K8sDeployment]):
    return K8sStep(cluster_tag=with_tag, k8s_deployments=run)


class K8sStep(Step):
    def __init__(self, cluster_tag: str, k8s_deployments: List[K8sDeployment]):
        super().__init__(name='Kubernetes Apply: ['+cluster_tag+']')
        self.cluster_tag = cluster_tag
        self.k8s_deployments = k8s_deployments

    def exec(self, kubectl: KubeCtl) -> E.Either:
        return _exec_in_clusters(self.cluster_tag, self.k8s_deployments, kubectl)


def _exec_in_clusters(cluster_tag: str,
                      k8s_deployments: List[K8sDeployment],
                      kubectl: KubeCtl):

    def _exec_deployment(deployment: K8sDeployment):

        if type(deployment) == K8sSecretDeployment:
            cur_deployment: K8sSecretDeployment = deployment
            return cur_deployment.exec(kubectl, cluster_tag)

        if type(deployment) == K8sMicroServiceDeployment:
            cur_deployment: K8sMicroServiceDeployment = deployment
            return cur_deployment.exec(kubectl, cluster_tag)

        if type(deployment) == K8sJobDeployment:
            cur_deployment: K8sJobDeployment = deployment
            return cur_deployment.exec(kubectl, cluster_tag)

        return E.Failure("Unsupported deployment type: {}".format(type(deployment)))

    return chain(k8s_deployments, _exec_deployment)
