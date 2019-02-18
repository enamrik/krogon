from krogon.gcp.deployment_manager.deployment_template import DeploymentTemplate
from krogon.steps.deploy.deployment import Deployment
from krogon.config import Config
from krogon.gcp.deployment_manager.deployment_manager import DeploymentManager
import krogon.gcp.deployment_manager.deployment_manager as dm


def postgres(db_name, username, password, region: str):
    return PostgresDeployment(db_name, username, password, region)


def instance_connection_name(project: str, db_name: str, db_region: str):
    return project+':'+db_region+':'+_db_instance_name(db_name)


class PostgresDeployment(Deployment):
    def __init__(self, db_name: str, username: str, password: str, region: str):
        super().__init__(name=db_name + '-db-stack')
        self.db_name = db_name
        self.username = username
        self.password = password
        self.region = region

    def run(self, config: Config, d_manager: DeploymentManager):
        resources = _build_deployment_resources(self.db_name, self.username, self.password, self.region)

        return dm.apply(d_manager, config.project_id, self.name, DeploymentTemplate(resources))


def _build_deployment_resources(db_name: str, username: str, password: str, region: str):
    instance_name = _db_instance_name(db_name)
    return {
        'resources': [
            {
                'name': instance_name,
                'type': 'gcp-types/sqladmin-v1beta4:instances',
                'properties': {
                    'region': region,
                    'backendType': 'SECOND_GEN',
                    'databaseVersion': 'POSTGRES_9_6',
                    'settings': {
                        'tier': 'db-custom-1-3840',
                        'backupConfiguration': {'enabled': True}
                    }
                }
            },
            {
                'name': db_name,
                'type': 'gcp-types/sqladmin-v1beta4:databases',
                'metadata': {'dependsOn': [instance_name]},
                'properties': {
                    'name': db_name,
                    'instance': '$(ref.' + instance_name + '.name)',
                    'charset': 'utf8'
                }
            },
            {
                'name': username,
                'type': 'gcp-types/sqladmin-v1beta4:users',
                'metadata': {'dependsOn': [instance_name, db_name]},
                'properties': {
                    'name': username,
                    'password': password,
                    'host': '',
                    'instance': '$(ref.' + instance_name + '.name)',
                }
            }
        ]
    }


def _db_instance_name(db_name: str):
    return db_name + '-instance'

