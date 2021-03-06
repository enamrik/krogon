from typing import List, Optional, Callable

from krogon.k8s.k8s_env_vars import set_environment_variable, add_environment_secret
from krogon.k8s.template_context import TemplateContext
from krogon.nullable import nmap
import krogon.maybe as M
import krogon.nullable as N


def container(name: str, image: str):
    return K8sContainer(name, image)


class K8sContainer:
    def __init__(self, name: str, image: str):
        self.name = name
        self.image = image
        self.containers = []
        self.environment_vars = []
        self.environment_vars_from_context = []
        self.command = M.nothing()
        self.resources = M.nothing()
        self.volumes = []
        self.app_ports = []

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

    def with_volume_mount(self, name: str, path: str):
        self.volumes.append({'name': name, 'mountPath': path})
        return self

    def with_app_port(self, port: int):
        self.app_ports.append({'containerPort': port})
        return self

    def with_command(self, command_args: List[str]):
        self.command = M.just(command_args)
        return self

    def with_environment_variable(self, name: str, value: str):
        self.environment_vars = set_environment_variable(self.environment_vars, name, value)
        return self

    def with_environment_from_context(self, name: str, action: Callable[[Callable[[str], str]], str]):
        self.environment_vars_from_context.append((name, action))
        return self

    def with_environment_secret(self, secret_name: str, data: dict):
        self.environment_vars = add_environment_secret(self.environment_vars, secret_name, data)
        return self

    def get_template(self, context: TemplateContext):
        cluster_name = context.get_state('cluster_name')
        if cluster_name is not None:
            self.environment_vars = set_environment_variable(self.environment_vars, 'CLUSTER', cluster_name)

        for (name, action) in self.environment_vars_from_context:
            self.environment_vars = set_environment_variable(self.environment_vars, name,
                                                             action(lambda key: context.get_state(key)))

        return nmap({
            'name': app_name(self.name),
            'image': self.image,
            'ports': self.app_ports,
            'env': self.environment_vars,
            'volumeMounts': self.volumes
        }).append_if_value(
            'command', self.command) \
          .append_if_value(
              'resources', self.resources) \
          .to_map()


def app_name(service_name: str):
    return service_name + '-app'

