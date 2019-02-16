from krogon.nullable import nmap
import krogon.maybe as M


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
