from krogon.k8s.template_context import TemplateContext
from krogon.nullable import nlist, nmap
import krogon.either as E
import krogon.maybe as M


def gateway_mapping(name: str, host: str, service: str, port: int = None):
    return K8sGatewayTemplate(name, host, service, port)


class K8sGatewayTemplate:
    def __init__(self, name: str, host: str, service: str, port: int = None):
        self.name = name
        self.host = host
        self.service = service
        self.port: M.Maybe[int] = M.from_value(port)
        self.gateway_name = 'cluster-gateway'

    def _is_ambassador(self, context: TemplateContext):
        cluster_name = context.get_state('cluster_name')
        return context.kubectl.cmd('get mappings', cluster_name) \
               | E.from_either | (dict(if_success=lambda _: True, if_failure=lambda _: False))

    def _is_istio(self, context: TemplateContext):
        cluster_name = context.get_state('cluster_name')
        return context.kubectl.cmd('get virtualservices', cluster_name) \
               | E.from_either | (dict(if_success=lambda _: True, if_failure=lambda _: False))

    def map_context(self, context: TemplateContext) -> TemplateContext:
        if self._is_ambassador(context):
            context.append_templates([{
                'apiVersion': 'getambassador.io/v1',
                'kind': 'Mapping',
                'metadata': {'name': self.name+'-mapping'},
                'spec': nmap({
                    'prefix': '/',
                    'service': self.service+str(M.map(self.port, (lambda x: ':'+str(x))) | M.value_or_default | '')
                }).append_if_value('host', M.nothing() if self.host == '*' else M.just(self.host)).to_map()
            }])
            return context
        if self._is_istio(context):
            context.append_templates([{
                'apiVersion': 'networking.istio.io/v1alpha3',
                'kind': 'VirtualService',
                'metadata': {'name': self.name+'-vs'},
                'spec': {
                    'hosts': [self.host],
                    'gateways': [self.gateway_name],
                    'http': nlist([
                        nmap({
                            'route': [{
                                'destination': nmap({
                                    'host': self.service
                                }).append_if_value(
                                    'port', M.map(self.port, (lambda x: {'number': x}))).to_map()
                            }]}).to_map(),
                    ]).to_list()
                }
            }])
            return context
        raise AssertionError('Unsupported gateway')
