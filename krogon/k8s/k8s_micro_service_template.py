from typing import List, Optional

from krogon.k8s.k8s_container import K8sContainer
from krogon.k8s.k8s_env_vars import set_environment_variable, add_environment_secret
from krogon.k8s.template_context import TemplateContext
from krogon.nullable import nlist, nmap
import krogon.maybe as M
import krogon.nullable as N


def micro_service(name: str, image: str, app_port: int):
    return K8sMicroServiceTemplate(name, image, app_port)


class K8sMicroServiceTemplate:
    def __init__(self, name: str, image: str, app_port: int):
        self.name = name
        self.image = image
        self.app_port = app_port
        self.service_port = 80
        self.environment_vars = []
        self.command = M.nothing()
        self.resources = M.nothing()
        self.sidecars: List[K8sContainer] = []
        self.init_containers: M.Maybe[List[K8sContainer]] = M.nothing()
        self.volumes = []
        self.min_replicas: int = 1
        self.max_replicas: int = 3
        self.cpu_threshold_percentage: int = 50
        self.service_type: str = 'ClusterIP'
        self.annotations: dict = {}
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
        self.min_replicas = 1
        self.max_replicas = 1
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

    def with_sidecar(self, container: K8sContainer):
        self.sidecars.append(container)
        return self

    def with_annotations(self, annotations: dict):
        self.annotations = {**self.annotations, **annotations}
        return self

    def with_empty_volume(self, name: str, mount_path: str):
        self.volumes.append({
            'volume': {'name': name, 'emptyDir': {}},
            'mount': {'name': name, 'mountPath': mount_path}})
        return self

    def with_volume_claim(self, name: str, claim_name: str, mount_path: str):
        self.volumes.append({
            'volume': {
                'name': name,
                'persistentVolumeClaim': {'claimName': claim_name}},
            'mount': {'name': name, 'mountPath': mount_path}})
        return self

    def with_service_type(self, service_type: str):
        self.service_type = service_type
        return self

    def with_service_port(self, port: int):
        self.service_port = port
        return self

    def with_replicas(self, min: int, max: int, cpu_threshold_percentage: int = 50):
        self.min_replicas = min
        self.max_replicas = max
        self.cpu_threshold_percentage = cpu_threshold_percentage
        return self

    def with_resources(self,
                       cpu_request: Optional[str] = None,
                       memory_request: Optional[str] = None,
                       cpu_limit: Optional[str] = None,
                       memory_limit: Optional[str] = None):

        def set_resource(cpu, memory):
            return N.nmap({}) \
                .append_if_value('cpu', cpu) \
                .append_if_value('memory', memory) \
                .to_maybe()

        requests = set_resource(cpu_request, memory_request)
        limits = set_resource(cpu_limit, memory_limit)
        self.resources = N.nmap({}) \
            .append_if_value('requests', requests) \
            .append_if_value('limits', limits) \
            .to_maybe()

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

    def map_context(self, context: TemplateContext) -> TemplateContext:
        if context.get_state('cluster_name') is not None:
            self.with_environment_variable('CLUSTER', context.get_state('cluster_name'))

        templates = nlist([
            {
                'kind': 'Service',
                'apiVersion': 'v1',
                'metadata': {'name': self.name},
                'spec': {
                    'type': self.service_type,
                    'selector': {'app': _app_name(self.name)},
                    'ports': [{'protocol': 'TCP', 'port': self.service_port, 'targetPort': self.app_port}]
                }
            },
            {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': _deployment_name(self.name),
                    'labels': {'app': _app_name(self.name)},
                },
                'spec': {
                    'replicas': self.min_replicas,
                    'strategy': self.strategy,
                    'selector': {
                        'matchLabels': {
                            'app': _app_name(self.name)
                        }
                    },
                    'template': {
                        'metadata': {
                            'annotations': self.annotations,
                            'labels': {'app': _app_name(self.name)}},
                        'spec': nmap({
                            'containers': nlist([
                                nmap({
                                    'name': _app_name(self.name),
                                    'image': self.image,
                                    'ports': [{'containerPort': self.app_port}],
                                    'env': self.environment_vars,
                                    'volumeMounts': list(map(lambda x: x['mount'], self.volumes))
                                }).append_if_value(
                                    'command', self.command)
                                    .append_if_value(
                                    'resources', self.resources)
                                    .to_map()
                            ]).append_all(
                                list(map(lambda x: x.get_template(context), self.sidecars))).to_list(),
                            'volumes': list(map(lambda x: x['volume'], self.volumes))
                        }).append_if_value('initContainers', self.init_containers)
                            .to_map()
                    }
                }
            },
            {
                'apiVersion': 'autoscaling/v1',
                'kind': 'HorizontalPodAutoscaler',
                'metadata': {'name': _horizontal_pod_autoscaler_name(self.name)},
                'spec': {
                    'scaleTargetRef': {
                        'apiVersion': 'apps/v1',
                        'kind': 'Deployment',
                        'name': _deployment_name(self.name)
                    },
                    'minReplicas': self.min_replicas,
                    'maxReplicas': self.max_replicas,
                    'targetCPUUtilizationPercentage': self.cpu_threshold_percentage
                }
            }
        ]).to_list()
        context.append_templates(templates)
        return context


def _horizontal_pod_autoscaler_name(service_name: str):
    return service_name + '-hpa'


def _deployment_name(service_name: str):
    return service_name + '-dp'


def _app_name(service_name: str):
    return service_name + '-app'
