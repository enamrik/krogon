from typing import List
from krogon.exec_context import ExecContext
from krogon.nullable import nmap
from krogon.steps.k8s.k8s_container import K8sContainer, app_name
import krogon.maybe as M


def deployment(name: str):
    return K8sDeploymentTemplate(name)


class K8sDeploymentTemplate:
    def __init__(self, name: str):
        self.name = name
        self.replicas = 1
        self.containers = []
        self.init_containers: M.Maybe[List[K8sContainer]] = M.nothing()
        self.volumes = []
        self.strategy = {
            'type': 'RollingUpdate',
            'rollingUpdate': {
                'maxSurge': '25%',
                'maxUnavailable': '25%'
            }
        }

    def with_init_containers(self, init_containers: List[K8sContainer]):
        self.init_containers = M.just(init_containers)
        return self

    def with_ensure_only_one(self):
        self.replicas = 1
        self.strategy = {'type': 'Recreate'}
        return self

    def with_rolling_update(self, max_surge: str, max_unavailable: str):
        self.strategy = {
            'type': 'RollingUpdate',
            'rollingUpdate': {
                'maxSurge': max_surge,
                'maxUnavailable': max_unavailable
            }
        }
        return self

    def with_empty_volume(self, name: str):
        self.volumes.append({'name': name, 'emptyDir': {}})
        return self

    def with_volume_claim(self, name: str, claim_name: str):
        self.volumes.append({'name': name,
                             'persistentVolumeClaim': {'claimName': claim_name}})
        return self

    def with_replicas(self, count):
        self.replicas = count
        return self

    def with_container(self, container: K8sContainer):
        self.containers.append(container)
        return self

    def with_containers(self, containers: List[K8sContainer]):
        self.containers = containers
        return self

    def map_context(self, context: ExecContext) -> ExecContext:
        context.append_templates([
            {
                'kind': 'Deployment',
                'apiVersion': 'apps/v1',
                'metadata': {
                    'name': _deployment_name(self.name),
                    'labels': {'app': app_name(self.name)},
                },
                'spec': {
                    'strategy': self.strategy,
                    'replicas': self.replicas,
                    'selector': {
                        'matchLabels': {
                            'app': app_name(self.name)
                        }
                    },
                    'template': {
                        'metadata': {
                            'annotations': {
                                "sidecar.istio.io/inject": "false"},
                            'labels': {'app': app_name(self.name)}},
                        'spec': nmap({
                            'containers': list(map(lambda x: x.get_template(context), self.containers)),
                            'volumes': self.volumes
                        }).append_if_value('initContainers',
                                           M.map(
                                               self.init_containers,
                                               lambda init_containers: list(map(
                                                   lambda x: x.get_template(context), init_containers))))
                            .to_map()
                    }
                }
            },
        ])
        return context


def _deployment_name(service_name: str):
    return service_name + '-dp'


