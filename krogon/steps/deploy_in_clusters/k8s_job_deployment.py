from krogon.steps.deploy_in_clusters.k8s_deployment import K8sDeployment
from krogon.nullable import nlist, nmap
from typing import List, Any
from krogon.steps.deploy_in_clusters.postgres_proxy import PostgresProxy
from krogon.config import Config
import krogon.k8s.kubectl as k
import krogon.either as E
import krogon.maybe as M


def create_job(name: str, image: str, version: str):
    return K8sJobDeployment(name, image, version)


class K8sJobDeployment(K8sDeployment):
    def __init__(self, name: str, image: str, version: str):
        super().__init__()
        self.name = name
        self.image = image
        self.version = version
        self.command = M.Nothing()
        self.postgres_proxy_settings = M.Nothing()
        self.environment_vars = []
        self.schedule = '* * * * *'
        self.suspend = True

    def with_environment_variable(self, name: str, value: str):
        self.environment_vars = self.environment_vars + [{'name': name, 'value': value}]
        return self

    def with_schedule(self, schedule: str):
        self.schedule = schedule
        self.suspend = False
        return self

    def with_command(self, command: str):
        self.command = M.Just(command)
        return self

    def with_postgres(self, db_name: str, db_region: str, service_account_b64: str):
        self.postgres_proxy_settings = M.Just(dict(
            db_name=db_name, db_region=db_region, service_account_b64=service_account_b64))
        return self

    def with_secret(self, name: str, keys: List[str]):
        def _key_to_secret_ref(key):
            return {
                'name': key,
                'valueFrom': {'secretKeyRef': {'name': name, 'key': key}}}

        secret_vars = list(map(lambda key: _key_to_secret_ref(key), keys))
        self.environment_vars = self.environment_vars + secret_vars
        return self

    def exec(self, kubectl: k.KubeCtl, config: Config, cluster_tag: str) -> E.Either[Any, Any]:
        templates = _get_templates(self.name, self.image, self.schedule, self.suspend, self.version,
                                   self.environment_vars,
                                   _get_postgres_proxy(config.project_id, self.name, self.postgres_proxy_settings),
                                   self.command)

        return k.apply(kubectl, templates, cluster_tag)


def _get_templates(name: str, image: str, schedule: str, suspend: bool, version: str, env_vars: List[str],
                   postgres_proxy: M.Maybe[PostgresProxy],
                   command: M.Maybe[List[str]]) -> List[dict]:
    return nlist([
        {
            'kind': 'CronJob',
            'apiVersion': 'batch/v1beta1',
            'metadata': {'name': name},
            'spec': {
                'suspend': suspend,
                'concurrencyPolicy': 'Forbid',
                'schedule': schedule,
                'jobTemplate': {'spec': {
                    'template': {
                        'metadata': {
                            'annotations': {
                                'traffic.sidecar.istio.io/excludeOutboundIPRanges': "0.0.0.0/0",
                                "sidecar.istio.io/inject": "false"}
                        },
                        'spec': {
                            'containers': nlist([
                                nmap({
                                    'name': name,
                                    'image': image + ':' + version,
                                    'env': env_vars
                                }).append_if_value(
                                    'command', command).to_map()
                            ]).append_if_value(
                                M.map(postgres_proxy, lambda x: x.container())).to_list(),
                            'volumes': nlist([]).append_if_value(M.map(postgres_proxy, lambda x: x.volume())).to_list(),
                            'restartPolicy': 'Never'
                        }
                    },
                    'backoffLimit': 0
                }},
            }
        }
    ]).append_if_value(
        M.map(postgres_proxy, lambda x: x.credential_file_secret())) \
        .to_list()


def _get_postgres_proxy(project: str, service_name: str, postgres_proxy_settings: M.Maybe[dict]):
    return postgres_proxy_settings \
           | M.map | (lambda settings: PostgresProxy(project,
                                                     service_name,
                                                     settings['db_name'],
                                                     settings['db_region'],
                                                     settings['service_account_b64']))

