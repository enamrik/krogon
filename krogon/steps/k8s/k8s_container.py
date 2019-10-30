from typing import List, Optional
from krogon.nullable import nmap
from krogon.steps.k8s.k8s_env_vars import set_environment_variable, add_environment_secret
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

    def with_environment_secret(self, secret_name: str, data: dict):
        self.environment_vars = add_environment_secret(self.environment_vars, secret_name, data)
        return self

    def get_template(self):
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

