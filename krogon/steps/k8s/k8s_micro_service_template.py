from typing import List, Any
from python_maybe.nullable import nlist, nmap
import python_maybe.maybe as M
import krogon.yaml as y


def micro_service(name: str, image: str, port: int):
    return K8sMicroServiceTemplate(name, image, port)


class K8sMicroServiceTemplate:
    def __init__(self, name: str, image: str, app_port: int):
        self.name = name
        self.image = image
        self.app_port = app_port
        self.service_port = 80
        self.containers = []
        self.environment_vars = []
        self.postgres_proxy_settings = M.nothing()
        self.command = M.nothing()
        self.sidecars = []
        self.volumes = []
        self.min_replicas: int = 1
        self.max_replicas: int = 10

    def with_service_port(self, port):
        self.service_port = port
        return self

    def with_replicas(self, min: int, max: int):
        self.min_replicas = min
        self.max_replicas = max
        return self

    def with_command(self, command_args: List[str]):
        self.command = M.just(command_args)
        return self

    def with_postgres(self, db_name: str, db_region: str, service_account_b64: str):
        self.postgres_proxy_settings = M.just(dict(
            db_name=db_name, db_region=db_region, service_account_b64=service_account_b64))
        return self

    def with_environment_variable(self, name: str, value: str):
        self.environment_vars = self.environment_vars + [{'name': name, 'value': value}]
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
        return _get_templates(self.name,
                              self.image,
                              self.app_port,
                              self.service_port,
                              self.min_replicas,
                              self.max_replicas,
                              self.environment_vars,
                              self.command)


def _get_templates(name: str,
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
                        'annotations': {'traffic.sidecar.istio.io/excludeOutboundIPRanges': "0.0.0.0/0"},
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
