from krogon.gcp.deployment_manager.deployment_template import DeploymentTemplate
from krogon.steps.deploy.deployment import Deployment
from krogon.gcp.deployment_manager.deployment_manager import DeploymentManager
from krogon.istio.https import IstioHttpsConfig, LetsEncryptConfig, HttpsCertConfig
from krogon.config import Config
from typing import Optional
from krogon.logger import Logger
import krogon.gcp.deployment_manager.deployment_manager as dm
import krogon.vault.vault as v
import krogon.istio.istio as i
import krogon.ci.gocd.deploy_gocd as cd
import krogon.either as E
import krogon.maybe as M


def gke_cluster(name: str, region: str):
    return GkeClusterDeployment(cluster_name=name, region=region)


class HttpsConfig:
    def __init__(self):
        self.istio_https_config: M.Maybe[IstioHttpsConfig] = M.Nothing()

    def with_lets_encrypt(self, email: str, dns_host: str):
        self.istio_https_config = M.Just(LetsEncryptConfig(email=email, dns_host=dns_host))
        return self

    def with_cert(self, server_certificate_path: str, private_key_path: str):
        self.istio_https_config = M.Just(HttpsCertConfig(server_certificate_path=server_certificate_path,
                                                         private_key_path=private_key_path))
        return self


class GkeClusterDeployment(Deployment):
    def __init__(self, cluster_name: str, region: str):
        super().__init__(name=cluster_name + '-cluster-stack')
        self.node_pool_name = cluster_name + '-node-pool'
        self.cluster_name = cluster_name
        self.region = region
        self.istio_settings: M.Maybe[dict] = M.Nothing()
        self.vault_settings: M.Maybe[dict] = M.Nothing()
        self.gocd_settings: M.Maybe[dict] = M.Nothing()

    def with_istio(self,
                   version: str,
                   using_global_load_balancer: bool = False,
                   auto_sidecar_injection: bool = True,
                   https: Optional[HttpsConfig] = None):

        gateway_type = 'NodePort' if using_global_load_balancer else 'LoadBalancer'
        self.istio_settings = M.Just(dict(version=version,
                                          gateway_type=gateway_type,
                                          auto_sidecar_injection=auto_sidecar_injection,
                                          https=https))
        return self

    def with_vault(self, vault_address: str, vault_token: str, vault_ca_b64: str):
        self.vault_settings = M.Just(dict(
            vault_address=vault_address,
            vault_token=vault_token,
            vault_ca_b64=vault_ca_b64))
        return self

    def with_gocd(self, root_username: str,
                  root_password: str,
                  git_id_rsa_path: str,
                  git_id_rsa_pub_path: str,
                  git_host: str,
                  gateway_host: Optional[str]):

        self.gocd_settings = M.Just(dict(
            root_username=root_username,
            root_password=root_password,
            git_id_rsa_path=git_id_rsa_path,
            git_id_rsa_pub_path=git_id_rsa_pub_path,
            git_host=git_host,
            gateway_host=gateway_host))
        return self

    def run(self,
            config: Config,
            d_gocd: cd.DeployGoCD,
            vault: v.Vault,
            istio: i.Istio,
            d_manager: DeploymentManager,
            log: Logger):

        return _create_template(self, config.project_id) \
               | E.then | (lambda template: dm.create_or_update(d_manager,
                                                                config.project_id,
                                                                self.name,
                                                                create_template=template['create'],
                                                                update_template=template['update'])) \
               | E.then | (lambda _: _post_deployment(self, d_gocd, vault, istio))


def _post_deployment(deployment: GkeClusterDeployment,
                     d_gocd: cd.DeployGoCD,
                     vault: v.Vault,
                     istio: i.Istio):

    return E.Success() \
           | E.then | (lambda _:
                       deployment.istio_settings
                       | M.from_maybe | dict(
                           if_just=lambda settings:
                               i.install_istio(istio,
                                               deployment.cluster_name,
                                               settings['version'],
                                               settings['gateway_type'],
                                               settings['auto_sidecar_injection'],
                                               https_config=settings['https']),
                           if_nothing=lambda: E.Success())
                       ) \
           | E.then | (lambda _:
                       deployment.vault_settings
                       | M.from_maybe | dict(
                           if_just=lambda settings: v.configure_vault(vault,
                                                                      deployment.cluster_name,
                                                                      settings['vault_address'],
                                                                      settings['vault_token'],
                                                                      settings['vault_ca_b64']),
                           if_nothing=lambda: E.Success())
                       ) \
           | E.then | (lambda _:
                       deployment.gocd_settings
                       | M.from_maybe | dict(
                           if_just=lambda settings: cd.deploy_gocd(d_gocd,
                                                                   settings['root_username'],
                                                                   settings['root_password'],
                                                                   settings['git_id_rsa_path'],
                                                                   settings['git_id_rsa_pub_path'],
                                                                   settings['git_host'],
                                                                   settings['gateway_host'],
                                                                   deployment.cluster_name),
                           if_nothing=lambda: E.Success())
                       )


def _create_template(deployment: GkeClusterDeployment, project: str):

    return E.Success(dict(
        create=DeploymentTemplate(_build_create_deployment_resources(project,
                                                                     deployment.cluster_name,
                                                                     deployment.node_pool_name,
                                                                     deployment.region)),
        update=DeploymentTemplate.empty()))


def _build_create_deployment_resources(project, cluster_name, node_pool_name, region):
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
