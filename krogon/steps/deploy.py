from krogon.steps.step import Step
from krogon.gcp.deployment_manager.deployment import Deployment
from krogon.gcp.deployment_manager.deployments.gke import K8sClusterDeployment
from krogon.gcp.deployment_manager.deployments.postgres import PostgresDeployment
from krogon.logger import Logger
from krogon.config import Config
from krogon.gcp.gcloud import GCloud
import krogon.scripts.scripter as scp
import krogon.either as E


def deploy(deployment: Deployment):
    return DeploymentManagerStep(deployment)


class DeploymentManagerStep(Step):
    def __init__(self, deployment: Deployment):
        super().__init__(name='deploy: ['+deployment.name+']')
        self.deployment = deployment

    def exec(self, scripter: scp.Scripter, gcloud: GCloud, config: Config, logger: Logger):

        if type(self.deployment) == K8sClusterDeployment:
            cur_deployment: K8sClusterDeployment = self.deployment
            return gcloud.deployment_manager(logger) \
                   | E.then | (lambda d_manager: cur_deployment.run(config, scripter, d_manager))

        if type(self.deployment) == PostgresDeployment:
            cur_deployment: PostgresDeployment = self.deployment
            return gcloud.deployment_manager(logger) \
                   | E.then | (lambda d_manager: cur_deployment.run(config, d_manager))

        return E.Failure("Unsupported deployment type: {}".format(self.deployment))
