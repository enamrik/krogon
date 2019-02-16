from krogon.gcp.k8s.k8s_deployment import K8sDeployment
from typing import List, Any
from krogon.gcp.k8s.postgres_proxy import PostgresProxy
from krogon.nullable import nlist, nmap
import krogon.gcp.k8s.kubectl as k
import krogon.either as E
import krogon.maybe as M


def create_micro_service(name: str, image: str, version: str, port: int):
    return K8sMicroServiceDeployment(name, image, version, port)


class K8sMicroServiceDeployment(K8sDeployment):
    def __init__(self, name: str, image: str, version: str, port: int):
        super().__init__()
        self.name = name
        self.image = image
        self.version = version
        self.port = port
        self.containers = []
        self.environment_vars = []
        self.postgres_proxy_settings = M.Nothing()
        self.gateway_host = M.Nothing()
        self.command = M.Nothing()

    def with_command(self, command_args: List[str]):
        self.command = M.Just(command_args)
        return self

    def with_gateway_host(self, host: str):
        self.gateway_host = M.Just(host)
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

    def exec(self, kubectl: k.KubeCtl, cluster_tag: str) -> E.Either[Any, Any]:
        templates = _get_templates(self.name, self.image, self.version, self.port,
                                   self.environment_vars,
                                   _get_postgres_proxy(kubectl.scripter.project, self.name, self.postgres_proxy_settings),
                                   self.gateway_host,
                                   self.command)

        return k.apply(kubectl, templates, cluster_tag)


def _get_templates(name: str, image: str, version: str, port: int, env_vars: List[str],
                   postgres_proxy: M.Maybe[PostgresProxy],
                   gateway_host: M.Maybe[str],
                   command: M.Maybe[List[str]]) \
        -> List[dict]:
    return nlist([
        {
            'kind': 'Service',
            'apiVersion': 'v1',
            'metadata': {'name': _service_name(name)},
            'spec': {
                'selector': {'app': name},
                'ports': [{'protocol': 'TCP', 'port': 80, 'targetPort': port}]
            }
        },
        {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': _deployment_name(name),
                'labels': {'app': name},
            },
            'spec': {
                'replicas': 1,
                'selector': {
                    'matchLabels': {
                        'app': name
                    }
                },
                'template': {
                    'metadata': {
                        'annotations': {'traffic.sidecar.istio.io/excludeOutboundIPRanges': "0.0.0.0/0"},
                        'labels': {'app': name}},
                    'spec': {
                        'containers': nlist([
                            nmap({
                                'name': name,
                                'image': image + ':' + version,
                                'ports': [{'containerPort': port}],
                                'env': env_vars
                            }).append_if_value(
                                'command', command).to_map()
                        ]).append_if_value(
                            M.map(postgres_proxy, lambda x: x.container())).to_list(),
                        'volumes': nlist([]).append_if_value(
                            M.map(postgres_proxy, lambda x: x.volume())).to_list()
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
                'minReplicas': 1,
                'maxReplicas': 10,
                'targetCPUUtilizationPercentage': 50
            }
        }
    ]).append_if_value(
        M.map(postgres_proxy, lambda x: x.credential_file_secret())) \
      .append_if_value(
        M.map(gateway_host, lambda host: {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'VirtualService',
            'metadata': {'name': _virtual_service_name(name)},
            'spec': {
                'hosts': [host],
                'gateways': ['cluster-gateway'],
                'http': [{'route': [{'destination': {'host': _service_name(name)}}]}]
            }
        })).to_list()


def _horizontal_pod_autoscaler_name(service_name: str):
    return service_name + '-hpa'


def _virtual_service_name(service_name: str):
    return service_name + '-vs'


def _deployment_name(service_name: str):
    return service_name + '-dp'


def _service_name(service_name: str):
    return service_name + '-svc'


def _get_postgres_proxy(project: str, service_name: str, postgres_proxy_settings: M.Maybe[dict]):
    return postgres_proxy_settings \
           | M.map | (lambda settings: PostgresProxy(project,
                                                     service_name,
                                                     settings['db_name'],
                                                     settings['db_region'],
                                                     settings['service_account_b64']))
