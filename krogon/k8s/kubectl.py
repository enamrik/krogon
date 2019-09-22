from base64 import b64encode
from typing import Union, List
from python_either.either_ext import chain
from krogon.config import Config
from krogon.os import OS
from krogon.logger import Logger
from typing import Optional
from python_maybe.nullable import nmap
import krogon.yaml as yaml
import python_either.either as E
import python_maybe.maybe as M
import krogon.gcp.gcloud as g
import krogon.file_system as fs


class KubeCtl:
    def __init__(self,
                 config: Config,
                 os: OS,
                 log: Logger,
                 gcloud: g.GCloud,
                 file: fs.FileSystem):

        self.config = config
        self.log = log
        self.file = file
        self.gcloud = gcloud
        self.run = lambda cmd: os.run(cmd, log)
        self.is_macos = os.is_macos


def secret(k_ctl: KubeCtl,
           name: str,
           key_values: dict,
           cluster_tag: str,
           namespace: Optional[str] = None,
           already_b64: Optional[bool] = False):

    to_base64 = lambda value: value \
        if already_b64 \
        else b64encode(value.encode('utf-8')).decode('utf-8')

    data = {k: to_base64(v) for k, v in key_values.items()}

    secret_template = {
        'apiVersion': 'v1',
        'kind': 'Secret',
        'metadata': nmap({
            'name': name}).append_if_value(
            'namespace', M.from_value(namespace)).to_map(),
        'type': 'Opaque',
        'data': data
    }
    return apply(k_ctl, [secret_template], cluster_tag)


def delete(k_ctl: KubeCtl, templates: List[Union[dict, str]], cluster_tag: str):
    return _exec_template(k_ctl, 'delete', templates, cluster_tag)


def apply(k_ctl: KubeCtl, templates: List[Union[dict, str]], cluster_tag: str):
    return _exec_template(k_ctl, 'apply', templates, cluster_tag)


def proxy(k_ctl: KubeCtl, cluster_name: str, port: str):
    return _setup(k_ctl, cluster_name) \
           | E.then | (lambda _: g.gen_kubeconfig(k_ctl.gcloud, cluster_name)) \
           | E.then | (lambda _: k_ctl.run('{cache_dir}/kubectl proxy --port {port} --kubeconfig {kubeconfig_file}'
                                           .format(cache_dir=k_ctl.config.cache_dir,
                                                   kubeconfig_file=g.kubeconfig_file_path(k_ctl.gcloud, cluster_name),
                                                   port=port)))


def kubectl_all_by_tag(k_ctl: KubeCtl, cluster_tag: str, command: str):

    def _exec_in_clusters(cluster_names: List[str]):
        return chain(cluster_names, lambda cluster_name: kubectl(k_ctl, cluster_name, command))

    return g.get_clusters(k_ctl.gcloud, by_tag=cluster_tag) \
           | E.then | (lambda cluster_names: _exec_in_clusters(cluster_names))


def kubectl(k_ctl: KubeCtl, cluster_name: str, command: str):
    kubeconfig_file = g.kubeconfig_file_path(k_ctl.gcloud, cluster_name)
    return _setup(k_ctl, cluster_name) \
           | E.then | (lambda _: g.gen_kubeconfig(k_ctl.gcloud, cluster_name)) \
           | E.then | (lambda _: k_ctl.run('{cache_dir}/kubectl --kubeconfig {kubeconfig_file} {command}'
                                           .format(cache_dir=k_ctl.config.cache_dir,
                                                   kubeconfig_file=kubeconfig_file,
                                                   command=command)))


def _exec_template(k_ctl: KubeCtl, action, templates: List[Union[dict, str]], cluster_tag: str):
    return k_ctl.file.with_temp_file(
        contents=_combine_templates(templates),
        filename='template.yaml',
        runner=lambda temp_file: kubectl_all_by_tag(k_ctl,
                                                    cluster_tag,
                                                    action+' -f {}'.format(temp_file)))


def _combine_templates(templates: List[Union[dict, str]]) -> str:
    def _get_template_string(template: Union[dict, str]) -> str:
        if type(template) is not str:
            template = yaml.dump(template)
        return template

    template_strings = list(map(_get_template_string, templates))
    return '\n---\n'.join(template_strings)


def _setup(k_ctl: KubeCtl, cluster_name: str):
    return g.gen_kubeconfig(k_ctl.gcloud, cluster_name)


