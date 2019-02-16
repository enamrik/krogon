import krogon.gcp.k8s.kubectl as k
import krogon.scripts.scripter as sc
import bcrypt
import krogon.either as E
import krogon.maybe as M
import krogon.yaml as yaml
import krogon.gcp.k8s.gateway as gateway
from typing import Optional
from .agent_image import generate_agent_pod_template
from . import gocd_version


def deploy_gocd(
        root_username: str,
        root_password: str,
        git_id_rsa_path: str,
        git_id_rsa_pub_path: str,
        git_host: str,
        gateway_host: Optional[str],
        cluster_name: str,
        script: sc.Scripter):

    kubectl = k.KubeCtl(script)

    gocd_template_text = script.file_system.read(script.file_system.path_rel_to_file('./gocd.yaml', __file__))
    gocd_template_text = _inject_agent_pod_template(
        generate_agent_pod_template(agent_name='gocd-agent-default',
                                    agent_image='gocd/gocd-agent-docker-dind:v'+gocd_version),
        gocd_template_text
    )

    gocd_gateway_entry = gateway.create_virtual_service_template('gocd-server', gateway_host, M.Just(8153))

    return k.secret(kubectl,
                    name='gocd-passwords-file',
                    key_values={'passwords.txt': _create_password_file(root_username, root_password)},
                    cluster_tag=cluster_name) \
           | E.then | (lambda _: k.secret(kubectl,
                                          name='gocd-git-ssh',
                                          key_values={'id_rsa': script.file_system.read(git_id_rsa_path),
                                                      'id_rsa.pub': script.file_system.read(git_id_rsa_pub_path),
                                                      'known_hosts': git_host},
                                          cluster_tag=cluster_name)) \
           | E.then | (lambda _: k.apply(kubectl,
                                         [gocd_template_text, gocd_gateway_entry],
                                         cluster_tag=cluster_name))


def _create_password_file(root_username: str, root_password: str):
    root_password_hash = bcrypt.hashpw(root_password.encode('utf-8'), bcrypt.gensalt(10)).decode('utf-8')
    return "{}:{}\n".format(root_username, root_password_hash)


def _inject_agent_pod_template(agent_template: dict, gocd_template_text: str):
    agent_template = yaml.dump(agent_template).replace("\n", "\\n")
    gocd_template_text = gocd_template_text.replace("<< AGENT_POD_TEMPLATE >>", agent_template)
    return gocd_template_text



