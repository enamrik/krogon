from krogon.exec_context import ExecContext
from krogon.steps.k8s.k8s_container import K8sContainer, app_name


def deployment(name: str):
    return K8sDeploymentTemplate(name)


class K8sDeploymentTemplate:
    def __init__(self, name: str):
        self.name = name
        self.replicas = 1
        self.containers = []
        self.volumes = []
        self.strategy = {
            'type': 'RollingUpdate',
            'rollingUpdate': {
                'maxSurge': '25%',
                'maxUnavailable': '25%'
            }
        }

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

    def with_replicas(self, count):
        self.replicas = count
        return self

    def with_container(self, container: K8sContainer):
        self.containers.append(container)
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
                        'spec': {
                            'containers': list(map(lambda x: _to_container_template(x, context), self.containers)),
                            'volumes': self.volumes
                        }
                    }
                }
            },
        ])
        return context


def _to_container_template(container: K8sContainer, context: ExecContext) -> dict:
    if context.get_state('cluster_name') is not None:
        container = container.with_environment_variable('CLUSTER', context.get_state('cluster_name'))
    return container.get_template()


def _deployment_name(service_name: str):
    return service_name + '-dp'


