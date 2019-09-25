from krogon.nullable import nlist, nmap
from typing import List
import krogon.maybe as M


def cron_job(name: str, image: str):
    return K8sJobTemplate(name, image)


class K8sJobTemplate:
    def __init__(self, name: str, image: str):
        super().__init__()
        self.name = name
        self.image = image
        self.command = M.nothing()
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
        self.command = M.just(command)
        return self

    def with_secret(self, name: str, keys: List[str]):
        def _key_to_secret_ref(key):
            return {
                'name': key,
                'valueFrom': {'secretKeyRef': {'name': name, 'key': key}}}

        secret_vars = list(map(lambda key: _key_to_secret_ref(key), keys))
        self.environment_vars = self.environment_vars + secret_vars
        return self

    def with_environment_secret(self, secret_name: str, data: map):
        def _key_to_secret_ref(env_name, secret_content_key):
            return {
                'name': env_name,
                'valueFrom': {'secretKeyRef': {'name': secret_name, 'key': secret_content_key}}}
        secret_vars = list(map(lambda item: _key_to_secret_ref(item[0], item[1]), data.items()))
        self.environment_vars = self.environment_vars + secret_vars
        return self

    def run(self) -> List[dict]:
        return _get_templates(self.name, self.image,
                              self.schedule, self.suspend,
                              self.environment_vars,
                              self.command)


def _get_templates(name: str, image: str,
                   schedule: str, suspend: bool, env_vars: List[str],
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
                                    'image': image,
                                    'env': env_vars
                                }).append_if_value(
                                    'command', command).to_map()
                            ]).to_list(),
                            'volumes': nlist([]).to_list(),
                            'restartPolicy': 'Never'
                        }
                    },
                    'backoffLimit': 0
                }},
            }
        }
    ]).to_list()
