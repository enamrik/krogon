from krogon.steps.step import Step
from krogon.steps.deploy.deployment import Deployment
from krogon.steps.deploy.gke_cluster.gke_cluster_deployment import GkeClusterDeployment
from krogon.steps.deploy.postgres.postgres_deployment import PostgresDeployment
from krogon.logger import Logger
from krogon.config import Config
from krogon.gcp.gcloud import GCloud
from krogon.vault.vault import Vault
from krogon.istio.istio import Istio
from krogon.ci.gocd.deploy_gocd import DeployGoCD
import krogon.gcp.deployment_manager.deployment_manager as dm
import krogon.either as E


def deploy(deployment: Deployment):
    return DeploymentManagerStep(deployment)


class DeploymentManagerStep(Step):
    def __init__(self, deployment: Deployment):
        super().__init__(name='deploy -> '+deployment.__class__.__name__+'')
        self.deployment = deployment

    def exec(self,
             d_gocd: DeployGoCD,
             vault: Vault,
             istio: Istio,
             gcloud: GCloud,
             config: Config,
             logger: Logger):

        logger.info('Deploying stack: '+self.deployment.name)

        if type(self.deployment) == GkeClusterDeployment:
            cur_deployment: GkeClusterDeployment = self.deployment
            return dm.new_deployment_manager(gcloud, logger.add_prefix('['+self.deployment.name+']')) \
                   | E.then | (lambda d_manager:
                               cur_deployment.run(config, d_gocd, vault, istio, d_manager, logger))

        if type(self.deployment) == PostgresDeployment:
            cur_deployment: PostgresDeployment = self.deployment
            return dm.new_deployment_manager(gcloud, logger) \
                   | E.then | (lambda d_manager: cur_deployment.run(config, d_manager))

        return E.Failure("Unsupported deployment type: {}".format(self.deployment))
