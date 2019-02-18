import krogon.k8s.kubectl as k
import json
import krogon.either as E


cert_issuer_name = 'letsencrypt-prod'
istio_certs_secret = 'istio-ingressgateway-certs'


def _create_https(k_ctl: k.KubeCtl, cluster_name: str):
    return \
        k.kubectl(k_ctl, cluster_name, 'label namespace istio-system certmanager.k8s.io/disable-validation=true') \
        | E.then | (lambda _: k.kubectl(k_ctl, cluster_name,
                                        'apply --namespace istio-system '
                                        '-f https://raw.githubusercontent.com/jetstack/cert-manager/'
                                        'release-0.6/deploy/manifests/00-crds.yaml')) \
        | E.then | (lambda _: k.kubectl(k_ctl, cluster_name,
                                        'apply --namespace istio-system '
                                        '-f https://raw.githubusercontent.com/jetstack/cert-manager/'
                                        'release-0.6/deploy/manifests/cert-manager.yaml'))


def _create_https_certmanager_config(k_ctl: k.KubeCtl,
                                     project_id: str,
                                     service_account: dict,
                                     email: str,
                                     cluster_host: str,
                                     cluster_name: str):

    cert_manager_credentials = 'cert-manager-credentials'
    cert_manager_credentials_file = 'gcp-dns-admin.json'

    return k.secret(k_ctl,
                    name=cert_manager_credentials,
                    key_values={cert_manager_credentials_file: json.dumps(service_account)},
                    cluster_tag=cluster_name) \
           | E.then | (lambda _: k.apply(k_ctl,
                                         templates=[
                                             _create_cert_issuer_template(
                                                 project_id,
                                                 service_account_secret_name=cert_manager_credentials,
                                                 service_account_secret_key=cert_manager_credentials_file,
                                                 email=email),
                                             _create_cert_template(cluster_host)
                                         ],
                                         cluster_tag=cluster_name))


def _create_cert_issuer_template(project_id:str ,
                                 service_account_secret_name: str,
                                 service_account_secret_key: str,
                                 email: str):
    return {
        'apiVersion': 'certmanager.k8s.io/v1alpha1',
        'kind': 'Issuer',
        'metadata': {'name': 'letsencrypt-prod',
                     'namespace': 'istio-system'},
        'spec': {
            'acme': {
                'server': 'https://acme-v02.api.letsencrypt.org/directory',
                'email': email,
                'privateKeySecretRef': {'name': 'letsencrypt-prod'},
                'dns01': {
                    'providers': [
                        {'name': 'cloud-dns',
                         'clouddns': {
                             'serviceAccountSecretRef': {'name': service_account_secret_name,
                                                         'key': service_account_secret_key},
                             'project': project_id
                         }}
                    ]
                }
            }
        }
    }


def _create_cert_template(cluster_host: str):
    return {
        'apiVersion': 'certmanager.k8s.io/v1alpha1',
        'kind': 'Certificate',
        'metadata': {'name': 'istio-gateway',
                     'namespace': 'istio-system'},
        'spec': {
            'secretname': istio_certs_secret,
            'issuerRef': {'name': cert_issuer_name},
            'commonName': '*.'+cluster_host,
            'acme': {
                'config': [
                    {'dns01': {'provider': 'cloud-dns'},
                     'domains': ['*.'+cluster_host, cluster_host]}
                ]
            }
        }
    }

