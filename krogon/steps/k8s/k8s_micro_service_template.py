from typing import List

from krogon.exec_context import ExecContext
from krogon.nullable import nlist, nmap
import krogon.maybe as M
from krogon.steps.k8s.k8s_env_vars import set_environment_variable, add_environment_secret


def micro_service(name: str, image: str, app_port: int):
    return K8sMicroServiceTemplate(name, image, app_port)


class K8sMicroServiceTemplate:
    def __init__(self, name: str, image: str, app_port: int):
        self.name = name
        self.image = image
        self.app_port = app_port
        self.service_port = 80
        self.containers = []
        self.environment_vars = []
        self.command = M.nothing()
        self.sidecars = []
        self.volumes = []
        self.min_replicas: int = 1
        self.max_replicas: int = 3
        self.service_type: str = 'ClusterIP'

    def with_service_type(self, service_type: str):
        self.service_type = service_type
        return self

    def with_service_port(self, port: int):
        self.service_port = port
        return self

    def with_replicas(self, min: int, max: int):
        self.min_replicas = min
        self.max_replicas = max
        return self

    def with_command(self, command_args: List[str]):
        self.command = M.just(command_args)
        return self

    def with_environment_variable(self, name: str, value: str):
        self.environment_vars = set_environment_variable(self.environment_vars, name, value)
        return self

    def with_environment_secret(self, secret_name: str, data: dict):
        self.environment_vars = add_environment_secret(self.environment_vars, secret_name, data)
        return self

    def map_context(self, context: ExecContext) -> ExecContext:
        if context.get_state('cluster_name') is not None:
            self.with_environment_variable('CLUSTER', context.get_state('cluster_name'))

        templates = _get_templates(self.name,
                                   self.service_type,
                                   self.image,
                                   self.app_port,
                                   self.service_port,
                                   self.min_replicas,
                                   self.max_replicas,
                                   self.environment_vars,
                                   self.command)
        context.append_templates(templates)
        return context


def _get_templates(name: str,
                   service_type: str,
                   image: str,
                   app_port: int,
                   service_port: int,
                   min_replicas: int,
                   max_replicas: int,
                   env_vars: List[str],
                   command: M.Maybe[List[str]]) \
        -> List[dict]:
    return nlist([
        {
            'kind': 'Service',
            'apiVersion': 'v1',
            'metadata': {'name': name},
            'spec': {
                'type': service_type,
                'selector': {'app': _app_name(name)},
                'ports': [{'protocol': 'TCP', 'port': service_port, 'targetPort': app_port}]
            }
        },
        {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': _deployment_name(name),
                'labels': {'app': _app_name(name)},
            },
            'spec': {
                'replicas': 1,
                'selector': {
                    'matchLabels': {
                        'app': _app_name(name)
                    }
                },
                'template': {
                    'metadata': {
                        'annotations': {
                            'traffic.sidecar.istio.io/excludeOutboundIPRanges': "0.0.0.0/0",
                            "sidecar.istio.io/inject": "true"},
                        'labels': {'app': _app_name(name)}},
                    'spec': {
                        'containers': nlist([
                            nmap({
                                'name': _app_name(name),
                                'image': image,
                                'ports': [{'containerPort': app_port}],
                                'env': env_vars
                            }).append_if_value(
                                'command', command).to_map()
                        ]).to_list(),
                        'volumes': nlist([]).to_list()
                    }
                }
            }
        },
        {
            'apiVersion': 'autoscaling/v1',
            'kind': 'HorizontalPodAutoscaler',
            'metadata': {'name': _horizontal_pod_autoscaler_name(name)},
            'spec': {
                'scaleTargetRef': {
                    'apiVersion': 'apps/v1',
                    'kind': 'Deployment',
                    'name': _deployment_name(name)
                },
                'minReplicas': min_replicas,
                'maxReplicas': max_replicas,
                'targetCPUUtilizationPercentage': 50
            }
        }
    ]).to_list()


def _horizontal_pod_autoscaler_name(service_name: str):
    return service_name + '-hpa'


def _deployment_name(service_name: str):
    return service_name + '-dp'


def _app_name(service_name: str):
    return service_name + '-app'
