from krogon.gcp.k8s.k8s_deployment import K8sDeployment
from krogon.nullable import nlist, nmap
from krogon.file_system import FileSystem
from typing import List, Any
from krogon.gcp.k8s.postgres_proxy import PostgresProxy
import krogon.scripts.scripter as scp
from .combine_templates import combine_templates
import krogon.either as E
import krogon.maybe as M


def create_job(name: str, image: str, version: str):
    return K8sJobDeployment(name, image, version)


class K8sJobDeployment(K8sDeployment):
    def __init__(self, name: str, image: str, version: str):
        self.name = name
        self.image = image
        self.version = version
        self.command = M.Nothing()
        self.postgres_proxy_settings = M.Nothing()
        self.environment_vars = []

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

    def exec(self, cluster_tag: str, scripter: scp.Scripter, fs: FileSystem) -> E.Either[Any, Any]:
        templates = _get_templates(self.name, self.image, self.version,
                                   self.environment_vars,
                                   _get_postgres_proxy(scripter.project, self.name, self.postgres_proxy_settings),
                                   self.command)

        return fs.with_temp_file(
            contents=combine_templates(templates),
            filename='template',
            runner=lambda temp_file: scp.kubectl_all_by_tag(scripter,
                                                            cluster_tag,
                                                            'apply -f {}'.format(temp_file)))


def _get_templates(name: str, image: str, version: str, env_vars: List[str],
                   postgres_proxy: M.Maybe[PostgresProxy],
                   command: M.Maybe[List[str]]) -> List[dict]:
    return nlist([
        {
            'kind': 'CronJob',
            'apiVersion': 'batch/v1beta1',
            'metadata': {'name': name},
            'spec': {
                'suspend': True,
                'concurrencyPolicy': 'Forbid',
                'schedule': '* * * * *',
                'jobTemplate': {'spec': {
                    'template': {
                        'metadata': {
                            'annotations': {'traffic.sidecar.istio.io/excludeOutboundIPRanges': "0.0.0.0/0"},
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

