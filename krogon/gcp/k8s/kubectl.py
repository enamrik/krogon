import krogon.scripts.scripter as sc
import krogon.yaml as yaml
import krogon.either as E
from base64 import b64encode
from typing import Union, List
from krogon.either_ext import chain


class KubeCtl:
    def __init__(self, scripter: sc.Scripter):
        self.scripter = scripter


def secret(k_ctl: KubeCtl, name: str, key_values: dict, cluster_tag: str):
    to_base64 = lambda value: b64encode(value.encode('utf-8')).decode('utf-8')
    data = {k: to_base64(v) for k, v in key_values.items()}

    secret_template = {
        'apiVersion': 'v1',
        'kind': 'Secret',
        'metadata': {'name': name},
        'type': 'Opaque',
        'data': data
    }
    return apply(k_ctl, [secret_template], cluster_tag)


def apply(k_ctl: KubeCtl, templates: List[Union[dict, str]], cluster_tag: str):
    return k_ctl.scripter.file_system.with_temp_file(
        contents=_combine_templates(templates),
        filename='template',
        runner=lambda temp_file: kubectl_all_by_tag(k_ctl,
                                                    cluster_tag,
                                                    'apply -f {}'.format(temp_file)))


def proxy(k_ctl: KubeCtl, cluster_name: str, port: str):
    scp = k_ctl.scripter
    kubeconfig_file = sc._kubeconfig_file_path(scp.cache_dir, cluster_name)
    return sc._setup(scp) \
           | E.then | (lambda _: sc._gen_kubeconfig(scp, cluster_name)) \
           | E.then | (lambda _: scp.os_run('{cache_dir}/kubectl proxy --port {port} --kubeconfig {kubeconfig_file}'
                                            .format(cache_dir=scp.cache_dir,
                                                    kubeconfig_file=kubeconfig_file,
                                                    port=port)))


def kubectl_all_by_tag(k_ctl: KubeCtl, cluster_tag: str, command: str):

    def _exec_in_clusters(cluster_names: List[str]):
        return chain(cluster_names, lambda cluster_name: kubectl(k_ctl, cluster_name, command))

    return _get_clusters(k_ctl, by_tag=cluster_tag) \
           | E.then | (lambda cluster_names: _exec_in_clusters(cluster_names))


def kubectl(k_ctl: KubeCtl, cluster_name: str, command: str):
    scp = k_ctl.scripter
    kubeconfig_file = sc._kubeconfig_file_path(scp.cache_dir, cluster_name)
    return sc._setup(scp) \
           | E.then | (lambda _: sc._gen_kubeconfig(scp, cluster_name)) \
           | E.then | (lambda _: scp.os_run('{cache_dir}/kubectl --kubeconfig {kubeconfig_file} {command}'
                                            .format(cache_dir=scp.cache_dir,
                                                    kubeconfig_file=kubeconfig_file,
                                                    command=command)))


def _get_clusters(k_ctl: KubeCtl, by_tag: str):
    scp = k_ctl.scripter

    def _parse_cluster_names(cluster_names: str):
        names = list(map(lambda c: c.strip().strip(), cluster_names.split('\n')))
        return list(filter(lambda name: by_tag in name, names))

    return sc._setup(scp) \
           | E.then | (lambda _: scp.os_run("{cache_dir}/google-cloud-sdk/bin/gcloud "
                                            "container clusters list --format=\"value(name)\""
                                            .format(cache_dir=scp.cache_dir))) \
           | E.then | _parse_cluster_names


def _combine_templates(templates: List[Union[dict, str]]) -> str:
    def _get_template_string(template: Union[dict, str]) -> str:
        if type(template) == dict:
            template = yaml.dump(template)
        return template

    template_strings = list(map(_get_template_string, templates))
    return '\n---\n'.join(template_strings)
