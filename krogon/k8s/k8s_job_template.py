from krogon.k8s.k8s_env_vars import add_environment_secret
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

    def with_environment_secret(self, secret_name: str, data: map):
        self.environment_vars = add_environment_secret(self.environment_vars, secret_name, data)
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
