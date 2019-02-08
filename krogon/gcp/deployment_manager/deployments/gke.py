from krogon.gcp.deployment_manager.deployment_template import DeploymentTemplate
from krogon.gcp.deployment_manager.deployment import Deployment
from krogon.gcp.deployment_manager.deployment_manager import DeploymentManager
from krogon.config import Config
from krogon.logger import Logger
from typing import Callable, Any
import krogon.gcp.deployment_manager.deployment_manager as dm
import krogon.scripts.scripter as scp
import krogon.either as E
import krogon.maybe as M


def cluster(name: str, region: str):
    return K8sClusterDeployment(cluster_name=name, region=region)


class K8sClusterDeployment(Deployment):
    def __init__(self, cluster_name: str, region: str):
        super().__init__(name=cluster_name + '-cluster-stack')
        self.node_pool_name = cluster_name + '-node-pool'
        self.cluster_name = cluster_name
        self.region = region
        self.istio_settings: M.Maybe[dict] = M.Nothing()
        self.vault_settings: M.Maybe[dict] = M.Nothing()

    def with_istio(self, version: str, using_global_load_balancer: bool = False):
        gateway_type = 'NodePort' if using_global_load_balancer else 'LoadBalancer'
        self.istio_settings = M.Just(dict(version=version, gateway_type=gateway_type))
        return self

    def with_vault(self, vault_address: str, vault_token: str, vault_ca_b64: str):
        self.vault_settings = M.Just(dict(
            vault_address=vault_address,
            vault_token=vault_token,
            vault_ca_b64=vault_ca_b64))
        return self

    def run(self,
            config: Config,
            scripter: scp.Scripter,
            d_manager: DeploymentManager):

        return _create_template(self, config.project_id) \
               | E.then | (lambda template: dm.apply(d_manager, config.project_id, self.name, template)) \
               | E.then | (lambda _: _post_deployment(self, scripter))


def _create_template(deployment: K8sClusterDeployment, project: str):

    resources = _build_deployment_resources(project,
                                            deployment.cluster_name,
                                            deployment.node_pool_name,
                                            deployment.region)

    return E.Success(DeploymentTemplate(resources))


def _post_deployment(deployment: K8sClusterDeployment, scripter: scp.Scripter):
    return E.Success() \
           | E.then | (lambda _:
                       deployment.istio_settings
                       | M.from_maybe | dict(
                           if_just=lambda settings: scp.install_istio(scripter,
                                                                      deployment.cluster_name,
                                                                      settings['version'],
                                                                      settings['gateway_type']),
                           if_nothing=lambda: E.Success())
                       ) \
           | E.then | (lambda _:
                       deployment.vault_settings
                       | M.from_maybe | dict(
                           if_just=lambda settings: scp.configure_vault(scripter,
                                                                        deployment.cluster_name,
                                                                        settings['vault_address'],
                                                                        settings['vault_token'],
                                                                        settings['vault_ca_b64']),
                           if_nothing=lambda: E.Success())
                       )


def _build_deployment_resources(project, cluster_name, node_pool_name, region):
    return {
        'resources': [{
            'name': cluster_name,
            'type': 'gcp-types/container-v1beta1:projects.locations.clusters',
            'properties': {
                'projectId': project,
                'parent': 'projects/' + project + '/locations/' + region,
                'cluster': {
                    'maintenancePolicy': {
                        'window': {
                            'dailyMaintenanceWindow': {'startTime': '08:00'}
                        }
                    },
                    'addonsConfig': {
                        'kubernetesDashboard': {'disabled': False},
                        'horizontalPodAutoscaling': {'disabled': False}
                    },
                    'loggingService': 'logging.googleapis.com',
                    'monitoringService': 'monitoring.googleapis.com',
                    'nodePools': [{
                        'name': node_pool_name,
                        'management': {
                            'autoRepair': True,
                            'autoUpgrade': True
                        },
                        'autoscaling': {
                            'enabled': True,
                            'minNodeCount': 1,
                            'maxNodeCount': 10
                        },
                        'initialNodeCount': 1,
                        'config': {
                            'machineType': 'n1-standard-1',
                            'oauthScopes': [
                                'https://www.googleapis.com/auth/compute',
                                'https://www.googleapis.com/auth/logging.write',
                                'https://www.googleapis.com/auth/monitoring',
                                'https://www.googleapis.com/auth/cloud-platform',
                            ],
                            'diskType': 'pd-standard'
                        }
                    }
                    ]
                }
            }
        }
        ]
    }
