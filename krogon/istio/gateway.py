from krogon.nullable import nmap, nlist
from .https import IstioHttpsConfig, configure_https, HttpsResult
from krogon.config import Config
import krogon.k8s.kubectl as k
import krogon.maybe as M
import krogon.either as E


gateway_name = 'cluster-gateway'


def create_virtual_service_template(service_name: str, host_url: str, port: M.Maybe[int]):
    return {
        'apiVersion': 'networking.istio.io/v1alpha3',
        'kind': 'VirtualService',
        'metadata': {'name': service_name},
        'spec': {
            'hosts': [host_url],
            'gateways': ['cluster-gateway'],
            'http': [{
                'route': [{
                    'destination': nmap({
                        'host': service_name
                    }).append_if_value('port', port | M.map |(lambda x: {'number': x})).to_map()
                }]}]
        }
    }


def create_gateway(k_ctl: k.KubeCtl,
                   config: Config,
                   cluster_name: str,
                   https_config: M.Maybe[IstioHttpsConfig]):

    def _create_gateway(https_result: HttpsResult):
        templates = _create_gateway_health_templates()
        templates.append(_create_gateway_template(https_result.using_https))
        return k.apply(k_ctl, templates, cluster_name)

    return https_config \
           | M.from_maybe | dict(if_just=lambda c: configure_https(c,
                                                                   k_ctl,
                                                                   config,
                                                                   cluster_name=cluster_name),
                                 if_nothing=lambda: E.Success(HttpsResult.none())) \
           | E.then | (lambda result: _create_gateway(result))


def _create_gateway_template(https: bool):
    redirect_config = \
        M.Just({'httpsRedirect': True}) \
        if https \
        else M.Nothing()

    https_config = \
        M.Just({'port': {'number': 443, 'name': 'https', 'protocol': 'HTTPS'},
                'hosts': ['*'],
                'tls': {'mode': 'SIMPLE',
                        'privateKey': '/etc/istio/ingressgateway-certs/tls.key',
                        'serverCertificate': '/etc/istio/ingressgateway-certs/tls.crt'}}) \
        if https \
        else M.Nothing()

    return {
        'apiVersion': 'networking.istio.io/v1alpha3',
        'kind': 'Gateway',
        'metadata': {'name': gateway_name},
        'spec': {
            'selector': {'istio': 'ingressgateway'},
            'servers': nlist([
                nmap({'port': {'number': 80, 'name': 'http', 'protocol': 'HTTP'},
                      'hosts': ['*']}).append_if_value('tls', redirect_config).to_map()
            ]).append_if_value(https_config).to_list()
        }
    }


def _create_gateway_health_templates():
    return [
        {
           'apiVersion' : 'v1',
            'kind': 'Service',
            'metadata': {'name': 'healthcheck'},
            'spec': {
                'type': 'ClusterIP',
                'selector': {'app': 'healthcheck-app'},
                'ports': [{'port': 80, 'targetPort': 80}]
            }
        },
        {

            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': 'healthcheck-dp',
                'labels': {'app': 'healthcheck-app'}
            },
            'spec': {
                'replicas': 1,
                'selector': {'matchLabels': {'app': 'healthcheck-app'}},
                'template': {
                    'metadata': {
                        'labels': {'app': 'healthcheck-app'}
                    },
                    'spec': {
                        'containers': [
                            {'name': 'healthcheck-app',
                             'image': 'nginx:1.14',
                             'ports': [{'containerPort': 80}]}
                        ]
                    }
                }
            }
        },
        {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'VirtualService',
            'metadata': {'name': 'healthcheck-vs'},
            'spec': {
                'hosts': ['*'],
                'gateways': [gateway_name],
                'http': [{'route': [{'destination': {'host': 'healthcheck'}}]}]
            }
        }
    ]


